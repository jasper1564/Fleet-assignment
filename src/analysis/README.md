# Analysis Module

这个目录主要服务两类目标：

- 为题目第 2 问提供行为与截断解释
- 为题目第 4 问提供模型结果诊断与后分析

## 文件说明

| 文件 | 作用 | 主要输出 |
| --- | --- | --- |
| [`analyze_itinerary_sales_truncation.py`](analyze_itinerary_sales_truncation.py) | 行程级销售截断分析 | `data/interim/truncation/itinerary_truncation_flags.csv` 及 3 张图 |
| [`analyze_flight_capacity_truncation.py`](analyze_flight_capacity_truncation.py) | 航班级容量截断分析 | `data/interim/truncation/flight_truncation_flags.csv` 及相关图 |
| [`analyze_carrier_truncation.py`](analyze_carrier_truncation.py) | 航司维度截断分析 | `data/interim/truncation/carrier_truncation_flags.csv` 及相关图 |
| [`analyze_fare_class_truncation.py`](analyze_fare_class_truncation.py) | 舱位/票价层级截断分析 | `data/interim/truncation/fare_level_truncation_flags.csv` 及相关图 |
| [`plot_sales_vs_demand.py`](plot_sales_vs_demand.py) | 对销售与需求关系做探索性散点图 | 图形展示为主 |
| [`plot_leg_demand_sales_capacity.py`](plot_leg_demand_sales_capacity.py) | 对模型结果做航段需求-销量-容量后分析 | `results/figures/post_analysis/` 下图形 |

## 这些脚本在项目里的位置

- 它们大多不是模型主入口。
- 但它们会决定你能否把题目第 2 问和第 4 问讲清楚。
- 如果报告要解释“为什么要做需求恢复”或“为什么某些航段值得调整”，这里的图和统计很重要。

## 当前阅读建议

### 想解释需求截断

优先看前四个 `analyze_*truncation.py`。

### 想解释模型结果

优先看 `plot_leg_demand_sales_capacity.py`。

## 当前限制

- 这些分析脚本和主模型之间还不是强耦合的自动流水线。
- 更准确地说，它们现在更像“支撑报告解释的分析工具箱”。
