# Visualization Module

这个目录属于展示层，不是核心建模层，但对理解网络结构和展示结果有帮助。

## 文件说明

| 文件 | 作用 | 输入 | 输出 |
| --- | --- | --- | --- |
| [`build_airport_timeline_network.py`](build_airport_timeline_network.py) | 从机场时间网络 JSON 生成 HTML 网络图 | `data/model_input/network/airport_timeline.json` | `results/network/airport_timeline_network_v3.html` |
| [`plot_assignment_by_airline.py`](plot_assignment_by_airline.py) | 按航司/任务类别统计分配机型数量 | `results/runs/root_current/assignment.csv` | `results/figures/post_analysis/assignment_by_airline.png` |

## 当前要注意的点

- `plot_assignment_by_airline.py` 依赖的是 `root_current/assignment.csv`，它是历史结果口径，不是 `model_current/` 目录。
- `build_airport_timeline_network.py` 生成的 HTML 依赖 `results/network/assets/bindings/utils.js`，路径已经按新结构修正。

## 什么时候需要看这里

- 想快速理解机场时间网络结构时。
- 想做展示材料、PPT 或报告配图时。
- 想核对经停与航班连接关系的可视化表达时。
