import gurobipy as gp
from gurobipy import GRB
import json
import os
import csv
import numpy as np


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
# 2. 蒙特卡洛需求场景生成
# =====================================================================
def generate_demand_scenarios(demand, n_scenarios=20, cv=0.2, dist="negbinom", seed=42):
    """
    基于历史均值需求，使用蒙特卡洛方法生成 N 个需求场景。

    参数说明：
    ----------
    demand      : dict {product: mean_demand}，从 JSON 加载的历史均值需求
    n_scenarios : int，生成的场景数量，建议 100~500（越多越稳健，但求解越慢）
    cv          : float，变异系数 (Coefficient of Variation = std / mean)
                  建议取值范围 0.1~0.3，典型航空需求取 0.2
    dist        : str，采样分布类型：
                  - "negbinom"  负二项分布（推荐）：适合航空需求，能自然捕捉过离散性
                  - "lognormal" 对数正态分布：适合收益管理场景，右偏，不会出现负值
                  - "normal"    正态分布：简单对称，可能产生负值（会被截断为 0）
    seed        : int，随机种子，保证实验可复现

    返回：
    ------
    scenarios   : list of dict，长度 n_scenarios，每个元素为 {product: sampled_demand}
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

            sigma = cv * mu  # 标准差

            if dist == "negbinom":
                # 负二项分布参数：mu, r（离散参数）
                # r = mu^2 / (sigma^2 - mu)，当 sigma^2 > mu 时有意义（过离散）
                var = sigma ** 2
                if var <= mu:
                    # 方差 <= 均值时退化为泊松分布
                    sampled = float(rng.poisson(mu))
                else:
                    r = mu ** 2 / (var - mu)
                    p_nb = r / (r + mu)
                    sampled = float(rng.negative_binomial(r, p_nb))

            elif dist == "lognormal":
                # 对数正态参数推导：mu_ln, sigma_ln
                sigma_ln = np.sqrt(np.log(1 + (sigma / mu) ** 2))
                mu_ln = np.log(mu) - 0.5 * sigma_ln ** 2
                sampled = float(rng.lognormal(mu_ln, sigma_ln))

            elif dist == "normal":
                sampled = float(rng.normal(mu, sigma))
                sampled = max(sampled, 0.0)  # 截断负值

            else:
                raise ValueError(f"未知分布类型: {dist}，请选择 'negbinom', 'lognormal' 或 'normal'")

            scenario[p] = round(sampled, 4)
        scenarios.append(scenario)

    # 打印场景统计摘要
    print(f"\n📊 蒙特卡洛场景生成完毕（分布={dist}, N={n_scenarios}, CV={cv}）")
    sample_product = products[0]
    sampled_vals = [s[sample_product] for s in scenarios]
    print(f"   示例产品 [{sample_product}]：均值需求={demand[sample_product]:.1f}, "
          f"场景均值={np.mean(sampled_vals):.1f}, "
          f"场景标准差={np.std(sampled_vals):.1f}, "
          f"场景范围=[{np.min(sampled_vals):.1f}, {np.max(sampled_vals):.1f}]")

    return scenarios

# =====================================================================
# 3. 从 JSON 文件读取真实数据
# =====================================================================
def load_real_data(data_dir="."):
    """
    从本地读取数据清洗后的 JSON 文件，并构造为 Gurobi 模型所需的 14 个基础数据结构。
    严格按照《数据说明.md》解析字段。
    """
    print(f"🔄 正在从 '{data_dir}' 目录加载 JSON 数据...")
    
    with open(os.path.join(data_dir, 'predict_product_info.json'), 'r', encoding='utf-8') as f:
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
                    "cost_per_min": float(row['每小时飞行成本']) / 60.0
                }
        print("✅ 成功加载 data_fam_fleet.csv")
    except FileNotFoundError:
        print(f"⚠️ 未找到 {csv_file_path}，请确保该 CSV 文件在当前目录中！")
        raise

    # 1. 提取机队基础属性
    fleets = list(fleet_info.keys())
    total_aircraft = {k: v['count'] for k, v in fleet_info.items()}
    seats = {k: v['seats'] for k, v in fleet_info.items()}

    # 2. 提取产品收益与需求（均值，用于场景生成）
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

    # 4. 构建核心：时空网络节点
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
# 4. 核心建模函数（两阶段随机规划 + SAA）
# =====================================================================
def build_and_solve_fap_model(
    fleets, tasks, products, all_legs, airports, total_aircraft, seats,
    flight_cost, fare, demand, leg_to_products, leg_to_task_map,
    overnight_tasks, airport_nodes_dict,
    # --- 新增：蒙特卡洛随机规划参数 ---
    n_scenarios=200,
    demand_cv=0.2,
    demand_dist="negbinom",
    mc_seed=42,
    mip_gap=5e-4
):
    """
    两阶段随机规划（Extensive Form / SAA）：

    第一阶段（此刻决策，需求不确定）：
        x[f,k]  ∈ {0,1}  ← 机型分配，必须在需求实现前确定

    第二阶段（需求实现后的最优响应）：
        s[p,n]  ≥ 0      ← 场景 n 下产品 p 的实际售票量

    目标：最大化期望利润
        max  -Σ(f,k) cost[f,k]·x[f,k]  +  (1/N)·Σ_n Σ_p fare[p]·s[p,n]

    关键约束变化：
        约束 D（容量）：对每个场景 n，需求变量 s[p,n] 受该场景需求上界和运力共同约束
    """
    # --- Step 1: 生成蒙特卡洛需求场景 ---
    scenarios = generate_demand_scenarios(
        demand, n_scenarios=n_scenarios, cv=demand_cv, dist=demand_dist, seed=mc_seed
    )
    scenario_ids = list(range(n_scenarios))
    prob = 1.0 / n_scenarios  # 等概率场景（SAA 标准假设）

    # --- Step 2: 构建模型 ---
    model = gp.Model("FAP_NRM_Stochastic")
    model.setParam('OutputFlag', 1)
    model.setParam('MIPGap', mip_gap)

    # ── 第一阶段变量（与需求无关，全局共享）──
    x = model.addVars(tasks, fleets, vtype=GRB.BINARY, name="x")
    all_nodes = [node for airport in airports for node in airport_nodes_dict[airport]]
    g = model.addVars(all_nodes, fleets, lb=0.0, vtype=GRB.CONTINUOUS, name="g")

    # ── 第二阶段变量（每个场景独立，s[p,n] 上界由各场景需求决定）──
    # 注意：上界需在添加变量后通过约束施加，以便每个场景使用不同的需求值
    s = model.addVars(products, scenario_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="s")

    # 为每个场景施加需求上界约束（替代直接设 ub，以便按场景差异化）
    for n in scenario_ids:
        for p in products:
            model.addConstr(
                s[p, n] <= scenarios[n][p],
                name=f"demand_ub[{p},{n}]"
            )

    # ── 目标函数：期望利润最大化 ──
    # 飞行成本：确定性（第一阶段），与场景无关
    cost = gp.quicksum(
        flight_cost[f, k] * x[f, k]
        for f in tasks for k in fleets if (f, k) in flight_cost
    )
    # 期望票务收入：所有场景的加权平均（等权重 = 1/N）
    expected_revenue = prob * gp.quicksum(
        fare[p] * s[p, n]
        for p in products for n in scenario_ids
    )
    model.setObjective(expected_revenue - cost, GRB.MAXIMIZE)

    # ── 约束 A：唯一性约束（与原模型相同，不受场景影响）──
    model.addConstrs(
        (gp.quicksum(x[f, k] for k in fleets) == 1 for f in tasks),
        name="task_cover"
    )

    # ── 约束 B：流平衡与跨日循环约束（与原模型相同）──
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

    # ── 约束 C：可用机队规模约束（与原模型相同）──
    for k in fleets:
        last_nodes = [airport_nodes_dict[airport][-1] for airport in airports]
        ground_at_midnight = gp.quicksum(g[n, k] for n in last_nodes)
        airborne_overnight = gp.quicksum(x[f, k] for f in overnight_tasks)
        model.addConstr(
            ground_at_midnight + airborne_overnight <= total_aircraft[k],
            name=f"fleet_count[{k}]"
        )

    # ── 约束 D（随机化）：航段容量约束，对每个场景分别施加 ──
    # 运力由第一阶段决策 x 决定（确定性），但需求来自各场景
    for l in all_legs:
        parent_task = leg_to_task_map[l]
        capacity_of_leg = gp.quicksum(seats[k] * x[parent_task, k] for k in fleets)
        for n in scenario_ids:
            demand_on_leg_n = gp.quicksum(s[p, n] for p in leg_to_products.get(l, []))
            model.addConstr(
                demand_on_leg_n <= capacity_of_leg,
                name=f"leg_capacity[{l},{n}]"
            )

    # --- Step 3: 求解 ---
    model.optimize()
    return model, x, g, s, scenarios

# =====================================================================
# 5. 运行与结果解析及导出
# =====================================================================
if __name__ == "__main__":
    # ── 蒙特卡洛参数配置（可按需调整）──
    MC_N_SCENARIOS = 50   # 场景数量：越大越稳健，但模型规模线性增长
    MC_CV          = 0.20  # 需求变异系数：0.1=低波动, 0.2=中等(推荐), 0.3=高波动
    MC_DIST        = "negbinom"  # 分布类型："negbinom" / "lognormal" / "normal"
    MC_SEED        = 42    # 随机种子

    SOLVE_MIP_GAP  = 5e-4

    data_tuple = load_real_data(data_dir=".")
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
        print(f"🎉 求解成功！最大期望总利润: ¥ {model.ObjVal:,.2f}")
        print(f"   (基于 {MC_N_SCENARIOS} 个蒙特卡洛需求场景，CV={MC_CV}，分布={MC_DIST})")
        print("="*55)
        
        print("\n💾 正在将完整结果导出为 CSV 文件...")
        fleets    = data_tuple[0]
        tasks     = data_tuple[1]
        products  = data_tuple[2]
        all_legs  = data_tuple[3]
        airports  = data_tuple[4]
        total_aircraft = data_tuple[5]
        seats     = data_tuple[6]
        flight_cost = data_tuple[7]
        fare = data_tuple[8]
        demand    = data_tuple[9]  # 原始历史均值需求
        leg_to_products = data_tuple[10]
        leg_to_task_map = data_tuple[11]
        airport_nodes_dict = data_tuple[13]
        scenario_ids = list(range(MC_N_SCENARIOS))
        with open('super_flight_schedule.json', 'r', encoding='utf-8') as f:
            super_flight_schedule = json.load(f)

        # ---------------------------------------------------------
        # 构建基础映射缓存
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
        # 导出 1：产品销量综合分析（场景统计汇总）
        # ==========================================
        comprehensive_records = []
        for p in products:
            # 跨场景计算期望销量与统计特征
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
                    "Historical_Demand":  round(demand[p], 2),      # 原始历史均值
                    "MC_Mean_Demand":     round(mean_demand, 2),     # 蒙特卡洛场景均值
                    "Expected_Sold":      round(mean_sold, 2),       # 期望销量
                    "Std_Sold":           round(std_sold, 2),        # 销量标准差
                    "P5_Sold":            round(p5_sold, 2),         # 5%分位数（悲观情景）
                    "P95_Sold":           round(p95_sold, 2),        # 95%分位数（乐观情景）
                    "Expected_Unmet":     round(mean_unmet, 2),      # 期望未满足需求
                    "Legs":               " -> ".join(p_legs),
                    "Tasks":              " -> ".join(p_tasks),
                    "Assigned_Fleets":    " -> ".join(p_fleets)
                })

        with open('result_comprehensive_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            fieldnames = ["Product", "Historical_Demand", "MC_Mean_Demand", "Expected_Sold",
                          "Std_Sold", "P5_Sold", "P95_Sold", "Expected_Unmet",
                          "Legs", "Tasks", "Assigned_Fleets"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(comprehensive_records)

        # ==========================================
        # 导出 2：跨日地面驻场状态（与原模型一致）
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

        # ==========================================
        # 导出 3：航段影子价格（Bid Price，场景均值）
        # ==========================================
        print("🔍 正在计算网络航段期望影子价格(Expected Bid Prices)...")
        fixed_model = model.fixed()
        fixed_model.setParam('OutputFlag', 0)
        fixed_model.optimize()
        shadow_price_map = {}

        if fixed_model.Status == GRB.OPTIMAL:
            shadow_price_records = []
            for l in all_legs:
                # 对每个场景的影子价格取均值，得到期望 Bid Price
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
            with open('result_shadow_prices.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
                fieldnames = ["Leg", "Expected_Shadow_Price", "Std_Shadow_Price",
                              "P5_Shadow_Price", "P95_Shadow_Price"]
                writer = csv.DictWriter(f_out, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(shadow_price_records)

        # ==========================================
        # 导出 4：航段客座率（场景均值与分布）
        # ==========================================
        leg_load_records = []
        leg_stats_map = {}
        for l in all_legs:
            parent_task   = leg_to_task_map.get(l)
            assigned_fleet = task_to_fleet.get(parent_task, "Unknown")
            assigned_seats = seats.get(assigned_fleet, 0)
            
            # 逐场景计算客座率
            load_factors = []
            for n in scenario_ids:
                pax_n = sum(s[p, n].X for p in leg_to_products.get(l, []))
                lf_n  = (pax_n / assigned_seats * 100) if assigned_seats > 0 else 0
                load_factors.append(lf_n)

            mean_lf  = float(np.mean(load_factors))
            # 识别瓶颈：如果超过 50% 的场景中客座率达到 100% 且存在溢出需求
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
                "Bottleneck_Freq(%)":   round(bottleneck_freq * 100, 1),  # 满舱场景占比
            })

        with open('result_leg_load_factor.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
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
        with open('result_model_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
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
        with open('result_task_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
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
        with open('result_fleet_summary.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
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
        with open('result_leg_value_analysis.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(leg_value_records[0].keys()))
            writer.writeheader()
            writer.writerows(leg_value_records)

        # ==========================================
        # 导出 5（新增）：各场景利润分布明细
        # ==========================================
        scenario_profit_records = []
        for n in scenario_ids:
            scenario_revenue = sum(fare[p] * s[p, n].X for p in products)
            # 飞行成本为确定值，对所有场景一致
            scenario_profit_records.append({
                "Scenario_ID":      n,
                "Scenario_Revenue": round(scenario_revenue, 2),
            })
        
        # 统计利润分布特征（成本确定，仅收入波动）
        revenues = [r["Scenario_Revenue"] for r in scenario_profit_records]
        print(f"\n📈 期望收入: ¥{np.mean(revenues):,.2f}  |  "
              f"标准差: ¥{np.std(revenues):,.2f}  |  "
              f"P5: ¥{np.percentile(revenues, 5):,.2f}  |  "
              f"P95: ¥{np.percentile(revenues, 95):,.2f}")

        with open('result_scenario_profit.csv', 'w', newline='', encoding='utf-8-sig') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=["Scenario_ID", "Scenario_Revenue"])
            writer.writeheader()
            writer.writerows(scenario_profit_records)

        print("\n✅ 导出完成！请在当前目录下查看以下文件：")
        print("   - result_comprehensive_analysis.csv (产品期望销量与场景分布统计)")
        print("   - result_ground_status.csv          (各机场机型过夜停场明细)")
        print("   - result_shadow_prices.csv          (各航段期望影子价格/竞价分布)")
        print("   - result_leg_load_factor.csv        (航段期望客座率与瓶颈频率)")
        print("   - result_scenario_profit.csv        (各场景收入分布，用于风险分析)")

    elif model.Status == GRB.INFEASIBLE:
        print("\n❌ 模型未能找到最优解，发生约束冲突 (Infeasible)。")
        print("💡 建议：")
        print("1. 检查物理总机队数量是否足以覆盖所有的航班起降循环。")
        print("2. 检查是否有特定的航线循环无法闭环（如某机场只进不出）。")
        print("3. 如果场景数量过大导致内存不足，可尝试减少 MC_N_SCENARIOS。")
    else:
        print(f"\n⚠️ 求解结束，状态码：{model.Status}")
