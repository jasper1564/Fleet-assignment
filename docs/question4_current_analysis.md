# Question 4 Analysis

最后更新：2026-04-23

本文基于当前正式主模型结果目录 [`results/runs/model_current`](../results/runs/model_current) 对题目第 4 问进行整理。当前 `model_current` 已经切换为 20 场景 Monte Carlo 结果；原 5 场景结果保存在 [`results/runs/model_current_5scenario_archive_2026-04-23`](../results/runs/model_current_5scenario_archive_2026-04-23)。

更完整的 20 场景分析包见：

- [`../results/analysis/question4_mc20_2026-04-23/question4_analysis.md`](../results/analysis/question4_mc20_2026-04-23/question4_analysis.md)
- [`../results/analysis/question4_mc20_2026-04-23/comparison_with_5_scenarios.md`](../results/analysis/question4_mc20_2026-04-23/comparison_with_5_scenarios.md)
- [`monte_carlo_20_scenario_handoff.md`](monte_carlo_20_scenario_handoff.md)

## 1. 当前方案的总体画像

基于 [`scenario_summary.csv`](../results/runs/model_current/scenario_summary.csv)：

- 场景数：`20`
- 总收入：`11,902,969.36`
- 总成本：`6,455,770.83`
- 总利润：`5,447,198.52`
- 总未满足需求：`13,539.85`
- 平均载客率：`85.83%`
- 加权载客率：`87.49%`
- 高影子价格航段数：`602`

这说明当前方案总体盈利能力较强，但网络中仍有大量航段处于容量紧张状态。第 4 问的重点不是“是否还能求出一个解”，而是：

- 哪些机型是当前真正的主力资源
- 哪些航班/航段最紧张、最值得追加容量
- 哪些配置明显偏大、可以降级或重审
- 哪些机型当前并不值得扩充

## 2. 机型使用情况分析

核心依据来自 [`fleet_summary.csv`](../results/runs/model_current/fleet_summary.csv)。

当前总可用飞机数为 `211`，实际使用飞机数为 `95`，整体使用占比为 `45.02%`。有实际使用的机型为 `4` 类，完全未使用的机型为 `5` 类。

### 2.1 主力机型

当前真正支撑网络利润和运力的机型高度集中在两类：

| 机型 | 可用飞机 | 使用飞机 | 利用率 | 加权载客率 | 归因利润 | 正影子价格航段数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `F16C0Y165` | 48 | 42 | 87.50% | 89.62% | 3,008,368.00 | 260 |
| `F0C0Y76` | 38 | 38 | 100.00% | 86.33% | 1,693,450.62 | 295 |

两者合计归因利润为 `4,701,818.62`，占总方案利润的 `86.32%`；同时承载了 `92.19%` 的正影子价格航段。这说明它们是当前网络的核心瓶颈资源。

### 2.2 补充机型

`F12C12Y48` 和 `F0C0Y72` 被完全使用，但利润贡献和瓶颈承载能力明显低于两类主力机型：

| 机型 | 可用飞机 | 使用飞机 | 利用率 | 加权载客率 | 归因利润 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `F12C12Y48` | 11 | 11 | 100.00% | 69.94% | 227,077.91 |
| `F0C0Y72` | 4 | 4 | 100.00% | 72.45% | 60,060.24 |

它们更像补充型运力，而不是网络利润的主要来源。

### 2.3 闲置机型

以下机型当前完全未使用：

- `F8C12Y126`：39 架可用，0 架使用
- `F12C0Y132`：8 架可用，0 架使用
- `F8C12Y99`：9 架可用，0 架使用
- `F12C0Y112`：10 架可用，0 架使用
- `F12C30Y117`：44 架可用，0 架使用

这些完全未使用机型对应可用飞机数合计为 `110` 架。该结果说明当前不是所有机型都紧缺，而是少数高适配机型紧缺。

## 3. 航班与航段价值分析

核心依据来自：

- [`task_summary.csv`](../results/runs/model_current/task_summary.csv)
- [`leg_value_analysis.csv`](../results/runs/model_current/leg_value_analysis.csv)
- [`product_assignment_analysis.csv`](../results/runs/model_current/product_assignment_analysis.csv)
- [`task_adjustment_candidates.csv`](../results/runs/model_current/task_adjustment_candidates.csv)
- [`leg_adjustment_candidates.csv`](../results/runs/model_current/leg_adjustment_candidates.csv)

20 场景下共有：

- `473` 个任务被标记为 `Upgauge_or_AddCapacity`
- `93` 个任务被标记为 `Downgauge`
- `5` 个任务被标记为 `Review_Schedule`
- `602` 个航段被标记为 `Upgauge_or_AddCapacity`
- `87` 个航段被标记为 `Downgauge`
- `55` 个航段被标记为 `Review_Schedule`

这说明当前最主要的动作不是全面重排，而是对高价值瓶颈任务进行定向增容，同时对低载客率任务做局部降级或复核。

## 4. 调整建议分析

### 4.1 优先建议扩容或换大机型

优先级最高的对象包括：

- `AA0123` `TFB -> GBJ`，利润 `37,294.80`
- `AA0004` `TFB -> EDB`，利润 `32,488.55`
- `AA0129` `TFB -> GBJ`，利润 `25,690.92`
- `AA0087` `TFB -> BOD`，利润 `25,486.23`
- `AA0083` `TFB -> BOD`，利润 `24,877.32`

这些任务具有高利润、高载客率和正影子价格信号，说明增加容量有直接收益空间。

### 4.2 可以考虑降级机型的任务

被标记为 `Downgauge` 的任务共有 `93` 个，典型例子包括：

- `BA2389` `ZZK -> TFB`，期望载客率 `18.79%`
- `AA0195` `BOD -> GBJ`，期望载客率 `20.21%`
- `AA0042` `CFU -> BOD`，期望载客率 `24.67%`
- `AA0106` `BOD -> TFB`，期望载客率 `26.70%`
- `BA2382` `TFB -> ZZK`，期望载客率 `27.70%`

这些对象不是“应该取消”，而是可以优先考虑换小机型，以释放更大机型去支撑高紧张航线。

### 4.3 应重点复核时刻或保留必要性的任务

被标记为 `Review_Schedule` 的任务共有 `5` 个：

- `AA0138` `BOD -> PSE`，载客率 `9.34%`，利润 `-13,668.36`
- `BA2631` `TFB -> QEY`，载客率 `17.06%`，利润 `-1,072.70`
- `AA0082` `BOD -> TFB`，载客率 `49.67%`，利润 `-751.35`
- `BA2484` `TFB -> CMJ`，载客率 `21.46%`，利润 `-354.00`
- `BA2111` `QTD -> TFB`，载客率 `27.43%`，利润 `-4.90`

这些任务不一定要立刻删除，但需要结合网络连接价值进一步确认。

## 5. 任务四的最终回答口径

如果直接面向题目作答，推荐这样组织：

1. 并购后机队使用明显分化，`F16C0Y165` 与 `F0C0Y76` 是主力且偏紧张。
2. 多个机型家族明显闲置，说明当前更可能是结构错配而不是总量不足。
3. 网络中存在大量容量瓶颈，高影子价格航段达到 `602`。
4. 对高价值满载任务优先换大机型或补运力。
5. 对中低负载、低影子价格任务优先考虑降级。
6. 对极低载客率且亏损任务进行时刻/航班复核。

20 场景主线相较原 5 场景归档结果仅 `54/739` 个任务发生机型调整，总利润变化约 `-0.32%`，说明上述结构性调整建议具有较好的稳定性。

## 6. 当前限制

- 当前建议以现有解的解释和管理建议为主，而不是新的排班重构模型。
- 20 场景比 5 场景更稳健，但仍不应包装为“大规模 Monte Carlo”主卖点。
- 若后续继续扩展场景数，应另设结果目录，并保留当前 20 场景主线作为对照。
