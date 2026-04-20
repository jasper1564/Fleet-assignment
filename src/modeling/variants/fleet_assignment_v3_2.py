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
RESULTS_DIR = ROOT / 'results' / 'runs' / 'variants' / 'v3_2'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_leg_code(leg):
    """Parse a leg code like AA0040BERBOD into task, origin and destination."""
    leg_str = str(leg)
    if len(leg_str) >= 12:
        return {
            "task": leg_str[:6],
            "origin": leg_str[6:9],
            "destination": leg_str[9:12],
        }
    return {
        "task": leg_str[:6],
        "origin": "",
        "destination": "",
    }

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
# 2. 钂欑壒鍗℃礇闇€姹傚満鏅敓鎴?
# =====================================================================
def generate_demand_scenarios(demand, n_scenarios=20, cv=0.2, dist="negbinom", seed=42):
    """
    鍩轰簬鍘嗗彶鍧囧€奸渶姹傦紝浣跨敤钂欑壒鍗℃礇鏂规硶鐢熸垚 N 涓渶姹傚満鏅€?

    鍙傛暟璇存槑锛?
    ----------
    demand      : dict {product: mean_demand}锛屼粠 JSON 鍔犺浇鐨勫巻鍙插潎鍊奸渶姹?
    n_scenarios : int锛岀敓鎴愮殑鍦烘櫙鏁伴噺锛屽缓璁?100~500锛堣秺澶氳秺绋冲仴锛屼絾姹傝В瓒婃參锛?
    cv          : float锛屽彉寮傜郴鏁?(Coefficient of Variation = std / mean)
                  寤鸿鍙栧€艰寖鍥?0.1~0.3锛屽吀鍨嬭埅绌洪渶姹傚彇 0.2
    dist        : str锛岄噰鏍峰垎甯冪被鍨嬶細
                  - "negbinom"  璐熶簩椤瑰垎甯冿紙鎺ㄨ崘锛夛細閫傚悎鑸┖闇€姹傦紝鑳借嚜鐒舵崟鎹夎繃绂绘暎鎬?
                  - "lognormal" 瀵规暟姝ｆ€佸垎甯冿細閫傚悎鏀剁泭绠＄悊鍦烘櫙锛屽彸鍋忥紝涓嶄細鍑虹幇璐熷€?
                  - "normal"    姝ｆ€佸垎甯冿細绠€鍗曞绉帮紝鍙兘浜х敓璐熷€硷紙浼氳鎴柇涓?0锛?
    seed        : int锛岄殢鏈虹瀛愶紝淇濊瘉瀹為獙鍙鐜?

    杩斿洖锛?
    ------
    scenarios   : list of dict锛岄暱搴?n_scenarios锛屾瘡涓厓绱犱负 {product: sampled_demand}
    """
    rng = np.random.default_rng(seed)
    products = list(demand.keys())
    scenarios = []

    for _ in range(n_scenarios):
        scenario = {}
        for p in products:
            mu = demand[p]
            if mu <= 0:
                scenario[p] = 0.0
                continue

            sigma = cv * mu  # 鏍囧噯宸?

            if dist == "negbinom":
                # 璐熶簩椤瑰垎甯冨弬鏁帮細mu, r锛堢鏁ｅ弬鏁帮級
                # r = mu^2 / (sigma^2 - mu)锛屽綋 sigma^2 > mu 鏃舵湁鎰忎箟锛堣繃绂绘暎锛?
                var = sigma ** 2
                if var <= mu:
                    # 鏂瑰樊 <= 鍧囧€兼椂閫€鍖栦负娉婃澗鍒嗗竷
                    sampled = float(rng.poisson(mu))
                else:
                    r = mu ** 2 / (var - mu)
                    p_nb = r / (r + mu)
                    sampled = float(rng.negative_binomial(r, p_nb))

            elif dist == "lognormal":
                # 瀵规暟姝ｆ€佸弬鏁版帹瀵硷細mu_ln, sigma_ln
                sigma_ln = np.sqrt(np.log(1 + (sigma / mu) ** 2))
                mu_ln = np.log(mu) - 0.5 * sigma_ln ** 2
                sampled = float(rng.lognormal(mu_ln, sigma_ln))

            elif dist == "normal":
                sampled = float(rng.normal(mu, sigma))
                sampled = max(sampled, 0.0)  # 鎴柇璐熷€?

            else:
                raise ValueError(f"鏈煡鍒嗗竷绫诲瀷: {dist}锛岃閫夋嫨 'negbinom', 'lognormal' 鎴?'normal'")

            scenario[p] = round(sampled, 4)
        scenarios.append(scenario)

    # 鎵撳嵃鍦烘櫙缁熻鎽樿
    print(f"\nGenerated demand scenarios: dist={dist}, N={n_scenarios}, CV={cv}")
    sample_product = products[0]
    sampled_vals = [s[sample_product] for s in scenarios]
    print(f"   绀轰緥浜у搧 [{sample_product}]锛氬潎鍊奸渶姹?{demand[sample_product]:.1f}, "
          f"鍦烘櫙鍧囧€?{np.mean(sampled_vals):.1f}, "
          f"鍦烘櫙鏍囧噯宸?{np.std(sampled_vals):.1f}, "
          f"鍦烘櫙鑼冨洿=[{np.min(sampled_vals):.1f}, {np.max(sampled_vals):.1f}]")

    return scenarios

# =====================================================================
# 3. 浠?JSON 鏂囦欢璇诲彇鐪熷疄鏁版嵁
# =====================================================================
def load_real_data(data_dir=None):
    """
    浠庢湰鍦拌鍙栨暟鎹竻娲楀悗鐨?JSON 鏂囦欢锛屽苟鏋勯€犱负 Gurobi 妯″瀷鎵€闇€鐨?14 涓熀纭€鏁版嵁缁撴瀯銆?
    涓ユ牸鎸夌収銆婃暟鎹鏄?md銆嬭В鏋愬瓧娈点€?
    """
    print(f"馃攧 姝ｅ湪浠?'{data_dir}' 鐩綍鍔犺浇 JSON 鏁版嵁...")
    
    with open(DEMAND_INPUT_DIR / 'product_info_rf_predicted.json', 'r', encoding='utf-8') as f:
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

    # 1. 鎻愬彇鏈洪槦鍩虹灞炴€?
    fleets = list(fleet_info.keys())
    total_aircraft = {k: v['count'] for k, v in fleet_info.items()}
    seats = {k: v['seats'] for k, v in fleet_info.items()}

    # 2. 鎻愬彇浜у搧鏀剁泭涓庨渶姹傦紙鍧囧€硷紝鐢ㄤ簬鍦烘櫙鐢熸垚锛?
    products = list(product_info.keys())
    demand = {p: info.get('Total_Demand', 0.0) for p, info in product_info.items()}
    fare = {p: info.get('Fare', 1000.0) for p, info in product_info.items()}

    # 3. 鎻愬彇鑸彮浠诲姟銆佽埅娈垫槧灏勩€佽繃澶滆埅鐝笌椋炶鎴愭湰
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

    # 4. 鏋勫缓鏍稿績锛氭椂绌虹綉缁滆妭鐐?
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
# 4. 鏍稿績寤烘ā鍑芥暟锛堜袱闃舵闅忔満瑙勫垝 + SAA锛?
# =====================================================================
def build_and_solve_fap_model(
    fleets, tasks, products, all_legs, airports, total_aircraft, seats,
    flight_cost, fare, demand, leg_to_products, leg_to_task_map,
    overnight_tasks, airport_nodes_dict,
    # --- 鏂板锛氳挋鐗瑰崱娲涢殢鏈鸿鍒掑弬鏁?---
    n_scenarios=200,
    demand_cv=0.2,
    demand_dist="negbinom",
    mc_seed=42,
    mip_gap=5e-4
):
    """
    涓ら樁娈甸殢鏈鸿鍒掞紙Extensive Form / SAA锛夛細

    绗竴闃舵锛堟鍒诲喅绛栵紝闇€姹備笉纭畾锛夛細
        x[f,k]  鈭?{0,1}  鈫?鏈哄瀷鍒嗛厤锛屽繀椤诲湪闇€姹傚疄鐜板墠纭畾

    绗簩闃舵锛堥渶姹傚疄鐜板悗鐨勬渶浼樺搷搴旓級锛?
        s[p,n]  鈮?0      鈫?鍦烘櫙 n 涓嬩骇鍝?p 鐨勫疄闄呭敭绁ㄩ噺

    鐩爣锛氭渶澶у寲鏈熸湜鍒╂鼎
        max  -危(f,k) cost[f,k]路x[f,k]  +  (1/N)路危_n 危_p fare[p]路s[p,n]

    鍏抽敭绾︽潫鍙樺寲锛?
        绾︽潫 D锛堝閲忥級锛氬姣忎釜鍦烘櫙 n锛岄渶姹傚彉閲?s[p,n] 鍙楄鍦烘櫙闇€姹備笂鐣屽拰杩愬姏鍏卞悓绾︽潫
    """
    # --- Step 1: 鐢熸垚钂欑壒鍗℃礇闇€姹傚満鏅?---
    scenarios = generate_demand_scenarios(
        demand, n_scenarios=n_scenarios, cv=demand_cv, dist=demand_dist, seed=mc_seed
    )
    scenario_ids = list(range(n_scenarios))
    prob = 1.0 / n_scenarios  # 绛夋鐜囧満鏅紙SAA 鏍囧噯鍋囪锛?

    # --- Step 2: 鏋勫缓妯″瀷 ---
    model = gp.Model("FAP_NRM_Stochastic")
    model.setParam('OutputFlag', 1)
    model.setParam('MIPGap', mip_gap)

    # 鈹€鈹€ 绗竴闃舵鍙橀噺锛堜笌闇€姹傛棤鍏筹紝鍏ㄥ眬鍏变韩锛夆攢鈹€
    x = model.addVars(tasks, fleets, vtype=GRB.BINARY, name="x")
    all_nodes = [node for airport in airports for node in airport_nodes_dict[airport]]
    g = model.addVars(all_nodes, fleets, lb=0.0, vtype=GRB.CONTINUOUS, name="g")

    # 鈹€鈹€ 绗簩闃舵鍙橀噺锛堟瘡涓満鏅嫭绔嬶紝s[p,n] 涓婄晫鐢卞悇鍦烘櫙闇€姹傚喅瀹氾級鈹€鈹€
    # 娉ㄦ剰锛氫笂鐣岄渶鍦ㄦ坊鍔犲彉閲忓悗閫氳繃绾︽潫鏂藉姞锛屼互渚挎瘡涓満鏅娇鐢ㄤ笉鍚岀殑闇€姹傚€?
    s = model.addVars(products, scenario_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="s")

    # 涓烘瘡涓満鏅柦鍔犻渶姹備笂鐣岀害鏉燂紙鏇夸唬鐩存帴璁?ub锛屼互渚挎寜鍦烘櫙宸紓鍖栵級
    for n in scenario_ids:
        for p in products:
            model.addConstr(
                s[p, n] <= scenarios[n][p],
                name=f"demand_ub[{p},{n}]"
            )

    # 鈹€鈹€ 鐩爣鍑芥暟锛氭湡鏈涘埄娑︽渶澶у寲 鈹€鈹€
    # 椋炶鎴愭湰锛氱‘瀹氭€э紙绗竴闃舵锛夛紝涓庡満鏅棤鍏?
    cost = gp.quicksum(
        flight_cost[f, k] * x[f, k]
        for f in tasks for k in fleets if (f, k) in flight_cost
    )
    # 鏈熸湜绁ㄥ姟鏀跺叆锛氭墍鏈夊満鏅殑鍔犳潈骞冲潎锛堢瓑鏉冮噸 = 1/N锛?
    expected_revenue = prob * gp.quicksum(
        fare[p] * s[p, n]
        for p in products for n in scenario_ids
    )
    model.setObjective(expected_revenue - cost, GRB.MAXIMIZE)

    # 鈹€鈹€ 绾︽潫 A锛氬敮涓€鎬х害鏉燂紙涓庡師妯″瀷鐩稿悓锛屼笉鍙楀満鏅奖鍝嶏級鈹€鈹€
    model.addConstrs(
        (gp.quicksum(x[f, k] for k in fleets) == 1 for f in tasks),
        name="task_cover"
    )

    # 鈹€鈹€ 绾︽潫 B锛氭祦骞宠　涓庤法鏃ュ惊鐜害鏉燂紙涓庡師妯″瀷鐩稿悓锛夆攢鈹€
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

    # 鈹€鈹€ 绾︽潫 C锛氬彲鐢ㄦ満闃熻妯＄害鏉燂紙涓庡師妯″瀷鐩稿悓锛夆攢鈹€
    for k in fleets:
        last_nodes = [airport_nodes_dict[airport][-1] for airport in airports]
        ground_at_midnight = gp.quicksum(g[n, k] for n in last_nodes)
        airborne_overnight = gp.quicksum(x[f, k] for f in overnight_tasks)
        model.addConstr(
            ground_at_midnight + airborne_overnight <= total_aircraft[k],
            name=f"fleet_count[{k}]"
        )

    # 鈹€鈹€ 绾︽潫 D锛堥殢鏈哄寲锛夛細鑸瀹归噺绾︽潫锛屽姣忎釜鍦烘櫙鍒嗗埆鏂藉姞 鈹€鈹€
    # 杩愬姏鐢辩涓€闃舵鍐崇瓥 x 鍐冲畾锛堢‘瀹氭€э級锛屼絾闇€姹傛潵鑷悇鍦烘櫙
    for l in all_legs:
        parent_task = leg_to_task_map[l]
        capacity_of_leg = gp.quicksum(seats[k] * x[parent_task, k] for k in fleets)
        for n in scenario_ids:
            demand_on_leg_n = gp.quicksum(s[p, n] for p in leg_to_products.get(l, []))
            model.addConstr(
                demand_on_leg_n <= capacity_of_leg,
                name=f"leg_capacity[{l},{n}]"
            )

    # --- Step 3: 姹傝В ---
    model.optimize()
    return model, x, g, s, scenarios

# =====================================================================
# 5. 杩愯涓庣粨鏋滆В鏋愬強瀵煎嚭
# =====================================================================
if __name__ == "__main__":
    # 鈹€鈹€ 钂欑壒鍗℃礇鍙傛暟閰嶇疆锛堝彲鎸夐渶璋冩暣锛夆攢鈹€
    MC_N_SCENARIOS = 50   # 鍦烘櫙鏁伴噺锛氳秺澶ц秺绋冲仴锛屼絾妯″瀷瑙勬ā绾挎€у闀?
    MC_CV          = 0.20  # 闇€姹傚彉寮傜郴鏁帮細0.1=浣庢尝鍔? 0.2=涓瓑(鎺ㄨ崘), 0.3=楂樻尝鍔?
    MC_DIST        = "negbinom"  # 鍒嗗竷绫诲瀷锛?negbinom" / "lognormal" / "normal"
    MC_SEED        = 42    # 闅忔満绉嶅瓙

    SOLVE_MIP_GAP  = 5e-4

    data_tuple = load_real_data()
    model, x, g, s, scenarios = build_and_solve_fap_model(
        *data_tuple,
        n_scenarios=MC_N_SCENARIOS,
        demand_cv=MC_CV,
        demand_dist=MC_DIST,
        mc_seed=MC_SEED,
        mip_gap=SOLVE_MIP_GAP,
    )
    
    if model.Status == GRB.OPTIMAL:
        print("\n" + "="*55)
        print(f"馃帀 姹傝В鎴愬姛锛佹渶澶ф湡鏈涙€诲埄娑? 楼 {model.ObjVal:,.2f}")
        print(f"   (鍩轰簬 {MC_N_SCENARIOS} 涓挋鐗瑰崱娲涢渶姹傚満鏅紝CV={MC_CV}锛屽垎甯?{MC_DIST})")
        print("="*55)
        
        print("\n馃捑 姝ｅ湪灏嗗畬鏁寸粨鏋滃鍑轰负 CSV 鏂囦欢...")
        fleets    = data_tuple[0]
        tasks     = data_tuple[1]
        products  = data_tuple[2]
        all_legs  = data_tuple[3]
        airports  = data_tuple[4]
        total_aircraft = data_tuple[5]
        seats     = data_tuple[6]
        flight_cost = data_tuple[7]
        fare = data_tuple[8]
        demand    = data_tuple[9]  # 鍘熷鍘嗗彶鍧囧€奸渶姹?
        leg_to_products = data_tuple[10]
        leg_to_task_map = data_tuple[11]
        airport_nodes_dict = data_tuple[13]
        scenario_ids = list(range(MC_N_SCENARIOS))
        with open(NETWORK_INPUT_DIR / 'super_flight_schedule.json', 'r', encoding='utf-8') as f:
            super_flight_schedule = json.load(f)

        # ---------------------------------------------------------
        # 鏋勫缓鍩虹鏄犲皠缂撳瓨
        # ---------------------------------------------------------
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

        task_to_legs = {}
        for task in tasks:
            task_to_legs[task] = list(super_flight_schedule.get(task, {}).get("legs", []))

        # ==========================================
        # 瀵煎嚭 1锛氫骇鍝侀攢閲忕患鍚堝垎鏋愶紙鍦烘櫙缁熻姹囨€伙級
        # ==========================================
        comprehensive_records = []
        for p in products:
            # 璺ㄥ満鏅绠楁湡鏈涢攢閲忎笌缁熻鐗瑰緛
            sold_across_scenarios = [s[p, n].X for n in scenario_ids]
            mean_sold    = float(np.mean(sold_across_scenarios))
            std_sold     = float(np.std(sold_across_scenarios))
            p5_sold      = float(np.percentile(sold_across_scenarios, 5))
            p95_sold     = float(np.percentile(sold_across_scenarios, 95))
            mean_demand  = float(np.mean([scenarios[n][p] for n in scenario_ids]))
            mean_unmet   = mean_demand - mean_sold

            if mean_sold > 0.01:
                p_legs   = product_to_legs.get(p, [])
                p_tasks  = [leg_to_task_map.get(l) for l in p_legs if l in leg_to_task_map]
                p_fleets = [task_to_fleet.get(t, "Unassigned") for t in p_tasks]

                comprehensive_records.append({
                    "Product":            p,
                    "Historical_Demand":  round(demand[p], 2),      # 鍘熷鍘嗗彶鍧囧€?
                    "MC_Mean_Demand":     round(mean_demand, 2),     # 钂欑壒鍗℃礇鍦烘櫙鍧囧€?
                    "Expected_Sold":      round(mean_sold, 2),       # 鏈熸湜閿€閲?
                    "Std_Sold":           round(std_sold, 2),        # 閿€閲忔爣鍑嗗樊
                    "P5_Sold":            round(p5_sold, 2),         # 5%鍒嗕綅鏁帮紙鎮茶鎯呮櫙锛?
                    "P95_Sold":           round(p95_sold, 2),        # 95%鍒嗕綅鏁帮紙涔愯鎯呮櫙锛?
                    "Expected_Unmet":     round(mean_unmet, 2),      # 鏈熸湜鏈弧瓒抽渶姹?
                    "Legs":               " -> ".join(p_legs),
                    "Tasks":              " -> ".join(p_tasks),
                    "Assigned_Fleets":    " -> ".join(p_fleets)
                })

        with open(RESULTS_DIR / 'comprehensive_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Product", "Historical_Demand", "MC_Mean_Demand", "Expected_Sold",
                          "Std_Sold", "P5_Sold", "P95_Sold", "Expected_Unmet",
                          "Legs", "Tasks", "Assigned_Fleets"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comprehensive_records)

        # ==========================================
        # 瀵煎嚭 2锛氳法鏃ュ湴闈㈤┗鍦虹姸鎬侊紙涓庡師妯″瀷涓€鑷达級
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
        # 瀵煎嚭 3锛氳埅娈靛奖瀛愪环鏍硷紙Bid Price锛屽満鏅潎鍊硷級
        # ==========================================
        print("馃攳 姝ｅ湪璁＄畻缃戠粶鑸鏈熸湜褰卞瓙浠锋牸(Expected Bid Prices)...")
        fixed_model = model.fixed()
        fixed_model.setParam('OutputFlag', 0)
        fixed_model.optimize()
        shadow_price_map = {}

        if fixed_model.Status == GRB.OPTIMAL:
            shadow_price_records = []
            for l in all_legs:
                # 瀵规瘡涓満鏅殑褰卞瓙浠锋牸鍙栧潎鍊硷紝寰楀埌鏈熸湜 Bid Price
                pi_vals = []
                for n in scenario_ids:
                    constr = fixed_model.getConstrByName(f"leg_capacity[{l},{n}]")
                    if constr:
                        pi_vals.append(constr.Pi)
                if pi_vals:
                    shadow_price_map[l] = {
                        "expected": float(np.mean(pi_vals)),
                        "std": float(np.std(pi_vals)),
                        "p5": float(np.percentile(pi_vals, 5)),
                        "p95": float(np.percentile(pi_vals, 95)),
                    }
                    shadow_price_records.append({
                        "Leg":                l,
                        "Expected_Shadow_Price": round(float(np.mean(pi_vals)), 4),
                        "Std_Shadow_Price":      round(float(np.std(pi_vals)), 4),
                        "P5_Shadow_Price":       round(float(np.percentile(pi_vals, 5)), 4),
                        "P95_Shadow_Price":      round(float(np.percentile(pi_vals, 95)), 4),
                    })
            with open(RESULTS_DIR / 'shadow_prices.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
                fieldnames = ["Leg", "Expected_Shadow_Price", "Std_Shadow_Price",
                              "P5_Shadow_Price", "P95_Shadow_Price"]
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(shadow_price_records)

        # ==========================================
        # 瀵煎嚭 4锛氳埅娈靛搴х巼锛堝満鏅潎鍊间笌鍒嗗竷锛?
        # ==========================================
        leg_load_records = []
        leg_stats_map = {}
        for l in all_legs:
            parent_task   = leg_to_task_map.get(l)
            assigned_fleet = task_to_fleet.get(parent_task, "Unknown")
            assigned_seats = seats.get(assigned_fleet, 0)
            
            # 閫愬満鏅绠楀搴х巼
            load_factors = []
            for n in scenario_ids:
                pax_n = sum(s[p, n].X for p in leg_to_products.get(l, []))
                lf_n  = (pax_n / assigned_seats * 100) if assigned_seats > 0 else 0
                load_factors.append(lf_n)

            mean_lf  = float(np.mean(load_factors))
            # 璇嗗埆鐡堕锛氬鏋滆秴杩?50% 鐨勫満鏅腑瀹㈠骇鐜囪揪鍒?100% 涓斿瓨鍦ㄦ孩鍑洪渶姹?
            bottleneck_freq = sum(1 for lf in load_factors if lf >= 99.9) / MC_N_SCENARIOS
            expected_passengers = float(np.mean(
                [sum(s[p, n].X for p in leg_to_products.get(l, [])) for n in scenario_ids]
            ))
            leg_stats_map[l] = {
                "parent_task": parent_task,
                "assigned_fleet": assigned_fleet,
                "seat_capacity": assigned_seats,
                "expected_passengers": expected_passengers,
                "expected_load": mean_lf,
                "p5_load": float(np.percentile(load_factors, 5)),
                "p95_load": float(np.percentile(load_factors, 95)),
                "bottleneck_freq": bottleneck_freq * 100,
            }

            leg_load_records.append({
                "Leg":                  l,
                "Parent_Task":          parent_task,
                "Assigned_Fleet":       assigned_fleet,
                "Seat_Capacity":        assigned_seats,
                "Expected_Passengers":  round(expected_passengers, 2),
                "Expected_Load(%)":     round(mean_lf, 2),
                "P5_Load(%)":           round(float(np.percentile(load_factors, 5)), 2),
                "P95_Load(%)":          round(float(np.percentile(load_factors, 95)), 2),
                "Bottleneck_Freq(%)":   round(bottleneck_freq * 100, 1),  # 婊¤埍鍦烘櫙鍗犳瘮
            })

        with open(RESULTS_DIR / 'leg_load_factor.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Leg", "Parent_Task", "Assigned_Fleet", "Seat_Capacity",
                          "Expected_Passengers", "Expected_Load(%)",
                          "P5_Load(%)", "P95_Load(%)", "Bottleneck_Freq(%)"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leg_load_records)

        product_stats_map = {}
        task_revenue_map = {task: 0.0 for task in tasks}
        task_products_map = {task: set() for task in tasks}
        leg_revenue_map = {leg: 0.0 for leg in all_legs}

        for record in comprehensive_records:
            product = record["Product"]
            product_legs = product_to_legs.get(product, [])
            product_tasks = [leg_to_task_map.get(l) for l in product_legs if l in leg_to_task_map]
            expected_revenue = fare[product] * record["Expected_Sold"]
            product_stats_map[product] = {
                "expected_demand": record["MC_Mean_Demand"],
                "expected_sold": record["Expected_Sold"],
                "expected_unmet": record["Expected_Unmet"],
                "expected_revenue": expected_revenue,
                "legs": product_legs,
                "tasks": product_tasks,
            }

            if product_legs:
                revenue_per_leg = expected_revenue / len(product_legs)
                for leg in product_legs:
                    leg_revenue_map[leg] = leg_revenue_map.get(leg, 0.0) + revenue_per_leg

            unique_tasks = [t for t in dict.fromkeys(product_tasks) if t]
            if unique_tasks:
                revenue_per_task = expected_revenue / len(unique_tasks)
                for task in unique_tasks:
                    task_revenue_map[task] = task_revenue_map.get(task, 0.0) + revenue_per_task
                    task_products_map.setdefault(task, set()).add(product)

        total_expected_revenue = sum(stats["expected_revenue"] for stats in product_stats_map.values())
        total_operating_cost = sum(
            flight_cost[task, task_to_fleet[task]]
            for task in tasks if task in task_to_fleet and (task, task_to_fleet[task]) in flight_cost
        )
        total_expected_unmet = sum(stats["expected_unmet"] for stats in product_stats_map.values())
        avg_load_factor = float(np.mean([row["Expected_Load(%)"] for row in leg_load_records])) if leg_load_records else 0.0
        high_shadow_price_leg_count = sum(
            1 for leg in all_legs if shadow_price_map.get(leg, {}).get("expected", 0.0) > 0.0
        )

        model_summary_records = [{
            "Scenario_Count": MC_N_SCENARIOS,
            "Demand_CV": MC_CV,
            "Demand_Distribution": MC_DIST,
            "Random_Seed": MC_SEED,
            "Objective_Value": round(float(model.ObjVal), 2),
            "Expected_Revenue": round(total_expected_revenue, 2),
            "Operating_Cost": round(total_operating_cost, 2),
            "Expected_Unmet_Demand": round(total_expected_unmet, 2),
            "Average_Load_Factor(%)": round(avg_load_factor, 2),
            "Positive_Shadow_Price_Leg_Count": high_shadow_price_leg_count,
        }]
        with open(RESULTS_DIR / 'model_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(model_summary_records[0].keys()))
            writer.writeheader()
            writer.writerows(model_summary_records)

        task_summary_records = []
        for task in tasks:
            assigned_fleet = task_to_fleet.get(task, "Unknown")
            task_legs = task_to_legs.get(task, [])
            parsed_first = parse_leg_code(task_legs[0]) if task_legs else {"origin": "", "destination": ""}
            parsed_last = parse_leg_code(task_legs[-1]) if task_legs else {"origin": "", "destination": ""}
            expected_passengers = sum(
                leg_stats_map.get(leg, {}).get("expected_passengers", 0.0) for leg in task_legs
            )
            seat_capacity = seats.get(assigned_fleet, 0)
            task_capacity = seat_capacity * len(task_legs) if task_legs else seat_capacity
            expected_load_pct = (expected_passengers / task_capacity * 100) if task_capacity > 0 else 0.0
            expected_revenue = task_revenue_map.get(task, 0.0)
            operating_cost = flight_cost.get((task, assigned_fleet), 0.0)
            shadow_prices = [shadow_price_map.get(leg, {}).get("expected", 0.0) for leg in task_legs]
            task_summary_records.append({
                "Task": task,
                "Origin": parsed_first.get("origin", ""),
                "Destination": parsed_last.get("destination", ""),
                "Leg_Count": len(task_legs),
                "Legs": " -> ".join(task_legs),
                "Assigned_Fleet": assigned_fleet,
                "Seat_Capacity_Per_Leg": seat_capacity,
                "Task_Capacity": round(task_capacity, 2),
                "Total_Fly_Minutes": super_flight_schedule.get(task, {}).get("total_fly_minutes", 0),
                "Expected_Passengers": round(expected_passengers, 2),
                "Expected_Load(%)": round(expected_load_pct, 2),
                "Attributed_Revenue": round(expected_revenue, 2),
                "Operating_Cost": round(operating_cost, 2),
                "Attributed_Profit": round(expected_revenue - operating_cost, 2),
                "Avg_Shadow_Price": round(float(np.mean(shadow_prices)) if shadow_prices else 0.0, 4),
                "Max_Shadow_Price": round(max(shadow_prices) if shadow_prices else 0.0, 4),
                "Product_Count": len(task_products_map.get(task, set())),
                "Is_Overnight_Task": int(bool(super_flight_schedule.get(task, {}).get("is_overnight", False))),
            })
        with open(RESULTS_DIR / 'task_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(task_summary_records[0].keys()))
            writer.writeheader()
            writer.writerows(task_summary_records)

        fleet_summary_records = []
        for fleet in fleets:
            fleet_tasks = [row for row in task_summary_records if row["Assigned_Fleet"] == fleet]
            grounded_count = sum(
                row["Grounded_Count"] for row in ground_records if row["Fleet"] == fleet
            )
            overnight_count = sum(
                1 for task in tasks
                if task_to_fleet.get(task) == fleet and super_flight_schedule.get(task, {}).get("is_overnight", False)
            )
            fleet_summary_records.append({
                "Fleet": fleet,
                "Available_Aircraft": total_aircraft.get(fleet, 0),
                "Assigned_Task_Count": len(fleet_tasks),
                "Total_Fly_Minutes": round(sum(row["Total_Fly_Minutes"] for row in fleet_tasks), 2),
                "Average_Task_Load(%)": round(float(np.mean([row["Expected_Load(%)"] for row in fleet_tasks])) if fleet_tasks else 0.0, 2),
                "Attributed_Revenue": round(sum(row["Attributed_Revenue"] for row in fleet_tasks), 2),
                "Operating_Cost": round(sum(row["Operating_Cost"] for row in fleet_tasks), 2),
                "Attributed_Profit": round(sum(row["Attributed_Profit"] for row in fleet_tasks), 2),
                "Tasks_Per_Available_Aircraft": round(len(fleet_tasks) / total_aircraft.get(fleet, 1), 2) if total_aircraft.get(fleet, 0) > 0 else 0.0,
                "End_Of_Day_Grounded": round(grounded_count, 2),
                "Overnight_Airborne_Count": overnight_count,
            })
        with open(RESULTS_DIR / 'fleet_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(fleet_summary_records[0].keys()))
            writer.writeheader()
            writer.writerows(fleet_summary_records)

        leg_value_records = []
        for leg in all_legs:
            leg_info = leg_stats_map.get(leg, {})
            parsed_leg = parse_leg_code(leg)
            seat_capacity = leg_info.get("seat_capacity", 0)
            expected_passengers = leg_info.get("expected_passengers", 0.0)
            unit_revenue = (leg_revenue_map.get(leg, 0.0) / expected_passengers) if expected_passengers > 0 else 0.0
            shadow_price = shadow_price_map.get(leg, {}).get("expected", 0.0)
            value_score = leg_revenue_map.get(leg, 0.0) + shadow_price * seat_capacity
            leg_value_records.append({
                "Leg": leg,
                "Task": parsed_leg.get("task", ""),
                "Origin": parsed_leg.get("origin", ""),
                "Destination": parsed_leg.get("destination", ""),
                "Parent_Task": leg_info.get("parent_task", ""),
                "Assigned_Fleet": leg_info.get("assigned_fleet", "Unknown"),
                "Seat_Capacity": seat_capacity,
                "Expected_Passengers": round(expected_passengers, 2),
                "Expected_Load(%)": round(leg_info.get("expected_load", 0.0), 2),
                "Bottleneck_Freq(%)": round(leg_info.get("bottleneck_freq", 0.0), 1),
                "Expected_Shadow_Price": round(shadow_price, 4),
                "Attributed_Revenue": round(leg_revenue_map.get(leg, 0.0), 2),
                "Revenue_Per_Pax": round(unit_revenue, 2),
                "Product_Count": len(leg_to_products.get(leg, [])),
                "Value_Score": round(value_score, 2),
            })
        with open(RESULTS_DIR / 'leg_value_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(leg_value_records[0].keys()))
            writer.writeheader()
            writer.writerows(leg_value_records)

        # ==========================================
        # 瀵煎嚭 5锛堟柊澧烇級锛氬悇鍦烘櫙鍒╂鼎鍒嗗竷鏄庣粏
        # ==========================================
        scenario_profit_records = []
        for n in scenario_ids:
            scenario_revenue = sum(fare[p] * s[p, n].X for p in products)
            # 椋炶鎴愭湰涓虹‘瀹氬€硷紝瀵规墍鏈夊満鏅竴鑷?
            scenario_profit_records.append({
                "Scenario_ID":      n,
                "Scenario_Revenue": round(scenario_revenue, 2),
            })
        
        # 缁熻鍒╂鼎鍒嗗竷鐗瑰緛锛堟垚鏈‘瀹氾紝浠呮敹鍏ユ尝鍔級
        revenues = [r["Scenario_Revenue"] for r in scenario_profit_records]
        print(f"\n馃搱 鏈熸湜鏀跺叆: 楼{np.mean(revenues):,.2f}  |  "
              f"鏍囧噯宸? 楼{np.std(revenues):,.2f}  |  "
              f"P5: 楼{np.percentile(revenues, 5):,.2f}  |  "
              f"P95: 楼{np.percentile(revenues, 95):,.2f}")

        with open(RESULTS_DIR / 'scenario_profit.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=["Scenario_ID", "Scenario_Revenue"])
            writer.writeheader()
            writer.writerows(scenario_profit_records)

        print("\nExport complete. Key outputs:")
        print("   - comprehensive_analysis.csv")
        print("   - ground_status.csv")
        print("   - shadow_prices.csv")
        print("   - leg_load_factor.csv")
        print("   - scenario_profit.csv")

    elif model.Status == GRB.INFEASIBLE:
        print("\nModel is infeasible.")
        print("Suggestions:")
        print("1. Check whether total fleet availability can cover all flight rotations.")
        print("2. Check whether any airport flow is impossible to close into a valid cycle.")
        print("3. Reduce the number of Monte Carlo scenarios if memory becomes a bottleneck.")
    else:
        print(f"\nSolver finished with status code: {model.Status}")

