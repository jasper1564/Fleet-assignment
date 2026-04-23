# Repo Handoff

最后更新：2026-04-23

## 这是什么

这个仓库用于完成课程设计题目 [`docs/problem_statement/fleet_assignment_problem_statement.docx`](docs/problem_statement/fleet_assignment_problem_statement.docx) 对应的四个问题：

1. 并购前后收益比较
2. 旅客行程选择行为分析
3. 并购后机型分配方案设计
4. 机队使用情况分析与调整建议

当前主线工作已经完成，仓库现在更适合被理解成：

> 一套围绕题目四个问题整理好的数据、建模、结果解释与答题文档仓库。

## 先看什么

如果是第一次接手这个仓库，推荐按下面顺序获取上下文：

1. [`docs/problem_statement/README.md`](docs/problem_statement/README.md)
2. [`docs/repo_taskbook.md`](docs/repo_taskbook.md)
3. [`docs/final_model_spec.md`](docs/final_model_spec.md)
4. [`docs/monte_carlo_20_scenario_handoff.md`](docs/monte_carlo_20_scenario_handoff.md)
5. [`task.md`](task.md)

如果只想快速查看最终答题材料，优先看：

1. [`docs/question1_answer.md`](docs/question1_answer.md)
2. [`src/demand_estimation/passenger_choice_random_forest.md`](src/demand_estimation/passenger_choice_random_forest.md)
3. [`results/runs/model_current`](results/runs/model_current)
4. [`docs/question4_answer.md`](docs/question4_answer.md)
5. [`docs/question4_figure_notes.md`](docs/question4_figure_notes.md)

## 当前正式口径

### 总体答题口径

- 问题一：以原始历史销量口径回答并购前后票务收入变化，同时保留 RF 还原需求口径作为对照。
- 问题二：以 `Random Forest` 两阶段需求恢复框架为正式路线。
- 问题三：以 [`src/modeling/fleet_assignment_main.py`](src/modeling/fleet_assignment_main.py) 为正式机型分配主模型。
- 问题四：不再重新建模，而是基于问题三结果做管理解释与调整建议。

### 当前正式技术主线

- 正式需求输入：[`data/model_input/demand/product_info_rf_predicted.json`](data/model_input/demand/product_info_rf_predicted.json)
- 正式主模型：[`src/modeling/fleet_assignment_main.py`](src/modeling/fleet_assignment_main.py)
- 正式主结果：[`results/runs/model_current`](results/runs/model_current)（当前为 20 场景）
- `EM + robust model`：保留为对照/稳健性补充，不作为主答案
- `Monte Carlo`：正式主线使用 `20` 个需求场景，原 `5` 场景结果保留为归档对照
- 20 场景主线交接：[`docs/monte_carlo_20_scenario_handoff.md`](docs/monte_carlo_20_scenario_handoff.md)

## 四个问题的最终交付件

### 问题一：并购前后收益比较

- 正式答案：[`docs/question1_answer.md`](docs/question1_answer.md)
- 原始历史销量结果：[`results/runs/question1_current`](results/runs/question1_current)
- RF 对照结果：[`results/runs/question1_current/rf_restored`](results/runs/question1_current/rf_restored)
- 图形输出：[`results/figures/question1`](results/figures/question1)

当前结论摘要：

- 原始历史销量口径下，并购前票务收入约 `9.88M`，并购后约 `13.01M`，新增约 `3.13M`，增幅 `31.63%`
- RF 还原需求口径下，新增收入约 `3.32M`，增幅 `32.13%`
- 结论稳定：并购收益增长主要来自 B 网络接入与联程协同双重作用

### 问题二：旅客行程选择行为分析

- 模块说明：[`src/demand_estimation/README.md`](src/demand_estimation/README.md)
- 核心说明：[`src/demand_estimation/passenger_choice_random_forest.md`](src/demand_estimation/passenger_choice_random_forest.md)
- 中间结果：[`data/interim/passenger_choice`](data/interim/passenger_choice)
- 图形输出：[`results/figures/passenger_choice`](results/figures/passenger_choice)

当前结论摘要：

- 已完成“截断识别 -> 行为模型 -> 需求恢复 -> 总需求解释”的两阶段 RF 框架
- 当前恢复后的 `final_demand` 总量为 `84,974.02`
- 需求问题不只来自截断，也来自大规模零销量产品，但“零需求恢复”尚未并入主线

### 问题三：并购后机型分配方案

- 模型说明：[`src/modeling/README.md`](src/modeling/README.md)
- 主模型说明：[`src/modeling/fleet_assignment_main.md`](src/modeling/fleet_assignment_main.md)
- 最终模型口径：[`docs/final_model_spec.md`](docs/final_model_spec.md)
- 正式结果目录：[`results/runs/model_current`](results/runs/model_current)（20 场景）
- 原 5 场景归档：[`results/runs/model_current_5scenario_archive_2026-04-23`](results/runs/model_current_5scenario_archive_2026-04-23)

当前结论摘要：

- 当前主模型结果总收入 `11,902,969.36`
- 总成本 `6,455,770.83`
- 总利润 `5,447,198.52`
- 总未满足需求 `13,539.85`
- 加权载客率 `87.49%`
- 与原 5 场景归档结果相比，总利润变化约 `-0.32%`

### 问题四：机队使用情况与调整建议

- 正式答案：[`docs/question4_answer.md`](docs/question4_answer.md)
- 现状分析：[`docs/question4_current_analysis.md`](docs/question4_current_analysis.md)
- 图示说明：[`docs/question4_figure_notes.md`](docs/question4_figure_notes.md)
- 补充发现：[`docs/question4_additional_findings.md`](docs/question4_additional_findings.md)
- 图形输出：[`results/figures/question4`](results/figures/question4)（20 场景）
- 20 场景分析包：[`results/analysis/question4_mc20_2026-04-23`](results/analysis/question4_mc20_2026-04-23)

当前结论摘要：

- 当前网络不是“总机队数量不够”，而是“少数主力机型偏紧、部分机型明显闲置”
- `F16C0Y165` 和 `F0C0Y76` 是核心主力机型
- 若干 `0` 使用机型更像性价比筛选结果，而不是求解失败
- 当前 20 场景主线相比原 5 场景只带来少量边际机型重排

## 当前最重要的项目判断

### 1. 题目要求优先于单个脚本

仓库中保留了历史版本和对照版本，但什么算正式答案，应当由题目四个问题决定，而不是由某个版本号决定。

### 2. 问题一与问题三不能混口径

问题一回答的是“历史收益比较”，不能直接拿问题三的优化后结果去替代。  
当前仓库已经明确把这两件事分开：

- 问题一：原始历史销售口径为主，RF 修正版为对照
- 问题三：RF 需求恢复后的机型分配优化结果

### 3. 问题四是解释模块，不是第二个优化模型

问题四已经不再继续追求“再解一个更复杂的模型”，而是围绕当前最优分配结果做管理解释和结构性建议。

### 4. 仓库中仍保留若干对照线与历史资产

- `results/runs/robustness/`：稳健性对照
- `results/runs/model_mc20_2026-04-23/`：20 场景原始运行结果，与当前 `model_current` 内容一致
- `results/runs/model_current_5scenario_archive_2026-04-23/`：原 5 场景结果归档
- `results/analysis/question4_mc20_2026-04-23/`：20 场景下的第四问分析包
- `results/runs/variants/`：历史建模变体
- `data/model_input/network/*.json`：当前已沉淀的网络输入资产

这些内容仍然重要，但不应覆盖当前主线。

## 仓库结构

### 数据

- 原始输入：[`data/raw`](data/raw)
- 中间结果：[`data/interim`](data/interim)
- 模型输入：[`data/model_input`](data/model_input)

### 代码

- 预处理：[`src/preprocessing`](src/preprocessing)
- 需求分析与恢复：[`src/demand_estimation`](src/demand_estimation)
- 机型分配建模：[`src/modeling`](src/modeling)
- 结果分析与图形：[`src/analysis`](src/analysis)
- 展示层可视化：[`src/visualization`](src/visualization)

### 输出

- 结构化结果：[`results/runs`](results/runs)
- 图形输出：[`results/figures`](results/figures)
- 网络 HTML：[`results/network`](results/network)

## 后续如果还要继续做什么

当前四个问题的主线都已经完成。后续如果继续扩展，优先级建议如下：

1. 压缩和统一最终报告语言
2. 如果确实需要，再补问题一的利润比较口径
3. 将“零需求恢复”作为独立分支单独研究
4. 如有需要，再恢复 `network` JSON 的端到端生成链路
