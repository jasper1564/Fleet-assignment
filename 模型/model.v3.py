import gurobipy as gp
from gurobipy import GRB
import json
import os
import csv
import numpy as np  # 新增：用于生成正态分布的随机需求场景

# =====================================================================
# 1. 基础数据结构定义
# =====================================================================
class EventNode:
    def __init__(self, time):
        self.time = time
        self.landing_tasks = []   # 在此时刻降落并完成过站（ready）的任务
        self.departing_tasks = [] # 在此时刻起飞（depart）的任务
    
    def __repr__(self):
        return f"Node(time={self.time}, arr={self.landing_tasks}, dep={self.departing_tasks})"

# =====================================================================
# 2. 从 JSON 文件读取真实数据
# =====================================================================
def load_real_data(data_dir="."):
    """
    从本地读取数据清洗后的 JSON 文件，并构造为 Gurobi 模型所需的 14 个基础数据结构。
    """
    print(f"🔄 正在从 '{data_dir}' 目录加载 JSON 数据...")
    
    with open(os.path.join(data_dir, 'updated_product_info.json'), 'r', encoding='utf-8') as f:
        product_info = json.load(f)
    with open(os.path.join(data_dir, 'super_flight_schedule.json'), 'r', encoding='utf-8') as f:
        super_flight_schedule = json.load(f)
    with open(os.path.join(data_dir, 'airport_timeline.json'), 'r', encoding='utf-8') as f:
        airport_timeline = json.load(f)
    with open(os.path.join(data_dir, 'leg_to_products.json'), 'r', encoding='utf-8') as f:
        leg_to_products = json.load(f)
        
    # 从 CSV 文件读取机队信息
    fleet_info = {}
    csv_file_path = os.path.join(data_dir, 'data_fam_fleet.csv')
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fleet_type = row['机型'].strip()
                fleet_info[fleet_type] = {
                    "count": int(row['飞机数量']),
                    "seats": int(row['座位数']),
                    "cost_per_min": float(row['每小时飞行成本']) / 60.0  # 转换为分钟成本
                }
        print("✅ 成功加载 data_fam_fleet.csv")
    except FileNotFoundError:
        print(f"⚠️ 未找到 {csv_file_path}，请确保该 CSV 文件在当前目录中！")
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

    print("✅ JSON 数据加载并转换为网络图完毕！")
    return (fleets, tasks, products, all_legs, airports, total_aircraft, seats, 
            flight_cost, fare, demand, leg_to_products, leg_to_task_map, 
            overnight_tasks, airport_nodes_dict)

# =====================================================================
# 3. 两阶段随机规划核心建模函数 (引入鲁棒性)
# =====================================================================
def build_and_solve_fap_model_stochastic(
    fleets, tasks, products, all_legs, airports, total_aircraft, seats,
    flight_cost, fare, demand, leg_to_products, leg_to_task_map,
    overnight_tasks, airport_nodes_dict,
    num_scenarios=20, volatility=0.20
):
    model = gp.Model("FAP_NRM_Stochastic")
    model.setParam('OutputFlag', 1)

    print(f"\n🎲 正在生成 {num_scenarios} 个需求随机场景 (设定波动率: {volatility*100}%)...")
    
    # 0. 蒙特卡洛需求场景生成
    scenarios = list(range(num_scenarios))
    prob = 1.0 / num_scenarios  # 假设每个场景发生概率均等
    stochastic_demand = {}
    
    np.random.seed(42) # 固定随机种子，保证每次调试生成的场景一致
    for p in products:
        mu = demand.get(p, 0)
        sigma = mu * volatility
        samples = np.random.normal(loc=mu, scale=sigma, size=num_scenarios)
        stochastic_demand[p] = {w: max(0.0, round(samples[w])) for w in scenarios}

    # 1. 第一阶段决策变量：机型分配与飞机地面流转（不随场景改变）
    x = model.addVars(tasks, fleets, vtype=GRB.BINARY, name="x")
    all_nodes = [node for airport in airports for node in airport_nodes_dict[airport]]
    g = model.addVars(all_nodes, fleets, lb=0.0, vtype=GRB.CONTINUOUS, name="g")
    
    # 第二阶段决策变量：不同场景下的实际售票量（随场景波动）
    s = model.addVars(products, scenarios, lb=0.0, vtype=GRB.CONTINUOUS, name="s")

    # 售票量不能超过特定场景下的随机需求上限
    model.addConstrs((s[p, w] <= stochastic_demand[p][w] 
                      for p in products for w in scenarios), name="demand_ub")

    # 2. 目标函数：最大化（期望票价收入 - 固定飞行成本）
    expected_revenue = gp.quicksum(prob * fare[p] * s[p, w] for p in products for w in scenarios)
    cost = gp.quicksum(flight_cost[f, k] * x[f, k] for f in tasks for k in fleets if (f, k) in flight_cost)
    model.setObjective(expected_revenue - cost, GRB.MAXIMIZE)

    # 3A. 约束 A：唯一性约束
    model.addConstrs((gp.quicksum(x[f, k] for k in fleets) == 1 for f in tasks), name="task_cover")

    # 3B. 约束 B：流平衡与跨日循环约束
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

    # 3C. 约束 C：可用机队规模约束
    for k in fleets:
        last_nodes = [airport_nodes_dict[airport][-1] for airport in airports]
        ground_at_midnight = gp.quicksum(g[n, k] for n in last_nodes)
        airborne_overnight = gp.quicksum(x[f, k] for f in overnight_tasks)
        model.addConstr(
            ground_at_midnight + airborne_overnight <= total_aircraft[k],
            name=f"fleet_count[{k}]"
        )

    # 3D. 约束 D：航段容量约束 (必须在【每一个场景】下都满足物理座位限制)
    print("⚙️ 正在构建多场景航段容量约束...")
    for w in scenarios:
        for l in all_legs:
            parent_task = leg_to_task_map[l]
            demand_on_leg = gp.quicksum(s[p, w] for p in leg_to_products.get(l, []))
            capacity_of_leg = gp.quicksum(seats[k] * x[parent_task, k] for k in fleets)
            model.addConstr(demand_on_leg <= capacity_of_leg, name=f"leg_capacity[{l}_{w}]")

    # 4. 求解
    model.optimize()
    return model, x, g, s, stochastic_demand, scenarios

# =====================================================================
# 4. 运行与结果解析及导出 (多场景期望值版本)
# =====================================================================
if __name__ == "__main__":
    # 可以通过修改 num_scenarios 和 volatility 调整鲁棒性强度
    NUM_SCENARIOS = 20
    VOLATILITY = 0.20
    
    data_tuple = load_real_data(data_dir=".")
    
    # 解包部分基础数据以便后续导出使用
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
        print(f"🎉 鲁棒性求解成功！最大期望总利润: ¥ {model.ObjVal:,.2f}")
        print("="*60)
        
        print("\n💾 正在将多场景期望结果导出为 CSV 文件...")

        # --- 基础映射缓存 ---
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
        # 导出 1：构建产品销量与运力分配综合分析宽表 (期望值)
        # ==========================================
        comprehensive_records = []
        for p in products:
            # 计算各场景下的平均售票量和平均需求
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

        with open('result_comprehensive_analysis_robust.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Product", "Expected_Demand", "Expected_Sold", "Expected_Unmet", "Legs", "Tasks", "Assigned_Fleets"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comprehensive_records)

        # ==========================================
        # 导出 2：跨日地面驻场状态 (第一阶段变量，保持不变)
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

        with open('result_ground_status_robust.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=["Airport", "Fleet", "Grounded_Count"])
            writer.writeheader()
            writer.writerows(ground_records)

        # ==========================================
        # 导出 3：航段期望影子价格 (Bid Price)
        # ==========================================
        print("🔍 正在计算网络航段期望影子价格(Expected Bid Prices)...")
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
                
                # 增加一个物理座位的期望价值 = 各场景该约束 Pi 值的总和
                expected_shadow_price = total_pi
                
                shadow_price_records.append({
                    "Leg": l,
                    "Expected_Shadow_Price": round(expected_shadow_price, 2)
                })
            with open('result_shadow_prices_robust.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=["Leg", "Expected_Shadow_Price"])
                writer.writeheader()
                writer.writerows(shadow_price_records)

        # ==========================================
        # 导出 4：航段真实客座率探针 (期望值)
        # ==========================================
        leg_load_records = []
        for l in all_legs:
            parent_task = leg_to_task_map.get(l)
            assigned_fleet = task_to_fleet.get(parent_task, "Unknown")
            assigned_seats = seats.get(assigned_fleet, 0)
            
            # 计算所有场景下，该航段上的平均总客流
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

        with open('result_leg_load_factor_robust.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Leg", "Parent_Task", "Assigned_Fleet", "Seat_Capacity", 
                          "Expected_Passengers", "Expected_Load_Factor(%)"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(leg_load_records)

        print("✅ 导出完成！请在当前目录下查看以下文件 (带 _robust 后缀)：")
        print("   - result_comprehensive_analysis_robust.csv")
        print("   - result_ground_status_robust.csv")
        print("   - result_shadow_prices_robust.csv")
        print("   - result_leg_load_factor_robust.csv")

    elif model.Status == GRB.INFEASIBLE:
        print("\n❌ 模型未能找到最优解，发生约束冲突 (Infeasible)。")
    else:
        print(f"\n⚠️ 求解结束，状态码：{model.Status}")