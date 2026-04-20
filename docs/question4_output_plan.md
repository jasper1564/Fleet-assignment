# Question 4 Output Plan

最后更新：2026-04-20

这个文件把两套思路合并成一套统一框架：

- 你的思路：把第四问做成一个“管理建议生成模块”
- 我之前的思路：按“现状描述 -> 诊断 -> 候选 -> 建议”组织分析

合并后的结论是：

> 第四问不再被理解成“再做一个优化模型”，而是基于当前机型分配结果，构建一个面向航空公司管理决策的解释与建议模块。

也就是说，第四问回答的重点不是模型怎么建，而是：

- 各机型现在用得合不合理
- 哪些资源是紧约束
- 哪些航班/航段最有价值
- 进一步应该优先调什么

---

## 一、第四问的总框架

建议把第四问拆成 4 个分析模块。

### 模块 1：机型使用情况分析

回答：

- 每种机型用了多少次
- 每种机型承担了多少飞行时间
- 每种机型平均载客率如何
- 哪些机型被过度使用，哪些机型利用不足
- 哪些机型主要服务于高价值航段，哪些主要服务于低价值航段

### 模块 2：灵敏度分析

回答：

- 当关键参数变化时，方案稳不稳
- 哪些资源是紧约束
- 哪些结论对参数最敏感

### 模块 3：航班价值评估

回答：

- 哪些航班/航段是高收益资源
- 哪些航班/航段是运力瓶颈
- 哪些航班/航段虽然收益不高，但网络价值高
- 哪些航班/航段值得保留、扩张、压缩或重新审视

### 模块 4：调整建议分析

回答：

- 哪些航班建议换大机型
- 哪些航班建议换小机型
- 哪些航班值得考虑增班
- 哪些航班疑似可以取消、合并或重新审视时刻
- 哪些机型值得补充，哪些机型暂不建议扩充

---

## 二、4 个模块如何与“描述 -> 诊断 -> 候选 -> 建议”对应

这 4 个模块并不是互相割裂的，它们可以串成一条完整叙事链：

1. `机型使用情况分析`
   负责“现状描述”

2. `灵敏度分析`
   负责“结论稳不稳”的补充诊断

3. `航班价值评估`
   负责识别“高价值 / 高瓶颈 / 低价值”候选对象

4. `调整建议分析`
   负责把前 3 块翻译成管理建议

这样一来，第四问写出来会更像一个完整的管理分析模块，而不是几个零散表格。

---

## 三、模块 1：机型使用情况分析

这是第四问的起点，先回答“并购后机队到底是怎么被使用的”。

### 需要支持的核心问题

- 每种机型用了多少架、多少次
- 每种机型总飞行分钟/小时是多少
- 平均任务载客率如何
- 单架飞机平均承担多少任务
- 单架飞机平均飞了多久
- 哪些机型大量闲置
- 哪些机型承担了大部分高价值任务

### 需要的底层数据

- 每个 Task 的 `Assigned_Fleet`
- 每个 Task 的飞行时间
- 每个 Task/Leg 的座位容量
- 每个 Task/Leg 的期望销量或期望旅客数
- 每个 Task/Leg 的载客率
- 每种机型的可用数量
- 每种机型的实际使用数量

### 推荐输出

#### 1. 机型层汇总表

建议保留文件名：

- `fleet_summary.csv`

但字段建议升级为：

- `Fleet_Type`
- `Available_Aircraft`
- `Used_Aircraft`
- `Utilization_Rate`
- `Assigned_Task_Count`
- `Assigned_Leg_Count`
- `Total_Flight_Minutes`
- `Total_Flight_Hours`
- `Average_Flight_Minutes_Per_Aircraft`
- `Average_Load_Factor`
- `Expected_Passengers`
- `Average_Revenue_Per_Task`
- `Attributed_Revenue`
- `Operating_Cost`
- `Attributed_Profit`
- `Average_Shadow_Price_On_Assigned_Legs`
- `End_Of_Day_Grounded`

#### 2. 航班/任务层明细表

建议保留文件名：

- `task_summary.csv`

这张表是第四问最重要的明细支撑表之一。

---

## 四、模块 2：灵敏度分析

这一部分是第四问的重要支撑，但不要做太大。重点不是“研究随机规划”，而是说明结论稳不稳。

### 优先做的几个维度

- 需求波动系数 `CV`
- 机队规模变化
- 最短过站时间变化
- 需求还原前后对结果的影响
- 个别高价值机型数量增减的边际影响

### 输出原则

这一块不要输出每次试验的全部明细，而是做“实验汇总表”。

### 推荐输出

新增一张实验级汇总表：

- `scenario_summary.csv`

建议字段：

- `Experiment_Name`
- `Demand_CV`
- `Turnaround_Min`
- `Fleet_Adjustment`
- `Total_Revenue`
- `Total_Cost`
- `Total_Profit`
- `Total_Unmet_Demand`
- `Average_Load_Factor`
- `High_Shadow_Price_Leg_Count`

### 当前定位

这张表不是单次主模型运行必须每次都有内容。
它更适合做成“后续试验累积表”。

换句话说：

- `model_current/` 是一次正式运行结果
- `scenario_summary.csv` 是多次人工试验的横向汇总

---

## 五、模块 3：航班价值评估

这是第四问最容易写出亮点的部分。

你提的“对航班价值进行评估”非常对，但建议明确拆成 3 层价值，不然容易混在一起。

### 价值层 1：收入贡献

这个航班或航段本身承载了多少票务收入。

### 价值层 2：运力紧缺价值

这个航班或航段多一单位容量值多少钱，通常看影子价格。

### 价值层 3：网络连接价值

这个航班或航段支撑了多少 OD 产品，不只是本航段本身卖得多不多。

### 需要的底层指标

- 每个 Leg / Task 的总载运旅客数
- 每个 Leg / Task 的总收入贡献
- 每个 Leg / Task 的载客率
- 每个 Leg / Task 的影子价格
- 每个 Leg / Task 覆盖的产品数
- 每个 Leg / Task 的单位飞行时间收益
- 每个 Leg / Task 的单位座位收益

### 推荐输出

#### 1. 航段价值评估表

建议保留文件名：

- `leg_value_analysis.csv`

建议字段：

- `Leg`
- `Parent_Task`
- `Assigned_Fleet`
- `Seat_Capacity`
- `Total_Passengers`
- `Load_Factor`
- `Revenue_Contribution`
- `Shadow_Price`
- `Product_Count`
- `Value_Score`

#### 2. 产品-分配分析表

建议新增或由现有 `comprehensive_analysis.csv` 演化出：

- `product_assignment_analysis.csv`

建议字段：

- `Product`
- `Demand`
- `Sold`
- `Unmet`
- `Fare`
- `Legs`
- `Assigned_Fleets`
- `Revenue`
- `Bottleneck_Leg`

### 用这块结果能做什么分类

有了这些指标后，可以把航班/航段分成四类：

- 高收益高紧张：优先保留，考虑增班或换大机型
- 高收益低紧张：当前配置合理
- 低收益低载客：考虑降级机型或压缩
- 低收益但高网络价值：不能只看点对点收益，要谨慎处理

---

## 六、模块 4：调整建议分析

这一块才是第四问真正落地的部分。

### 第一层建议：不改模型结构，直接基于现有结果给建议

建议先做这一层，因为投入小、解释强、最贴题。

回答：

- 哪些航班建议换大机型
- 哪些航班建议换小机型
- 哪些航班建议重点关注增班可能
- 哪些航班疑似可取消或合并
- 哪些机型边际价值高，值得补充
- 哪些机型利用不足，暂不建议扩充

### 第二层建议：如果时间够，再做小规模情景试验

这一层不作为默认主线，但可以做加分项：

- 人工删除一批低价值航班重新求解
- 人工增加一两个关键高价值航班重新求解
- 人工调整若干高峰航班时间窗重新求解

关键点是：

> 第四问不一定非要做成“航班计划重构模型”，完全可以先做“基于现有解的调整建议与情景验证”。

### 推荐输出

#### 1. 任务调整建议表

- `task_adjustment_candidates.csv`

建议字段：

- `Task`
- `Assigned_Fleet`
- `Origin`
- `Destination`
- `Leg_Count`
- `Expected_Load(%)`
- `Revenue`
- `Cost`
- `Profit`
- `Shadow_Price_Summary`
- `Product_Count`
- `Recommendation_Tag`
- `Recommendation_Reason`

`Recommendation_Tag` 建议取值：

- `Upgauge_or_AddCapacity`
- `Keep`
- `Downgauge`
- `Review_Schedule`

#### 2. 航段调整建议表

- `leg_adjustment_candidates.csv`

建议字段：

- `Leg`
- `Parent_Task`
- `Assigned_Fleet`
- `Load_Factor`
- `Bottleneck_Freq`
- `Shadow_Price`
- `Revenue_Contribution`
- `Product_Count`
- `Value_Score`
- `Recommendation_Tag`

---

## 七、最终统一成 5 类标准结果表

你提的这一点非常关键。为了让第四问真正可写，我建议把输出端整理成 5 类标准结果表。

### 1. `fleet_summary.csv`

用途：

- 回答机型层总体使用情况

建议核心字段：

- `Fleet_Type`
- `Available_Aircraft`
- `Used_Aircraft`
- `Utilization_Rate`
- `Assigned_Task_Count`
- `Total_Flight_Hours`
- `Average_Load_Factor`
- `Average_Revenue_Per_Task`
- `Average_Shadow_Price_On_Assigned_Legs`

### 2. `task_summary.csv`

用途：

- 回答任务层机型分配结果与收益成本情况

建议核心字段：

- `Task`
- `Assigned_Fleet`
- `Origin`
- `Destination`
- `Fly_Minutes`
- `Seat_Capacity`
- `Total_Sold`
- `Total_Unmet`
- `Load_Factor`
- `Revenue`
- `Cost`
- `Profit`
- `Is_Super_Flight`
- `Shadow_Price_Summary`

### 3. `leg_value_analysis.csv`

用途：

- 做航段价值分层

建议核心字段：

- `Leg`
- `Parent_Task`
- `Assigned_Fleet`
- `Seat_Capacity`
- `Total_Passengers`
- `Load_Factor`
- `Revenue_Contribution`
- `Shadow_Price`
- `Product_Count`
- `Value_Score`

### 4. `product_assignment_analysis.csv`

用途：

- 支撑需求满足情况与瓶颈追踪

建议核心字段：

- `Product`
- `Demand`
- `Sold`
- `Unmet`
- `Fare`
- `Legs`
- `Assigned_Fleets`
- `Revenue`
- `Bottleneck_Leg`

### 5. `scenario_summary.csv`

用途：

- 专门服务灵敏度分析

建议核心字段：

- `Experiment_Name`
- `Demand_CV`
- `Turnaround_Min`
- `Fleet_Adjustment`
- `Total_Revenue`
- `Total_Cost`
- `Total_Profit`
- `Total_Unmet_Demand`
- `Average_Load_Factor`
- `High_Shadow_Price_Leg_Count`

---

## 八、当前已有输出与目标输出的映射

### 已有文件，可直接沿用或增强

- `fleet_summary.csv`
- `task_summary.csv`
- `leg_value_analysis.csv`
- `comprehensive_analysis.csv`
- `shadow_prices.csv`
- `leg_load_factor.csv`

### 最自然的演化方式

- `comprehensive_analysis.csv` -> 演化为 `product_assignment_analysis.csv`
- `shadow_prices.csv` + `leg_load_factor.csv` -> 继续作为底层支持表
- `fleet_summary.csv` / `task_summary.csv` / `leg_value_analysis.csv` -> 强化字段，不必完全推倒重来

### 建议新增的结果表

- `product_assignment_analysis.csv`
- `scenario_summary.csv`
- `task_adjustment_candidates.csv`
- `leg_adjustment_candidates.csv`

---

## 九、合并后的最终结论

你的思路和我现在的思路不但能合并，而且合并后会更完整：

- 你这边把第四问明确成“管理建议生成模块”，方向非常对。
- 我这边提供的“描述 -> 诊断 -> 候选 -> 建议”结构，可以把这些管理建议组织得更稳。

最终统一后的版本就是：

1. 用 `fleet_summary + task_summary` 先说现状
2. 用 `scenario_summary` 做稳健性/灵敏度支撑
3. 用 `leg_value_analysis + product_assignment_analysis` 做价值识别
4. 用 `task_adjustment_candidates + leg_adjustment_candidates` 落成建议

这套框架已经足够反推输出端设计，下一步完全可以直接按这份规格改模型输出，不需要再改模型主结构。
