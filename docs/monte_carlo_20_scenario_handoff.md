# 20 场景 Monte Carlo 主线交接

最后更新：2026-04-23

本文记录 20 场景 Monte Carlo 正式主线的模型结果、第四问分析、代码入口和上下游使用口径。当前已经将 20 场景结果提升为主路线，原 5 场景结果只作为归档对照保留。

## 一、口径结论

当前正式主线已经切换为 20 场景：

- 问题三正式结果仍以 `results/runs/model_current` 为准，但该目录当前已经替换为 20 场景结果。
- 问题三正式 Monte Carlo 场景数为 `20`。
- 问题四正式答案仍以 `docs/question4_answer.md`、`docs/question4_current_analysis.md` 和 `results/figures/question4` 为主，这些口径现在对应 20 场景结果。

保留的对照与来源目录是：

- `results/runs/model_mc20_2026-04-23`：20 场景原始运行结果，与当前 `model_current` 内容一致。
- `results/runs/model_current_5scenario_archive_2026-04-23`：原 5 场景正式结果归档。
- `results/analysis/question4_mc20_2026-04-23`：基于 20 场景结果生成的第四问分析包。
- `results/figures/question4_5scenario_archive_2026-04-23`：原 5 场景第四问图表归档。

推荐统一表述：

> 正式模型采用 20 个 Monte Carlo 需求场景刻画需求波动。与原 5 场景结果相比，20 场景仅带来小幅边际机型重排，核心管理结论保持一致：当前问题不是总机队数量不足，而是主力机型偏紧、部分机型闲置，应优先做结构优化与关键瓶颈航段定向增容。

## 二、上游输入

20 场景主线沿用当前正式输入：

- 需求输入：`data/model_input/demand/product_info_rf_predicted.json`
- 航班网络：`data/model_input/network/super_flight_schedule.json`
- 机场时间线：`data/model_input/network/airport_timeline.json`
- 产品-航段映射：`data/model_input/network/leg_to_products.json`
- 机队参考：`data/raw/reference/fleet_family_master.csv`

因此它与归档 5 场景结果的差异主要来自 Monte Carlo 场景数，而不是需求口径或网络结构变化。

## 三、模型侧改动

### 1. 主模型结果目录可配置

`src/modeling/fleet_assignment_main.py` 新增 `RESULTS_DIR` 环境变量支持。

默认行为现在会生成 20 场景主线结果：

```powershell
python src/modeling/fleet_assignment_main.py
```

默认写入：

```text
results/runs/model_current
```

如果要另存实验结果，可以显式指定新目录：

```powershell
$env:MC_N_SCENARIOS='20'
$env:RESULTS_DIR='results/runs/model_mc20_2026-04-23'
$env:EXPERIMENT_NAME='model_mc20_2026-04-23'
python src/modeling/fleet_assignment_main.py
```

### 2. 本次运行参数

- 场景数：`20`
- 需求波动系数：`0.20`
- 分布：`negbinom`
- 随机种子：`42`
- 正式主线目录：`results/runs/model_current`
- 原始运行目录：`results/runs/model_mc20_2026-04-23`

Gurobi 求解成功，最优 gap 为 `0.0097%`，求解耗时约 `513s`。

## 四、正式结果摘要

当前正式 20 场景结果见：

- `results/runs/model_current/scenario_summary.csv`
- `results/runs/model_current/scenario_profit.csv`
- `results/runs/model_current/fleet_summary.csv`
- `results/runs/model_current/task_summary.csv`

核心指标：

| 指标 | 5 场景归档结果 | 20 场景正式结果 | 变化 |
| --- | ---: | ---: | ---: |
| 总收入 | 11,891,210.82 | 11,902,969.36 | 11,758.54 |
| 总成本 | 6,426,543.33 | 6,455,770.83 | 29,227.50 |
| 总利润 | 5,464,667.49 | 5,447,198.52 | -17,468.97 |
| 总未满足需求 | 13,686.60 | 13,539.85 | -146.75 |
| 平均载客率 | 86.00% | 85.83% | -0.17 |
| 加权载客率 | 87.48% | 87.49% | 0.01 |
| 高影子价格航段数 | 549 | 602 | 53 |

解释口径：

- 20 场景下总利润较归档 5 场景下降约 `0.32%`，属于小幅变化。
- 未满足需求略降，加权载客率几乎不变。
- 高影子价格航段数上升，说明扩大场景数后瓶颈识别更充分。

## 五、机型分配变化

20 场景相比归档 5 场景：

- 总任务数均为 `739`。
- `54` 个任务更换机型，占比约 `7.31%`。
- 主体方案没有颠覆，核心机型仍是 `F16C0Y165` 与 `F0C0Y76`。

主要迁移方向：

| 迁移方向 | 任务数 |
| --- | ---: |
| `F16C0Y165 -> F0C0Y76` | 10 |
| `F12C12Y48 -> F0C0Y76` | 8 |
| `F0C0Y72 -> F0C0Y76` | 8 |
| `F0C0Y76 -> F16C0Y165` | 8 |
| `F0C0Y76 -> F12C12Y48` | 6 |
| `F0C0Y76 -> F0C0Y72` | 5 |

机队层面主要变化：

- `F0C0Y76`：任务数 `342 -> 349`，使用飞机仍为 `38`。
- `F16C0Y165`：任务数 `316 -> 317`，使用飞机 `44 -> 42`。
- `F12C0Y112`：从使用 `1` 架、承担 `2` 个任务，变为完全闲置。

完整清单见：

- `results/analysis/question4_mc20_2026-04-23/tables/task_fleet_changes.csv`
- `results/analysis/question4_mc20_2026-04-23/tables/task_fleet_transition_counts.csv`

## 六、第四问主线分析

### 1. 分析输出目录

20 场景第四问详细分析保存在：

```text
results/analysis/question4_mc20_2026-04-23
```

主要文件：

- `question4_analysis.md`：20 场景第四问主分析。
- `comparison_with_5_scenarios.md`：5 场景归档结果与 20 场景正式结果对照。
- `figure_notes.md`：20 场景图示说明。
- `figures/`：5 张问题四图。
- `tables/`：复核用汇总表。

### 2. 第四问结论

20 场景下第四问结论为：

- `F16C0Y165` 与 `F0C0Y76` 仍是核心主力机型。
- 两者合计贡献约 `86.32%` 的总利润。
- 两者承载约 `92.19%` 的正影子价格航段。
- 完全闲置机型增加到 `5` 类，说明闲置更像成本效率和网络适配筛选结果。
- 航班计划仍以“定向增容 + 局部降级 + 少数班次复核”为主。

20 场景下调整信号：

- 任务层面：`473` 个增容建议，`93` 个降级建议，`5` 个班次复核建议。
- 航段层面：`602` 个增容建议，`87` 个降级建议，`55` 个班次复核建议。

### 3. 图形生成脚本

`src/analysis/plot_question4_results.py` 新增输入/输出目录环境变量：

- `QUESTION4_RUN_DIR`
- `QUESTION4_OUTPUT_DIR`

复现本次图形：

```powershell
$env:QUESTION4_RUN_DIR='results/runs/model_current'
$env:QUESTION4_OUTPUT_DIR='results/analysis/question4_mc20_2026-04-23/figures'
python src/analysis/plot_question4_results.py
```

默认不传环境变量时，会读取当前正式 `results/runs/model_current`，并输出到 `results/figures/question4`。

### 4. 分析报告生成脚本

新增脚本：

```text
src/analysis/generate_question4_report.py
```

复现本次 Markdown 报告和辅助表：

```powershell
$env:QUESTION4_RUN_DIR='results/runs/model_current'
$env:QUESTION4_BASELINE_RUN_DIR='results/runs/model_current_5scenario_archive_2026-04-23'
$env:QUESTION4_ANALYSIS_DIR='results/analysis/question4_mc20_2026-04-23'
python src/analysis/generate_question4_report.py
```

默认不传环境变量时，会以当前正式 `model_current` 为输入，写入 `results/analysis/question4_current`。

## 七、下游引用建议

### 写正式报告时

主文建议引用：

- `results/runs/model_current`
- `docs/question4_answer.md`
- `results/figures/question4`

如需说明口径切换，可以写：

> 本文最终采用 20 场景 Monte Carlo 结果作为机型分配主线。相较早期 5 场景结果，20 场景下仅 `54/739` 个任务发生机型调整，总利润变化约 `-0.32%`，核心主力机型和瓶颈航段判断保持一致。

### 做答辩时

如果被问到为什么从 5 场景改为 20 场景，可以这样回应：

> 5 个场景适合作轻量波动刻画，但统计代表性偏弱；因此最终主线改用 20 场景。20 场景没有改变核心结论，只带来少量边际机型重排，因此第四问建议更稳健。

### 后续继续扩展时

如果继续跑 `50` 或 `100` 场景，建议沿用同一套目录命名：

```text
results/runs/model_mc50_YYYY-MM-DD
results/analysis/question4_mc50_YYYY-MM-DD
```

并复用同一套环境变量入口。若只是做对照实验，建议另设 `RESULTS_DIR`，避免误覆盖正式 `model_current`。

## 八、注意事项

- 当前 `results/runs/model_current` 已经是 20 场景正式结果。
- 当前 `results/figures/question4` 已经是 20 场景正式图表。
- 如果改了需求输入、网络 JSON 或机队参考表，则不再只是“场景数敏感性实验”，而是新的实验口径。
- 当前 20 场景是正式 Monte Carlo 主线，但仍不应包装成“大规模 Monte Carlo”主卖点。
