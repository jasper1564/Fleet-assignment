# Final Model Spec

最后更新：2026-04-23

这个文件用于锁定当前仓库的最终答题口径，避免后续再把“历史收益比较”“需求恢复”“机型分配优化”“机队使用解释”混成一条线。

## 一、四个问题的最终口径

### 问题一：并购前后收益比较

- 主口径：原始历史销量口径
- 对照口径：RF 还原需求口径
- 不直接使用第三问机型分配优化结果

对应输出：

- [`question1_answer.md`](question1_answer.md)
- [`../results/runs/question1_current`](../results/runs/question1_current)

### 问题二：旅客行程选择行为分析

- 正式路线：`Random Forest`
- 当前采用两阶段框架：
  - `X -> near_ratio`
  - 截断纠偏后 `X -> final_demand`

对应输出：

- [`../src/demand_estimation/passenger_choice_random_forest.md`](../src/demand_estimation/passenger_choice_random_forest.md)
- [`../data/model_input/demand/product_info_rf_predicted.json`](../data/model_input/demand/product_info_rf_predicted.json)

### 问题三：并购后机型分配方案

- 正式主模型：[`../src/modeling/fleet_assignment_main.py`](../src/modeling/fleet_assignment_main.py)
- 正式结果目录：[`../results/runs/model_current`](../results/runs/model_current)（20 场景）
- 原 5 场景归档：[`../results/runs/model_current_5scenario_archive_2026-04-23`](../results/runs/model_current_5scenario_archive_2026-04-23)

### 问题四：机队使用情况与调整建议

- 正式口径：基于问题三主模型结果做解释与建议
- 不再重新搭建独立优化模型

对应输出：

- [`question4_answer.md`](question4_answer.md)
- [`question4_current_analysis.md`](question4_current_analysis.md)
- [`question4_figure_notes.md`](question4_figure_notes.md)
- [`question4_additional_findings.md`](question4_additional_findings.md)
- 20 场景分析包：[`../results/analysis/question4_mc20_2026-04-23`](../results/analysis/question4_mc20_2026-04-23)

## 二、当前正式技术主线

### 需求输入

- 正式需求文件：[`../data/model_input/demand/product_info_rf_predicted.json`](../data/model_input/demand/product_info_rf_predicted.json)
- 对照需求文件：[`../data/model_input/demand/product_info_em_restored.json`](../data/model_input/demand/product_info_em_restored.json)

### 机型分配主模型

- 主模型文件：[`../src/modeling/fleet_assignment_main.py`](../src/modeling/fleet_assignment_main.py)
- 主结果目录：[`../results/runs/model_current`](../results/runs/model_current)（20 场景）

### 网络输入

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 机队输入

- `data/raw/reference/fleet_family_master.csv`

## 三、为什么当前主线这样定

### 1. RF 而不是 EM

题目第二问明确要求“通过影响因素分析来还原需求”。  
因此：

- `RF` 路线符合题意
- `EM` 路线更适合作为统计恢复对照，而不是正式主答案

### 2. `fleet_assignment_main.py` 而不是历史变体

当前主模型能稳定输出：

- 收益
- 成本
- 利润
- 载客率
- 影子价格
- 机队使用摘要
- 调整候选表

并且它能直接支撑问题三和问题四的正式答案。

### 3. Monte Carlo 采用 20 场景主线

当前 `Monte Carlo` 的定位是：

- 正式主线采用 `20` 个需求场景
- 保留对需求波动的敏感性意识
- 不再追求更大规模场景扩展
- 原 `5` 场景结果保留为归档对照

理由不是“技术上做不到”，而是：

- 对本题边际价值有限
- 会显著增加算力负担和解释成本

20 场景主线的统一口径见：

- [`monte_carlo_20_scenario_handoff.md`](monte_carlo_20_scenario_handoff.md)

当前可引用的正式结论是：20 场景下总利润为 `5,447,198.52`，相对原 5 场景归档结果变化约 `-0.32%`；`54/739` 个任务发生机型调整，但 `F16C0Y165` 与 `F0C0Y76` 仍是核心主力机型，第四问“结构优化与瓶颈增容”的结论不变。

## 四、明确不再作为主线的内容

### EM 需求还原

- 可以保留
- 可以比较
- 可以写进稳健性分析
- 但不作为正式答题主线

### 全量零需求恢复

- 当前只被视为未来扩展方向
- 暂不并入 `RF` 主线

### 大规模 Monte Carlo

- 不再作为主要技术卖点
- 只在需要时作为附加敏感性说明
- 当前 `20` 场景结果已经作为正式主线，但仍不应包装为“大规模 Monte Carlo”主卖点

## 五、当前最终答案的推荐表述

推荐后续统一这样表述整套方法：

> 首先，基于原始销售数据回答并购前后历史收益变化；其次，利用随机森林框架识别截断并恢复产品需求，从而回答特征如何影响总需求；再次，以 RF 恢复后的需求作为输入，求解并购后机型分配方案；最后，基于主模型结果解释机队使用结构、识别瓶颈资源并提出调整建议。

这套表述可以把四个问题自然串起来，同时又不混淆各自的时间线和数据口径。
