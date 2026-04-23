# Problem Statement Notes

最后更新：2026-04-23

这个目录是整个仓库的任务源头。  
开发时应默认题目文档高于任何单个脚本、历史实验目录或局部图形结果。

## 题目原文

- 正文：[`fleet_assignment_problem_statement.docx`](fleet_assignment_problem_statement.docx)

## 题目中的四个问题

1. 分析并比较 A 公司并购前后的收益情况。
2. 根据给定数据分析旅客行程选择行为，判断影响机票销售的因素。
3. 为并购后的每日航班制定新的机型分配方案，并计算收益与运营成本。
4. 分析各机型使用情况，并提出是否需要进一步调整机队或航班计划的建议。

## 关键业务约束

- 并购后每日航班总数：`815`
- 机队规模：`211` 架飞机，`9` 种机型
- 飞机最小过站时间：`40` 分钟
- 经停航班必须由同一架飞机、同一种机型执飞
- 产品规模：约 `47,190` 个行程产品

这些约束直接决定了后续分析和建模结构，尤其影响：

- 航班如何聚合成任务
- 经停航班如何打包
- 飞机流平衡如何建立
- 需求与座位约束如何连接

## 原始附件与当前仓库映射

| 题目附件名 | 当前仓库路径 |
| --- | --- |
| `data_fam_schedule.csv` | [`../../data/raw/schedule/flight_schedule.csv`](../../data/raw/schedule/flight_schedule.csv) |
| `data_fam_fleet.csv` | [`../../data/raw/reference/fleet_family_master.csv`](../../data/raw/reference/fleet_family_master.csv) |
| `data_fam_products.csv` | [`../../data/raw/booking/itinerary_sales_by_rd.csv`](../../data/raw/booking/itinerary_sales_by_rd.csv) |
| `data_fam_market_share.csv` | [`../../data/raw/reference/market_share_by_od.csv`](../../data/raw/reference/market_share_by_od.csv) |

## 当前仓库中的正式回答映射

| 题目问题 | 当前正式回答路径 |
| --- | --- |
| 问题一：并购前后收益比较 | [`../../docs/question1_answer.md`](../../docs/question1_answer.md), [`../../results/runs/question1_current`](../../results/runs/question1_current) |
| 问题二：旅客选择行为分析 | [`../../src/demand_estimation/passenger_choice_random_forest.md`](../../src/demand_estimation/passenger_choice_random_forest.md), [`../../data/interim/passenger_choice`](../../data/interim/passenger_choice) |
| 问题三：并购后机型分配方案 | [`../../docs/final_model_spec.md`](../../docs/final_model_spec.md), [`../../src/modeling/fleet_assignment_main.md`](../../src/modeling/fleet_assignment_main.md), [`../../results/runs/model_current`](../../results/runs/model_current) |
| 问题四：机队使用与调整建议 | [`../../docs/question4_answer.md`](../../docs/question4_answer.md), [`../../docs/question4_figure_notes.md`](../../docs/question4_figure_notes.md), [`../../results/figures/question4`](../../results/figures/question4) |

说明：当前 `results/runs/model_current` 与 `results/figures/question4` 已切换为 20 场景 Monte Carlo 正式主线；原 5 场景结果只作为归档对照保留。

## 当前项目的默认原则

- 如果代码结构与题目要求冲突，以题目要求为准。
- 如果多个模型版本都能运行，优先选择最能直接回答题目四个问题的版本。
- 如果某个结果很好看但无法映射回题目要求，它在提交优先级上应降低。
- 问题一与问题三不能混口径：
  - 问题一回答历史收益比较
  - 问题三回答优化后的机型分配结果

## 推荐补读顺序

1. [`../../docs/repo_taskbook.md`](../../docs/repo_taskbook.md)
2. [`../../docs/final_model_spec.md`](../../docs/final_model_spec.md)
3. [`../../src/demand_estimation/README.md`](../../src/demand_estimation/README.md)
4. [`../../src/modeling/README.md`](../../src/modeling/README.md)
