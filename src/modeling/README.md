# Modeling Module

最后更新：2026-04-23

这个目录是题目第 3 问和第 4 问的核心代码区域。

## 当前正式口径

- 正式主模型：[`fleet_assignment_main.py`](fleet_assignment_main.py)
- 对照模型：[`fleet_assignment_robust.py`](fleet_assignment_robust.py)
- 正式结果目录：[`../../results/runs/model_current`](../../results/runs/model_current)（20 场景）
- 原 5 场景归档目录：[`../../results/runs/model_current_5scenario_archive_2026-04-23`](../../results/runs/model_current_5scenario_archive_2026-04-23)
- 对照结果目录：[`../../results/runs/robustness`](../../results/runs/robustness)

## 推荐阅读顺序

1. [`fleet_assignment_main.md`](fleet_assignment_main.md)
2. [`../../docs/final_model_spec.md`](../../docs/final_model_spec.md)
3. [`fleet_assignment_robust.md`](fleet_assignment_robust.md)
4. [`variants/README.md`](variants/README.md)

## 活跃模型

| 文件 | 当前定位 | 需求输入 | 结果目录 |
| --- | --- | --- | --- |
| [`fleet_assignment_main.py`](fleet_assignment_main.py) | 问题三正式主模型入口，默认 20 场景 | `product_info_rf_predicted.json` | `results/runs/model_current/` |
| [`fleet_assignment_main.py`](fleet_assignment_main.py) + 自定义 `RESULTS_DIR` | Monte Carlo 对照实验 | `product_info_rf_predicted.json` | 自定义 `results/runs/...` |
| [`fleet_assignment_robust.py`](fleet_assignment_robust.py) | 稳健性/对照模型 | `product_info_em_restored.json` | `results/runs/robustness/` |

## 共同依赖

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`
- `data/raw/reference/fleet_family_master.csv`

## 当前项目里的关键判断

### 1. 主模型已经足够支撑问题三与问题四

当前 `model_current` 已稳定输出：

- `scenario_summary.csv`
- `fleet_summary.csv`
- `task_summary.csv`
- `leg_value_analysis.csv`
- `product_assignment_analysis.csv`
- `task_adjustment_candidates.csv`
- `leg_adjustment_candidates.csv`

20 场景已提升为正式主线，统一说明见：

- [`../../docs/monte_carlo_20_scenario_handoff.md`](../../docs/monte_carlo_20_scenario_handoff.md)

### 2. 闲置机型不自动等于求解失败

当前若干机型 `0` 使用，更合理的解释通常是：

- 模型只限制“使用量不超过可用量”
- 目标函数是“收入 - 飞行成本”
- 这些机型在当前网络中的综合性价比较低

对应说明见：

- [`../../docs/question4_additional_findings.md`](../../docs/question4_additional_findings.md)

### 3. 改需求输入就等于改答题口径

`product_info_rf_predicted.json` 与 `product_info_em_restored.json` 不是“可随手替换的数据文件”，而是两套不同的实验口径。

## 当前最稳的使用方式

- 问题三与问题四的正式结论，以 `fleet_assignment_main.py` 为准
- 默认正式结果以 `results/runs/model_current` 的 20 场景结果为准
- 原 5 场景结果只作为归档对照，不直接替换正式结果
- `fleet_assignment_robust.py` 只作为对照和稳健性补充
- 若继续扩展，优先补充解释端和报告端，而不是重写优化结构
