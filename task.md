# Task Status

最后更新：2026-04-23

这个文件现在不再是“待办清单”，而是整个仓库当前完成状态的集中说明。

## 当前总体状态

题目中的四个核心问题都已经完成主线作答，仓库当前处于：

> 主线结果已完成，文档与输出已收口，后续工作以补充说明和可选扩展为主。

## 四个问题的完成情况

### 题目要求 1：并购前后收益比较

完成情况：已完成

当前口径：

- 主口径：原始历史销量口径
- 对照口径：RF 还原需求口径

已完成内容：

- `A_Only / B_Only / Joint_Venture_AB` 产品分类与收益拆分
- 并购前后票务收入比较
- 新增收入来源拆解
- 原始口径与 RF 对照口径并列表

对应输出：

- [`docs/question1_answer.md`](docs/question1_answer.md)
- [`results/runs/question1_current`](results/runs/question1_current)
- [`results/runs/question1_current/rf_restored`](results/runs/question1_current/rf_restored)
- [`results/figures/question1`](results/figures/question1)

### 题目要求 2：旅客行程选择行为分析

完成情况：已完成

当前口径：

- 正式路线：`Random Forest`
- 对照路线：`EM`

已完成内容：

- 基于 RD 结构的规则式截断识别
- 仅用未截断样本训练 `near_ratio` 行为模型
- 对截断产品恢复 `final_demand`
- 基于 `final_demand` 回答“特征如何影响总需求”
- 下游 JSON 同步到正式主模型输入

对应输出：

- [`src/demand_estimation/passenger_choice_random_forest.md`](src/demand_estimation/passenger_choice_random_forest.md)
- [`data/interim/passenger_choice`](data/interim/passenger_choice)
- [`data/model_input/demand/product_info_rf_predicted.json`](data/model_input/demand/product_info_rf_predicted.json)

### 题目要求 3：并购后机型分配方案

完成情况：已完成

当前口径：

- 正式主模型：[`src/modeling/fleet_assignment_main.py`](src/modeling/fleet_assignment_main.py)
- 正式结果目录：[`results/runs/model_current`](results/runs/model_current)（当前为 20 场景）
- 原 5 场景归档：[`results/runs/model_current_5scenario_archive_2026-04-23`](results/runs/model_current_5scenario_archive_2026-04-23)

已完成内容：

- 固定 RF 恢复后的需求输入
- 求解并购后机型分配方案
- 输出收益、成本、利润、未满足需求、载客率与结构化分析表
- 将 20 场景 Monte Carlo 作为正式主线，原 5 场景保留为归档对照

对应输出：

- [`docs/final_model_spec.md`](docs/final_model_spec.md)
- [`docs/monte_carlo_20_scenario_handoff.md`](docs/monte_carlo_20_scenario_handoff.md)
- [`src/modeling/fleet_assignment_main.md`](src/modeling/fleet_assignment_main.md)
- [`results/runs/model_current`](results/runs/model_current)
- [`results/runs/model_mc20_2026-04-23`](results/runs/model_mc20_2026-04-23)
- [`results/runs/model_current_5scenario_archive_2026-04-23`](results/runs/model_current_5scenario_archive_2026-04-23)

### 题目要求 4：机队使用情况与调整建议

完成情况：已完成

当前口径：

- 不再重新建模
- 基于问题三结果做机队使用解释、瓶颈识别与调整建议
- 基于 20 场景主线结果做正式解释与调整建议

已完成内容：

- 机型使用画像
- 航班与航段价值评估
- 调整候选任务与航段识别
- 机型性价比与闲置解释
- 一套可直接用于报告的图形与配套文字
- 基于 20 场景结果生成第四问分析包

对应输出：

- [`docs/question4_answer.md`](docs/question4_answer.md)
- [`docs/question4_current_analysis.md`](docs/question4_current_analysis.md)
- [`docs/question4_figure_notes.md`](docs/question4_figure_notes.md)
- [`docs/question4_additional_findings.md`](docs/question4_additional_findings.md)
- [`results/figures/question4`](results/figures/question4)
- [`results/analysis/question4_mc20_2026-04-23`](results/analysis/question4_mc20_2026-04-23)

## 当前正式主线

- 问题一：原始历史销量为主，RF 对照为辅
- 问题二：RF 两阶段需求恢复主线
- 问题三：`fleet_assignment_main.py`
- 问题四：基于问题三结果的管理解释模块

## 当前不再视为主线的内容

- `EM + robust model`：稳健性/对照补充
- Monte Carlo：正式结果默认 `20` 场景，原 `5` 场景仅作为归档对照；仍不把大规模 Monte Carlo 作为主要技术卖点
- 全量零需求恢复：暂不并入主线

## 仍可继续扩展的方向

这些内容当前都属于“可选扩展”，不是主线缺口：

1. 为问题一补充利润比较口径
2. 为问题二单独研究“零需求恢复”
3. 为问题三恢复 `network` JSON 的端到端生成链路
4. 为问题四继续压缩成更适合直接交作业的终稿
