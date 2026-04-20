import gurobipy as gp
from gurobipy import GRB
import json
import os
import csv

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
    严格按照《数据说明.md》解析字段。
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
        # 使用 utf-8-sig 处理可能带 BOM 的 CSV 文件（Excel 导出常见）
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                fleet_type = row['机型'].strip()
                fleet_info[fleet_type] = {
                    "count": int(row['飞机数量']),
                    "seats": int(row['座位数']),
                    "cost_per_min": float(row['每小时飞行成本']) / 60.0  # 注意：必须转换为分钟成本
                }
        print("✅ 成功加载 data_fam_fleet.csv")
    except FileNotFoundError:
        print(f"⚠️ 未找到 {csv_file_path}，请确保该 CSV 文件在当前目录中！")
        raise

    # --- 开始转换 14 个 Gurobi 数据结构 ---

    # 1. 提取机队基础属性
    fleets = list(fleet_info.keys())
    total_aircraft = {k: v['count'] for k, v in fleet_info.items()}
    seats = {k: v['seats'] for k, v in fleet_info.items()}

    # 2. 提取产品收益与需求
    products = list(product_info.keys())
    demand = {p: info.get('Total_Demand', 0.0) for p, info in product_info.items()}
    fare = {p: info.get('Fare', 1000.0) for p, info in product_info.items()}

    # 3. 提取航班任务、航段映射、过夜航班与飞行成本
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

    # 4. 构建核心：时空网络节点 (修正了 type 和 flight_id)
    airports = list(airport_timeline.keys())
    airport_nodes_dict = {}

    for airport, events in airport_timeline.items():
        nodes_by_time = {}
        for event in events:
            t = event['time']
            if t not in nodes_by_time:
                nodes_by_time[t] = EventNode(t)
                
            # 根据《数据说明.md》，使用 'flight_id' 和 'type' ('ready' / 'depart')
            task_id = event.get('flight_id') 
            event_type = event.get('type') 
            
            if task_id and event_type:
                # 修复 KeyError：处理 timeline 中的 "AA0051" 与 schedule 中的 "super_AA0051" 名称不匹配的情况
                if task_id not in tasks and f"super_{task_id}" in tasks:
                    task_id = f"super_{task_id}"
                
                # 安全检查：确保只有确实在 schedule 中存在任务，才将其加入网络流，防止孤立节点报错
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
# 3. 你的核心建模函数
# =====================================================================
def build_and_solve_fap_model(
    fleets, tasks, products, all_legs, airports, total_aircraft, seats,
    flight_cost, fare, demand, leg_to_products, leg_to_task_map,
    overnight_tasks, airport_nodes_dict
):
    """
    联合机型分配与网络收益管理模型 (FAP-NRM)
    单日循环排班，时间轴为绝对分钟 [0, 1439]。
    """
    model = gp.Model("FAP_NRM")
    model.setParam('OutputFlag', 1)

    # 1. 决策变量
    x = model.addVars(tasks, fleets, vtype=GRB.BINARY, name="x")

    all_nodes = [node for airport in airports for node in airport_nodes_dict[airport]]
    g = model.addVars(all_nodes, fleets, lb=0.0, vtype=GRB.CONTINUOUS, name="g")

    s = model.addVars(products, lb=0.0, ub=demand, vtype=GRB.CONTINUOUS, name="s")

    # 2. 目标函数：最大化（票价收入 - 飞行成本）
    revenue = gp.quicksum(fare[p] * s[p] for p in products)
    cost = gp.quicksum(
        flight_cost[f, k] * x[f, k]
        for f in tasks
        for k in fleets
        if (f, k) in flight_cost
    )
    model.setObjective(revenue - cost, GRB.MAXIMIZE)

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

    # 3D. 约束 D：航段容量约束
    for l in all_legs:
        parent_task = leg_to_task_map[l]
        demand_on_leg = gp.quicksum(s[p] for p in leg_to_products.get(l, []))
        capacity_of_leg = gp.quicksum(seats[k] * x[parent_task, k] for k in fleets)

        model.addConstr(
            demand_on_leg <= capacity_of_leg,
            name=f"leg_capacity[{l}]"
        )

    # 4. 求解
    model.optimize()

    return model, x, g, s

# =====================================================================
# 4. 运行与结果解析及导出
# =====================================================================
if __name__ == "__main__":
    # 从真实 JSON 文件所在目录加载数据 (假设脚本和 json 在同一文件夹下)
    data_tuple = load_real_data(data_dir=".")
    
    model, x, g, s = build_and_solve_fap_model(*data_tuple)
    
    if model.Status == GRB.OPTIMAL:
        print("\n" + "="*50)
        print(f"🎉 求解成功！最大总利润: ¥ {model.ObjVal:,.2f}")
        print("="*50)
        
        print("\n💾 正在将完整结果导出为 CSV 文件...")
        fleets = data_tuple[0]
        tasks = data_tuple[1]
        products = data_tuple[2]
        airports = data_tuple[4]
        demand = data_tuple[9]
        leg_to_products = data_tuple[10]
        leg_to_task_map = data_tuple[11]
        airport_nodes_dict = data_tuple[13]

        # ==========================================
        # 导出 1：构建产品销量与运力分配综合分析宽表
        # ==========================================
        
        # 构建 任务 -> 分配机型 的映射
        task_to_fleet = {}
        for f in tasks:
            for k in fleets:
                if x[f, k].X > 0.5:
                    task_to_fleet[f] = k

        # 构建 产品 -> 航段 的映射
        product_to_legs = {p: [] for p in products}
        for leg, prods in leg_to_products.items():
            for p in prods:
                if p in product_to_legs:
                    product_to_legs[p].append(leg)

        # 组装综合分析宽表数据
        comprehensive_records = []
        for p in products:
            sold = s[p].X
            if sold > 0.01: 
                p_legs = product_to_legs.get(p, [])
                p_tasks = [leg_to_task_map.get(l) for l in p_legs if l in leg_to_task_map]
                p_fleets = [task_to_fleet.get(t, "Unassigned") for t in p_tasks]
                
                comprehensive_records.append({
                    "Product": p,
                    "Max_Demand": demand[p],
                    "Sold_Tickets": round(sold, 2),
                    "Legs": " -> ".join(p_legs),
                    "Tasks": " -> ".join(p_tasks),
                    "Assigned_Fleets": " -> ".join(p_fleets)
                })

        with open('result_comprehensive_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = [
                "Product", "Max_Demand", "Sold_Tickets", 
                "Legs", "Tasks", "Assigned_Fleets"
            ]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comprehensive_records)

        # ==========================================
        # 导出 2：跨日地面驻场状态 (午夜0点)
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

        with open('result_ground_status.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=["Airport", "Fleet", "Grounded_Count"])
            writer.writeheader()
            writer.writerows(ground_records)

        print("✅ 导出完成！请在当前目录下查看以下文件：")
        print("   - result_comprehensive_analysis.csv (产品销量与运力分配综合宽表)")
        print("   - result_ground_status.csv          (各机场机型过夜停场明细)")
        print("\n快把这些数据放到 Excel 里做图表分析吧！")

    elif model.Status == GRB.INFEASIBLE:
        print("\n❌ 模型未能找到最优解，发生约束冲突 (Infeasible)。")
        print("💡 建议：")
        print("1. 检查物理总机队数量是否足以覆盖所有的航班起降循环。")
        print("2. 检查是否有特定的航线循环无法闭环（如某机场只进不出）。")
        # 如果需要，可调用 model.computeIIS() 进行详细诊断
    else:
        print(f"\n⚠️ 求解结束，状态码：{model.Status}")