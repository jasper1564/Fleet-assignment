# 课程设计任务书与完成情况

最后更新：2026-04-23

## 一、项目目标

本仓库围绕课程设计题目“航空公司机型分配问题”展开，目标是基于题目提供的航班、机队、产品销售与市场份额数据，回答以下四个问题：

1. 分析并比较 A 公司并购前后的收益情况。
2. 根据给定数据分析旅客行程选择行为，判断影响机票销售的因素。
3. 为并购后的每日航班制定新的机型分配方案，并计算收益与运营成本。
4. 分析各机型使用情况，并提出是否需要进一步调整机队或航班计划的建议。

当前主线工作已经全部完成。

## 二、整体完成状态

| 题目问题 | 当前状态 | 当前正式口径 | 主要交付件 |
| --- | --- | --- | --- |
| 问题一：并购前后收益比较 | 已完成 | 原始历史销量为主，RF 还原需求为对照 | `docs/question1_answer.md`, `results/runs/question1_current/` |
| 问题二：旅客行程选择行为分析 | 已完成 | RF 两阶段需求恢复框架 | `src/demand_estimation/passenger_choice_random_forest.md` |
| 问题三：并购后机型分配方案 | 已完成 | `fleet_assignment_main.py` + RF 恢复需求输入 + 20 场景 Monte Carlo | `docs/final_model_spec.md`, `results/runs/model_current/` |
| 问题四：机队使用与调整建议 | 已完成 | 基于 20 场景问题三结果的管理解释模块 | `docs/question4_answer.md`, `results/figures/question4/`, `results/analysis/question4_mc20_2026-04-23/` |

## 三、四个问题分别做了什么

### 问题一：并购前后收益比较

题目要求：

> 分析并比较 A 公司并购前后的收益情况。

我们的完成方式：

- 不直接把第三问优化结果提前挪来回答第一问
- 先用原始产品销售数据构造历史票务收入口径
- 按 `A_Only / B_Only / Joint_Venture_AB` 拆分产品来源
- 计算并购前后收入规模、增量来源和网络扩张情况
- 再额外补一版基于 RF 还原需求的对照结果

当前结论：

- 原始历史销量口径下，并购后票务收入较并购前提升约 `31.63%`
- RF 对照口径下，增幅约 `32.13%`
- 结论稳定：收益增长主要来自 B 网络接入与联程协同双重作用

主要输出：

- [`question1_answer.md`](question1_answer.md)
- [`../results/runs/question1_current`](../results/runs/question1_current)
- [`../results/figures/question1`](../results/figures/question1)

### 问题二：旅客行程选择行为分析

题目要求：

> 根据给定数据分析旅客行程选择行为，判断影响机票销售的因素。

我们的完成方式：

- 将“影响因素分析”与“需求恢复”合并成同一条可解释链路
- 先基于 RD 列结构做规则式截断识别
- 仅用未截断样本训练 `near_ratio` 行为模型
- 再对截断产品恢复 `final_demand`
- 最后基于 `final_demand` 回答“特征如何影响总需求”

当前结论：

- 随机森林主线已经从“解释近端购票占比”升级为“解释总需求”
- 当前恢复后的总需求为 `84,974.02`
- 数据问题不只来自截断，也来自大量零销量产品，但零需求恢复尚未并入主线

主要输出：

- [`../src/demand_estimation/passenger_choice_random_forest.md`](../src/demand_estimation/passenger_choice_random_forest.md)
- [`../data/interim/passenger_choice`](../data/interim/passenger_choice)
- [`../results/figures/passenger_choice`](../results/figures/passenger_choice)

### 问题三：并购后机型分配方案

题目要求：

> 为并购后的每日航班制定新的机型分配方案，并计算收益与运营成本。

我们的完成方式：

- 使用 RF 恢复后的需求输入
- 以 `fleet_assignment_main.py` 作为正式主模型
- 使用 20 个 Monte Carlo 场景刻画需求波动
- 输出收益、成本、利润、载客率、影子价格及结构化结果表

当前结论：

- 总收入 `11,902,969.36`
- 总成本 `6,455,770.83`
- 总利润 `5,447,198.52`
- 总未满足需求 `13,539.85`
- 加权载客率 `87.49%`
- 相对原 5 场景归档结果，总利润变化约 `-0.32%`

主要输出：

- [`final_model_spec.md`](final_model_spec.md)
- [`monte_carlo_20_scenario_handoff.md`](monte_carlo_20_scenario_handoff.md)
- [`../src/modeling/fleet_assignment_main.md`](../src/modeling/fleet_assignment_main.md)
- [`../results/runs/model_current`](../results/runs/model_current)
- [`../results/runs/model_mc20_2026-04-23`](../results/runs/model_mc20_2026-04-23)
- [`../results/runs/model_current_5scenario_archive_2026-04-23`](../results/runs/model_current_5scenario_archive_2026-04-23)

### 问题四：机队使用情况与调整建议

题目要求：

> 分析各机型使用情况，并提出是否需要进一步调整机队或航班计划的建议。

我们的完成方式：

- 不再另建一个新的优化模型
- 基于问题三结果做机队使用画像、瓶颈识别与调整建议
- 配套输出可直接用于报告的图表与说明文字
- 补充解释“为什么部分机型完全没有被使用”

当前结论：

- 当前不是“总飞机数不够”，而是“主力机型偏紧、部分机型闲置”
- `F16C0Y165` 与 `F0C0Y76` 是当前网络的核心主力机型
- 若干 `0` 使用机型更像性价比筛选结果，而不是求解失败
- 当前 20 场景主线相对原 5 场景仅 `54/739` 个任务更换机型，核心结论保持稳定

主要输出：

- [`question4_answer.md`](question4_answer.md)
- [`question4_current_analysis.md`](question4_current_analysis.md)
- [`question4_figure_notes.md`](question4_figure_notes.md)
- [`question4_additional_findings.md`](question4_additional_findings.md)
- [`../results/figures/question4`](../results/figures/question4)
- [`../results/analysis/question4_mc20_2026-04-23`](../results/analysis/question4_mc20_2026-04-23)

## 四、当前正式主线与对照线

### 正式主线

- 问题一：原始历史销量口径
- 问题二：RF 需求恢复
- 问题三：`fleet_assignment_main.py`
- 问题四：基于问题三结果的解释模块

### 对照与扩展

- 问题一：RF 还原需求对照口径
- 问题二：EM 需求恢复路线
- 问题三：`fleet_assignment_robust.py`
- 原 5 场景 Monte Carlo：归档对照，不替代正式 20 场景结果
- 未来扩展：零需求恢复、更大规模 Monte Carlo、网络输入 JSON 重建

## 五、当前最重要的项目判断

1. 问题一与问题三必须分口径，不能把优化后的利润结果提前塞进历史收益比较。
2. RF 路线是第二问的正式答题主线，EM 只保留为稳健性对照。
3. 第四问已经完成为“解释模块”，不再继续扩成第二个优化模型。
4. 当前仓库已经处于“可交付、可汇报、可答辩”的状态。

## 六、如果后续还要继续扩展

这些内容当前都不属于主线缺口，而属于可选增强：

1. 给问题一补充利润比较口径
2. 单独设计零需求恢复分支
3. 恢复 `network` JSON 的端到端生成链路
4. 压缩文档措辞，进一步适配最终报告或 PPT
