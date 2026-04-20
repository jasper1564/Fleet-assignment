# Modeling Module

这个目录是题目第 3 问和第 4 问的核心区域。

优先看的单文件说明：

- [`fleet_assignment_main.md`](fleet_assignment_main.md)
- [`fleet_assignment_robust.md`](fleet_assignment_robust.md)

## 当前推荐阅读顺序

1. [`fleet_assignment_main.py`](fleet_assignment_main.py)
2. [`fleet_assignment_robust.py`](fleet_assignment_robust.py)
3. [`variants/README.md`](variants/README.md)

## 活跃模型

| 文件 | 当前定位 | 需求输入 | 主要结果目录 |
| --- | --- | --- | --- |
| [`fleet_assignment_main.py`](fleet_assignment_main.py) | 当前正式答题主模型入口 | `data/model_input/demand/product_info_rf_predicted.json` | `results/runs/model_current/` |
| [`fleet_assignment_robust.py`](fleet_assignment_robust.py) | 当前稳健性/对照模型入口 | `data/model_input/demand/product_info_em_restored.json` | `results/runs/robustness/` |

## 共同数据依赖

两个模型都依赖：

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`
- `data/raw/reference/fleet_family_master.csv`

## 当前模型层的重要事实

### `fleet_assignment_main.py`

- 当前最接近“继续开发与最终答题基线”的文件。
- 读取 RF 修正后的产品需求。
- 包含 Monte Carlo 需求场景生成逻辑。
- 当前正式口径中，Monte Carlo 只保留为轻量波动刻画，默认场景数固定为 `5`。
- 可以输出综合分析、地面状态、影子价格、航段负载率和若干摘要表。

### `fleet_assignment_robust.py`

- 更偏向“替代需求口径下的稳健性比较”。
- 读取 EM 还原需求。
- EM 还原结果本身较稳健，且结果和影子价格能跑出来。
- 但这条线不符合题目要求的需求还原逻辑，因此不应直接替代主模型成为正式答案。

## 开发时要小心的地方

- 改需求输入文件名，等于在改模型结论。
- 改 `network` JSON，等于在改任务结构与飞机流网络。
- 当前 `Monte Carlo` 不可直接默认可用，因为存在 OOM 问题。
- `results/runs/` 中的现有结果不一定是当前文件最近一次运行所得。

## 当前最关键的开发判断

如果目标是继续推进最终答题主线，当前默认判断应是：

- 主结论以 `fleet_assignment_main.py` 为核心
- `fleet_assignment_robust.py` 作为稳健性/对照补充
- `Monte Carlo` 只保留少量场景，用作轻量波动刻画
- 接下来主要开发重点转向输出端，尤其是第四问所需输出
