# Demand Estimation Module

这个目录是题目第 2 问的主要实现区，同时也负责为机型分配模型准备需求输入。

优先看的单文件说明：

- [`passenger_choice_random_forest.md`](passenger_choice_random_forest.md)
- [`em_restore_unconstrained_demand.md`](em_restore_unconstrained_demand.md)

## 先分清两条需求路线

### RF 路线

目标：基于旅客行程选择行为与影响因素分析，修正产品需求。

链路：

`itinerary_sales_by_rd.csv`
-> `passenger_choice_random_forest.py`
-> `corrected_demand_random_forest.csv`
-> `merge_rf_demand_into_products.py`
-> `products_with_rf_demand.csv`
-> `products_csv_to_product_info_json.py`
-> `product_info_rf_predicted.json`
-> `fleet_assignment_main.py`

当前定位：这是符合题目要求的正式答题路线。

### EM 路线

目标：基于截断与统计恢复，估计未观测需求。

链路：

`itinerary_sales_by_rd.csv`
-> `em_restore_unconstrained_demand.py`
-> `itinerary_unconstrained_demand.csv`
-> `merge_em_demand_into_products.py`
-> `products_with_em_demand.csv`
-> `product_info_em_restored.json`
-> `fleet_assignment_robust.py`

当前定位：这条路线更稳健，结果与影子价格也能跑出来，但不符合题目“通过第二问影响因素分析来还原需求”的要求，因此当前应视为对照线或稳健性参考线。

## 文件说明

| 文件 | 作用 | 主要输出 | 备注 |
| --- | --- | --- | --- |
| [`passenger_choice_random_forest.py`](passenger_choice_random_forest.py) | 分析旅客选择行为，预测近起飞期销售占比，并反推出修正需求 | `data/interim/passenger_choice/corrected_demand_random_forest.csv`, `results/figures/passenger_choice/random_forest_summary.png` | 这是题目第 2 问最核心的行为分析脚本 |
| [`merge_rf_demand_into_products.py`](merge_rf_demand_into_products.py) | 将 RF 修正需求并回产品表 | `data/interim/passenger_choice/products_with_rf_demand.csv` | 桥接脚本，逻辑简单但位置关键 |
| [`products_csv_to_product_info_json.py`](products_csv_to_product_info_json.py) | 把产品表转成模型可读 JSON | `data/model_input/demand/product_info_rf_predicted.json` | 给主模型供数 |
| [`em_restore_unconstrained_demand.py`](em_restore_unconstrained_demand.py) | 用 EM 思路恢复截断后的潜在需求 | `data/raw/demand/itinerary_unconstrained_demand.csv`, `results/figures/demand_recovery/em_demand_recovery_comparison.png` | 偏统计恢复路线 |
| [`merge_em_demand_into_products.py`](merge_em_demand_into_products.py) | 将 EM 恢复结果并回产品表并导出 JSON | `data/interim/demand_recovery/products_with_em_demand.csv`, `data/model_input/demand/product_info_em_restored.json` | 给稳健模型供数 |

## 开发时最容易混淆的点

- `RF` 和 `EM` 不是同一条链的两个小步骤，而是两套不同需求口径。
- `RF` 是题意主线，`EM` 不是默认最终答案。
- `product_info_rf_predicted.json` 与 `product_info_em_restored.json` 会直接改变模型结果。
- `restored_demand_gompertz.csv` 当前更像历史产物，不是当前主线入口。

## 如果只想回答题目第 2 问

优先看：

1. [`passenger_choice_random_forest.py`](passenger_choice_random_forest.py)
2. [`../../src/analysis/README.md`](../../src/analysis/README.md)
3. `results/figures/passenger_choice/`
4. `results/figures/truncation/`
