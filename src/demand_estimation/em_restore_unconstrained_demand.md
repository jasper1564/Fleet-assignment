# `em_restore_unconstrained_demand.py`

## 为什么存在

这个脚本代表另一条需求口径：把销量截断视为统计恢复问题，用 EM 思路估计潜在未观测需求。

## 核心思路

- 把部分产品看成存在销售截断。
- 按分组对销量分布做迭代估计。
- 对疑似截断样本恢复“未受限需求”。

## 输入

- `data/raw/booking/itinerary_sales_by_rd.csv`

## 输出

- `data/raw/demand/itinerary_unconstrained_demand.csv`
- `results/figures/demand_recovery/em_demand_recovery_comparison.png`

## 在项目里的位置

- 这是 `EM` 需求路线的起点。
- 下游会由 `merge_em_demand_into_products.py` 生成 `product_info_em_restored.json`。
- `fleet_assignment_robust.py` 直接使用这一路的需求结果。
- 这条线的结果更稳健，但当前不应被当成正式答题主线，因为它不来自题目第 2 问要求的影响因素分析。

## 开发时要注意

- 这个脚本的位置虽然在 `demand_estimation/`，但输出被放在 `data/raw/demand/`，是为了把“恢复后的需求表”单独沉淀出来。
- 它更偏向统计恢复，不等于旅客选择行为解释。

## 什么时候优先看它

- 想做需求敏感性或稳健性比较时。
- 想回答“如果历史销量被截断，模型结论会变化多少”时。
