# Problem Statement Notes

这个目录是整个仓库的任务源头。开发时应默认题目文档高于任何单个脚本。

## 题目原文

- 正文：[`fleet_assignment_problem_statement.docx`](fleet_assignment_problem_statement.docx)

## 题目要解决的四件事

1. 分析并比较 A 公司并购前后的收益情况。
2. 根据给定数据分析旅客行程选择行为，判断影响机票销售的因素。
3. 为并购后的每日航班制定新的机型分配方案，并计算收益与运营成本。
4. 分析各机型使用情况，并提出是否需要进一步调整机队或航班计划的建议。

## 题目中的关键业务约束

- 并购后每日航班总数：815
- 机队规模：211 架飞机，9 种机型
- 飞机最小过站时间：40 分钟
- 经停航班必须由同一架飞机、同一种机型执飞
- 产品规模：约 47190 个行程产品

这些约束会直接影响建模结构，尤其是：

- 航班如何聚合成任务
- 经停航班如何处理
- 飞机流平衡如何建模
- 需求与座位约束如何连接

## 题目原始附件与当前仓库映射

| 题目附件名 | 当前仓库路径 |
| --- | --- |
| `data_fam_schedule.csv` | [`../../data/raw/schedule/flight_schedule.csv`](../../data/raw/schedule/flight_schedule.csv) |
| `data_fam_fleet.csv` | [`../../data/raw/reference/fleet_family_master.csv`](../../data/raw/reference/fleet_family_master.csv) |
| `data_fam_products.csv` | [`../../data/raw/booking/itinerary_sales_by_rd.csv`](../../data/raw/booking/itinerary_sales_by_rd.csv) |
| `data_fam_market_share.csv` | [`../../data/raw/reference/market_share_by_od.csv`](../../data/raw/reference/market_share_by_od.csv) |

## 代码与题目要求的大致映射

| 题目要求 | 主要代码区域 |
| --- | --- |
| 收益比较 | [`../../src/modeling`](../../src/modeling), [`../../results/runs`](../../results/runs) |
| 旅客选择行为分析 | [`../../src/demand_estimation`](../../src/demand_estimation), [`../../src/analysis`](../../src/analysis) |
| 新机型分配方案 | [`../../src/modeling`](../../src/modeling) |
| 机队使用与调整建议 | [`../../src/modeling`](../../src/modeling), [`../../src/analysis`](../../src/analysis), [`../../results/runs`](../../results/runs) |

## 开发时的默认原则

- 如果代码结构与题目要求冲突，以题目要求为准。
- 如果多个模型版本都能运行，优先选最能直接回答题目四个问题的版本。
- 如果某个结果很好看但无法映射回题目要求，它在提交优先级上应降低。
