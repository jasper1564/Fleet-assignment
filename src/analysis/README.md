# Analysis Module

最后更新：2026-04-23

这个目录主要承担三类工作：

1. 为问题一提供并购前后收益比较与图形解释
2. 为问题二提供截断、行为与需求恢复解释
3. 为问题四提供机队使用、瓶颈与调整建议的后分析输出

## 当前在整套题目中的位置

- 问题一：正式分析脚本入口在这里
- 问题二：若要解释为什么需要做需求恢复，也会回到这里
- 问题四：最终图形包和补充分析主要在这里落地

## 文件说明

| 文件 | 作用 | 当前定位 |
| --- | --- | --- |
| [`analyze_question1_revenue.py`](analyze_question1_revenue.py) | 任务一并购前后收益比较 | 正式分析脚本 |
| [`plot_project_technical_roadmap.py`](plot_project_technical_roadmap.py) | 项目总体技术路线图可视化 | 项目总览脚本 |
| [`analyze_itinerary_sales_truncation.py`](analyze_itinerary_sales_truncation.py) | 行程级销售截断分析 | 问题二支撑分析 |
| [`analyze_flight_capacity_truncation.py`](analyze_flight_capacity_truncation.py) | 航班级容量截断分析 | 问题二支撑分析 |
| [`analyze_carrier_truncation.py`](analyze_carrier_truncation.py) | 航司维度截断分析 | 问题二支撑分析 |
| [`analyze_fare_class_truncation.py`](analyze_fare_class_truncation.py) | 舱位层级截断分析 | 问题二支撑分析 |
| [`plot_sales_vs_demand.py`](plot_sales_vs_demand.py) | 销量与需求关系探索图 | 探索性图形 |
| [`plot_leg_demand_sales_capacity.py`](plot_leg_demand_sales_capacity.py) | 航段需求-销量-容量后分析 | 历史/辅助图形 |
| [`plot_question4_results.py`](plot_question4_results.py) | 问题四正式图形输出脚本 | 正式图形脚本 |
| [`generate_question4_report.py`](generate_question4_report.py) | 基于指定结果目录生成问题四 Markdown 与复核表 | 20 场景主线分析/可复用报告脚本 |

## 问题一当前输出

[`analyze_question1_revenue.py`](analyze_question1_revenue.py) 当前会输出：

- [`results/runs/question1_current/question1_summary.csv`](../../results/runs/question1_current/question1_summary.csv)
- [`results/runs/question1_current/carrier_revenue_summary.csv`](../../results/runs/question1_current/carrier_revenue_summary.csv)
- [`results/runs/question1_current/network_expansion_summary.csv`](../../results/runs/question1_current/network_expansion_summary.csv)
- [`results/runs/question1_current/rf_restored`](../../results/runs/question1_current/rf_restored)
- [`results/runs/question1_current/question1_source_comparison.csv`](../../results/runs/question1_current/question1_source_comparison.csv)
- [`results/figures/question1/question1_revenue_comparison.png`](../../results/figures/question1/question1_revenue_comparison.png)
- [`results/figures/question1/question1_network_expansion.png`](../../results/figures/question1/question1_network_expansion.png)
- [`results/figures/question1/question1_source_comparison.png`](../../results/figures/question1/question1_source_comparison.png)

对应正式答案见：

- [`docs/question1_answer.md`](../../docs/question1_answer.md)

## 项目总览当前输出

[`plot_project_technical_roadmap.py`](plot_project_technical_roadmap.py) 当前会输出：

- [`results/figures/project/project_technical_roadmap.png`](../../results/figures/project/project_technical_roadmap.png)
- [`results/figures/project/project_technical_roadmap.svg`](../../results/figures/project/project_technical_roadmap.svg)
- [`docs/project_technical_roadmap.md`](../../docs/project_technical_roadmap.md)

## 问题四当前输出

[`plot_question4_results.py`](plot_question4_results.py) 当前会输出：

- `question4_fleet_portrait.png`
- `question4_adjustment_actions.png`
- `question4_bottleneck_legs.png`
- `question4_unmet_demand.png`
- `question4_fleet_cost_effectiveness.png`

默认情况下，它读取 `results/runs/model_current` 并输出到 `results/figures/question4`。当前 `model_current` 已经是 20 场景主线。如果要为对照实验单独生成图形，可以设置：

```powershell
$env:QUESTION4_RUN_DIR='results/runs/model_current'
$env:QUESTION4_OUTPUT_DIR='results/analysis/question4_mc20_2026-04-23/figures'
python src/analysis/plot_question4_results.py
```

[`generate_question4_report.py`](generate_question4_report.py) 用于生成 20 场景第四问分析和辅助表：

```powershell
$env:QUESTION4_RUN_DIR='results/runs/model_current'
$env:QUESTION4_BASELINE_RUN_DIR='results/runs/model_current_5scenario_archive_2026-04-23'
$env:QUESTION4_ANALYSIS_DIR='results/analysis/question4_mc20_2026-04-23'
python src/analysis/generate_question4_report.py
```

对应说明文档见：

- [`docs/question4_answer.md`](../../docs/question4_answer.md)
- [`docs/question4_figure_notes.md`](../../docs/question4_figure_notes.md)
- [`docs/question4_additional_findings.md`](../../docs/question4_additional_findings.md)
- [`docs/monte_carlo_20_scenario_handoff.md`](../../docs/monte_carlo_20_scenario_handoff.md)
- [`results/analysis/question4_mc20_2026-04-23`](../../results/analysis/question4_mc20_2026-04-23)

## 当前推荐阅读路径

### 想看问题一

1. [`analyze_question1_revenue.py`](analyze_question1_revenue.py)
2. [`docs/question1_answer.md`](../../docs/question1_answer.md)

### 想看问题二解释链

1. 前四个 `analyze_*truncation.py`
2. [`../demand_estimation/passenger_choice_random_forest.md`](../demand_estimation/passenger_choice_random_forest.md)

### 想看问题四结果

1. [`plot_question4_results.py`](plot_question4_results.py)
2. [`docs/question4_answer.md`](../../docs/question4_answer.md)
3. [`docs/question4_figure_notes.md`](../../docs/question4_figure_notes.md)

## 当前要注意的点

- 这里的大部分脚本不是模型主入口，而是答题解释工具箱。
- `results/runs/` 下的表格必须与对应问题的正式口径一起读。
- 历史图形脚本与正式图形脚本并存，引用时要优先使用当前正式主线对应的输出。
- 20 场景问题四分析已是当前主线；原 5 场景图表已归档到 `results/figures/question4_5scenario_archive_2026-04-23`。
