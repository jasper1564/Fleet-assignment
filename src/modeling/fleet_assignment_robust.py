import gurobipy as gp
from gurobipy import GRB
import json
import os
import csv
import numpy as np
from pathlib import Path

ROOT = next(path for path in Path(__file__).resolve().parents if (path / '.git').exists())
DEMAND_INPUT_DIR = ROOT / 'data' / 'model_input' / 'demand'
NETWORK_INPUT_DIR = ROOT / 'data' / 'model_input' / 'network'
REFERENCE_INPUT_DIR = ROOT / 'data' / 'raw' / 'reference'
RESULTS_DIR = ROOT / 'results' / 'runs' / 'robustness'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================================
# 1. 鍩虹鏁版嵁缁撴瀯瀹氫箟
# =====================================================================
class EventNode:
    def __init__(self, time):
        self.time = time
        self.landing_tasks = []   # 鍦ㄦ鏃跺埢闄嶈惤骞跺畬鎴愯繃绔欙紙ready锛夌殑浠诲姟
        self.departing_tasks = [] # 鍦ㄦ鏃跺埢璧烽锛坉epart锛夌殑浠诲姟
    
    def __repr__(self):
        return f"Node(time={self.time}, arr={self.landing_tasks}, dep={self.departing_tasks})"

# =====================================================================
# 2. 浠?JSON 鏂囦欢璇诲彇鐪熷疄鏁版嵁
# =====================================================================
def load_real_data(data_dir=None):
    """
    浠庢湰鍦拌鍙栨暟鎹竻娲楀悗鐨?JSON 鏂囦欢锛屽苟鏋勯€犱负 Gurobi 妯″瀷鎵€闇€鐨?14 涓熀纭€鏁版嵁缁撴瀯銆?
    """
    print(f"馃攧 姝ｅ湪浠?'{data_dir}' 鐩綍鍔犺浇 JSON 鏁版嵁...")
    
    with open(DEMAND_INPUT_DIR / 'product_info_em_restored.json', 'r', encoding='utf-8') as f:
        product_info = json.load(f)
    with open(NETWORK_INPUT_DIR / 'super_flight_schedule.json', 'r', encoding='utf-8') as f:
        super_flight_schedule = json.load(f)
    with open(NETWORK_INPUT_DIR / 'airport_timeline.json', 'r', encoding='utf-8') as f:
        airport_timeline = json.load(f)
    with open(NETWORK_INPUT_DIR / 'leg_to_products.json', 'r', encoding='utf-8') as f:
        leg_to_products = json.load(f)
        
    # 浠?CSV 鏂囦欢璇诲彇鏈洪槦淇℃伅
    fleet_info = {}
    csv_file_path = REFERENCE_INPUT_DIR / 'fleet_family_master.csv'
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fleet_type = row['机型'].strip()
                fleet_info[fleet_type] = {
                    "count": int(row['飞机数量']),
                    "seats": int(row['座位数']),
                    "cost_per_min": float(row['每小时飞行成本']) / 60.0
                }
        print(f"Loaded fleet reference from {csv_file_path}")
    except FileNotFoundError:
        print(f"Fleet reference file not found: {csv_file_path}")
        raise

    fleets = list(fleet_info.keys())
    total_aircraft = {k: v['count'] for k, v in fleet_info.items()}
    seats = {k: v['seats'] for k, v in fleet_info.items()}

    products = list(product_info.keys())
    demand = {p: info.get('Total_Demand', 0.0) for p, info in product_info.items()}
    fare = {p: info.get('Fare', 1000.0) for p, info in product_info.items()}

    tasks = list(super_flight_schedule.keys())
    flight_cost = {}
    overnight_tasks = []
    leg_to_task_map = {}
    all_legs_set = set()

    for task, info in super_flight_schedule.items():
        if info.get('is_overnight', False):
            overnight_tasks.append(task)
            
        fly_mins = info.get('total_fly_minutes', 0)
        for k in fleets:
            flight_cost[(task, k)] = fly_mins * fleet_info[k].get('cost_per_min', 50)
            
        for leg in info.get('legs', []):
            leg_to_task_map[leg] = task
            all_legs_set.add(leg)
            
    all_legs = list(all_legs_set)

    airports = list(airport_timeline.keys())
    airport_nodes_dict = {}

    for airport, events in airport_timeline.items():
        nodes_by_time = {}
        for event in events:
            t = event['time']
            if t not in nodes_by_time:
                nodes_by_time[t] = EventNode(t)
                
            task_id = event.get('flight_id') 
            event_type = event.get('type') 
            
            if task_id and event_type:
                if task_id not in tasks and f"super_{task_id}" in tasks:
                    task_id = f"super_{task_id}"
                
                if task_id in tasks:
                    if event_type == 'ready':
                        nodes_by_time[t].landing_tasks.append(task_id)
                    elif event_type == 'depart':
                        nodes_by_time[t].departing_tasks.append(task_id)

        sorted_nodes = [nodes_by_time[t] for t in sorted(nodes_by_time.keys())]
        airport_nodes_dict[airport] = sorted_nodes

    print("鉁?JSON 鏁版嵁鍔犺浇骞惰浆鎹负缃戠粶鍥惧畬姣曪紒")
    return (fleets, tasks, products, all_legs, airports, total_aircraft, seats, 
            flight_cost, fare, demand, leg_to_products, leg_to_task_map, 
            overnight_tasks, airport_nodes_dict)

# =====================================================================
# 3. 涓ら樁娈甸殢鏈鸿鍒掓牳蹇冨缓妯″嚱鏁?(寮曞叆椴佹鎬?
# =====================================================================
def build_and_solve_fap_model_stochastic(
    fleets, tasks, products, all_legs, airports, total_aircraft, seats,
    flight_cost, fare, demand, leg_to_products, leg_to_task_map,
    overnight_tasks, airport_nodes_dict,
    num_scenarios=20, volatility=0.20
):
    model = gp.Model("FAP_NRM_Stochastic")
    model.setParam('OutputFlag', 1)

    print(f"\n馃幉 姝ｅ湪鐢熸垚 {num_scenarios} 涓渶姹傞殢鏈哄満鏅?(璁惧畾娉㈠姩鐜? {volatility*100}%)...")
    
    # 0. 钂欑壒鍗℃礇闇€姹傚満鏅敓鎴?
    scenarios = list(range(num_scenarios))
    prob = 1.0 / num_scenarios  # 鍋囪姣忎釜鍦烘櫙鍙戠敓姒傜巼鍧囩瓑
    stochastic_demand = {}
    
    np.random.seed(42) # 鍥哄畾闅忔満绉嶅瓙锛屼繚璇佹瘡娆¤皟璇曠敓鎴愮殑鍦烘櫙涓€鑷?
    for p in products:
        mu = demand.get(p, 0)
        sigma = mu * volatility
        samples = np.random.normal(loc=mu, scale=sigma, size=num_scenarios)
        stochastic_demand[p] = {w: max(0.0, round(samples[w])) for w in scenarios}

    # 1. 绗竴闃舵鍐崇瓥鍙橀噺锛氭満鍨嬪垎閰嶄笌椋炴満鍦伴潰娴佽浆锛堜笉闅忓満鏅敼鍙橈級
    x = model.addVars(tasks, fleets, vtype=GRB.BINARY, name="x")
    all_nodes = [node for airport in airports for node in airport_nodes_dict[airport]]
    g = model.addVars(all_nodes, fleets, lb=0.0, vtype=GRB.CONTINUOUS, name="g")
    
    # 绗簩闃舵鍐崇瓥鍙橀噺锛氫笉鍚屽満鏅笅鐨勫疄闄呭敭绁ㄩ噺锛堥殢鍦烘櫙娉㈠姩锛?
    s = model.addVars(products, scenarios, lb=0.0, vtype=GRB.CONTINUOUS, name="s")

    # 鍞エ閲忎笉鑳借秴杩囩壒瀹氬満鏅笅鐨勯殢鏈洪渶姹備笂闄?
    model.addConstrs((s[p, w] <= stochastic_demand[p][w] 
                      for p in products for w in scenarios), name="demand_ub")

    # 2. 鐩爣鍑芥暟锛氭渶澶у寲锛堟湡鏈涚エ浠锋敹鍏?- 鍥哄畾椋炶鎴愭湰锛?
    expected_revenue = gp.quicksum(prob * fare[p] * s[p, w] for p in products for w in scenarios)
    cost = gp.quicksum(flight_cost[f, k] * x[f, k] for f in tasks for k in fleets if (f, k) in flight_cost)
    model.setObjective(expected_revenue - cost, GRB.MAXIMIZE)

    # 3A. 绾︽潫 A锛氬敮涓€鎬х害鏉?
    model.addConstrs((gp.quicksum(x[f, k] for k in fleets) == 1 for f in tasks), name="task_cover")

    # 3B. 绾︽潫 B锛氭祦骞宠　涓庤法鏃ュ惊鐜害鏉?
    for airport in airports:
        nodes = airport_nodes_dict[airport]
        for i, node in enumerate(nodes):
            prev_node = nodes[i - 1]
            for k in fleets:
                lhs_landing = gp.quicksum(x[f, k] for f in node.landing_tasks)
                rhs_departing = gp.quicksum(x[f, k] for f in node.departing_tasks)
                model.addConstr(
                    g[prev_node, k] + lhs_landing == g[node, k] + rhs_departing,
                    name=f"flow_balance[{airport},{i},{k}]"
                )

    # 3C. 绾︽潫 C锛氬彲鐢ㄦ満闃熻妯＄害鏉?
    for k in fleets:
        last_nodes = [airport_nodes_dict[airport][-1] for airport in airports]
        ground_at_midnight = gp.quicksum(g[n, k] for n in last_nodes)
        airborne_overnight = gp.quicksum(x[f, k] for f in overnight_tasks)
        model.addConstr(
            ground_at_midnight + airborne_overnight <= total_aircraft[k],
            name=f"fleet_count[{k}]"
        )

    # 3D. 绾︽潫 D锛氳埅娈靛閲忕害鏉?(蹇呴』鍦ㄣ€愭瘡涓€涓満鏅€戜笅閮芥弧瓒崇墿鐞嗗骇浣嶉檺鍒?
    print("鈿欙笍 姝ｅ湪鏋勫缓澶氬満鏅埅娈靛閲忕害鏉?..")
    for w in scenarios:
        for l in all_legs:
            parent_task = leg_to_task_map[l]
            demand_on_leg = gp.quicksum(s[p, w] for p in leg_to_products.get(l, []))
            capacity_of_leg = gp.quicksum(seats[k] * x[parent_task, k] for k in fleets)
            model.addConstr(demand_on_leg <= capacity_of_leg, name=f"leg_capacity[{l}_{w}]")

    # 4. 姹傝В
    model.optimize()
    return model, x, g, s, stochastic_demand, scenarios

# =====================================================================
# 4. 杩愯涓庣粨鏋滆В鏋愬強瀵煎嚭 (澶氬満鏅湡鏈涘€肩増鏈?
# =====================================================================
if __name__ == "__main__":
    # 鍙互閫氳繃淇敼 num_scenarios 鍜?volatility 璋冩暣椴佹鎬у己搴?
    NUM_SCENARIOS = 20
    VOLATILITY = 0.20
    
    data_tuple = load_real_data()
    
    # 瑙ｅ寘閮ㄥ垎鍩虹鏁版嵁浠ヤ究鍚庣画瀵煎嚭浣跨敤
    fleets = data_tuple[0]
    tasks = data_tuple[1]
    products = data_tuple[2]
    all_legs = data_tuple[3]
    airports = data_tuple[4]
    seats = data_tuple[6]
    leg_to_products = data_tuple[10]
    leg_to_task_map = data_tuple[11]
    airport_nodes_dict = data_tuple[13]

    model, x, g, s, stochastic_demand, scenarios = build_and_solve_fap_model_stochastic(
        *data_tuple, num_scenarios=NUM_SCENARIOS, volatility=VOLATILITY
    )
    
    if model.Status == GRB.OPTIMAL:
        print("\n" + "="*60)
        print(f"馃帀 椴佹鎬ф眰瑙ｆ垚鍔燂紒鏈€澶ф湡鏈涙€诲埄娑? 楼 {model.ObjVal:,.2f}")
        print("="*60)
        
        print("\n馃捑 姝ｅ湪灏嗗鍦烘櫙鏈熸湜缁撴灉瀵煎嚭涓?CSV 鏂囦欢...")

        # --- 鍩虹鏄犲皠缂撳瓨 ---
        task_to_fleet = {}
        for f in tasks:
            for k in fleets:
                if x[f, k].X > 0.5:
                    task_to_fleet[f] = k

        product_to_legs = {p: [] for p in products}
        for leg, prods in leg_to_products.items():
            for p in prods:
                if p in product_to_legs:
                    product_to_legs[p].append(leg)

        # ==========================================
        # 瀵煎嚭 1锛氭瀯寤轰骇鍝侀攢閲忎笌杩愬姏鍒嗛厤缁煎悎鍒嗘瀽瀹借〃 (鏈熸湜鍊?
        # ==========================================
        comprehensive_records = []
        for p in products:
            # 璁＄畻鍚勫満鏅笅鐨勫钩鍧囧敭绁ㄩ噺鍜屽钩鍧囬渶姹?
            avg_sold = sum(s[p, w].X for w in scenarios) / NUM_SCENARIOS
            avg_demand = sum(stochastic_demand[p][w] for w in scenarios) / NUM_SCENARIOS
            
            if avg_sold > 0.01: 
                p_legs = product_to_legs.get(p, [])
                p_tasks = [leg_to_task_map.get(l) for l in p_legs if l in leg_to_task_map]
                p_fleets = [task_to_fleet.get(t, "Unassigned") for t in p_tasks]
                
                comprehensive_records.append({
                    "Product": p,
                    "Expected_Demand": round(avg_demand, 2),
                    "Expected_Sold": round(avg_sold, 2),
                    "Expected_Unmet": round(avg_demand - avg_sold, 2),
                    "Legs": " -> ".join(p_legs),
                    "Tasks": " -> ".join(p_tasks),
                    "Assigned_Fleets": " -> ".join(p_fleets)
                })

        with open(RESULTS_DIR / 'comprehensive_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Product", "Expected_Demand", "Expected_Sold", "Expected_Unmet", "Legs", "Tasks", "Assigned_Fleets"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comprehensive_records)

        # ==========================================
        # 瀵煎嚭 2锛氳法鏃ュ湴闈㈤┗鍦虹姸鎬?(绗竴闃舵鍙橀噺锛屼繚鎸佷笉鍙?
        # ==========================================
        ground_records = []
        for a in airports:
            if not airport_nodes_dict[a]:
                continue
            last_node = airport_nodes_dict[a][-1]
            for k in fleets:
                ground_count = g[last_node, k].X
                if ground_count > 0.01:
                    ground_records.append({
                        "Airport": a, 
                        "Fleet": k, 
                        "Grounded_Count": round(ground_count, 2)
                    })

        with open(RESULTS_DIR / 'ground_status.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=["Airport", "Fleet", "Grounded_Count"])
            writer.writeheader()
            writer.writerows(ground_records)

        # ==========================================
        # 瀵煎嚭 3锛氳埅娈垫湡鏈涘奖瀛愪环鏍?(Bid Price)
        # ==========================================
        print("馃攳 姝ｅ湪璁＄畻缃戠粶鑸鏈熸湜褰卞瓙浠锋牸(Expected Bid Prices)...")
        fixed_model = model.fixed()
        fixed_model.setParam('OutputFlag', 0)
        fixed_model.optimize()
        
        if fixed_model.Status == GRB.OPTIMAL:
            shadow_price_records = []
            for l in all_legs:
                total_pi = 0
                for w in scenarios:
                    constr = fixed_model.getConstrByName(f"leg_capacity[{l}_{w}]")
                    if constr:
                        total_pi += constr.Pi
                
                # 澧炲姞涓€涓墿鐞嗗骇浣嶇殑鏈熸湜浠峰€?= 鍚勫満鏅绾︽潫 Pi 鍊肩殑鎬诲拰
                expected_shadow_price = total_pi
                
                shadow_price_records.append({
                    "Leg": l,
                    "Expected_Shadow_Price": round(expected_shadow_price, 2)
                })
            with open(RESULTS_DIR / 'shadow_prices.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=["Leg", "Expected_Shadow_Price"])
                writer.writeheader()
                writer.writerows(shadow_price_records)

        # ==========================================
        # 瀵煎嚭 4锛氳埅娈电湡瀹炲搴х巼鎺㈤拡 (鏈熸湜鍊?
        # ==========================================
        leg_load_records = []
        for l in all_legs:
            parent_task = leg_to_task_map.get(l)
            assigned_fleet = task_to_fleet.get(parent_task, "Unknown")
            assigned_seats = seats.get(assigned_fleet, 0)
            
            # 璁＄畻鎵€鏈夊満鏅笅锛岃鑸涓婄殑骞冲潎鎬诲娴?
            expected_pax_on_leg = 0
            for w in scenarios:
                expected_pax_on_leg += sum(s[p, w].X for p in leg_to_products.get(l, []))
            expected_pax_on_leg /= NUM_SCENARIOS
            
            load_factor = (expected_pax_on_leg / assigned_seats * 100) if assigned_seats > 0 else 0
            
            leg_load_records.append({
                "Leg": l,
                "Parent_Task": parent_task,
                "Assigned_Fleet": assigned_fleet,
                "Seat_Capacity": assigned_seats,
                "Expected_Passengers": round(expected_pax_on_leg, 2),
                "Expected_Load_Factor(%)": round(load_factor, 2)
            })

        with open(RESULTS_DIR / 'leg_load_factor.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Leg", "Parent_Task", "Assigned_Fleet", "Seat_Capacity", 
                          "Expected_Passengers", "Expected_Load_Factor(%)"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leg_load_records)

        print("Export complete. Key outputs:")
        print("   - comprehensive_analysis.csv")
        print("   - ground_status.csv")
        print("   - shadow_prices.csv")
        print("   - leg_load_factor.csv")

    elif model.Status == GRB.INFEASIBLE:
        print("\nModel is infeasible.")
    else:
        print(f"\nSolver finished with status code: {model.Status}")
