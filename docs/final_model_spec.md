# Final Model Spec

最后更新：2026-04-20

这个文件用来锁定当前项目的正式答题模型，避免后续围绕模型口径反复摇摆。

## 正式答题主线

### 需求还原

- 正式路线：`Random Forest`
- 对应输入：[`../data/model_input/demand/product_info_rf_predicted.json`](../data/model_input/demand/product_info_rf_predicted.json)
- 选择原因：符合题目第 2 问“通过影响因素分析来还原需求”的要求

### 机型分配模型

- 正式模型文件：[`../src/modeling/fleet_assignment_main.py`](../src/modeling/fleet_assignment_main.py)
- 正式结果目录：[`../results/runs/model_current`](../results/runs/model_current)

### 网络输入

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 机队输入

- `data/raw/reference/fleet_family_master.csv`

## 对 Monte Carlo 的最终定位

- 继续保留 `Monte Carlo`，但只作为“轻量需求波动刻画”。
- 默认场景数固定为 `5`。
- 不再追求 `30`、`50` 这类高场景数的重型随机规划。
- 理由不是“技术上做不到”，而是“对本题边际价值低，且会明显增加算力负担与解释成本”。

## 现在的正式表述方式

推荐后续统一这样描述模型：

> 基于第二问随机森林得到的需求还原结果，构建并求解并购后的机型分配模型；同时用少量 Monte Carlo 场景对需求波动做轻量敏感性刻画，场景数固定为 5。

这样有三个好处：

- 保证题意主线始终是“影响因素分析 -> 需求还原 -> 机型分配”
- 保留一定波动意识，但不把重点转移到大规模随机优化
- 便于报告解释和答辩

## 明确不再作为主线的内容

### EM 需求还原

- 可以保留
- 可以比较
- 可以作为稳健性/对照实验
- 但不再作为正式答题主答案

### 大规模 Monte Carlo

- 不再作为主要技术卖点
- 不再追求更多场景数
- 只在需要时作为附加敏感性说明

## 当前模型输出应服务谁

从现在开始，`model_current` 的输出不再优先服务“随机规划研究”，而是优先服务题目第 3 问和第 4 问：

- 第 3 问：给出并购后机型分配方案及收益成本结果
- 第 4 问：解释各机型使用情况，并提出是否需要进一步调整机队或航班计划

因此后续的主要开发方向应是：

- 不再改模型结构
- 优先改输出端和分析端
