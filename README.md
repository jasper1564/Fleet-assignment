# Repo Handoff

最后更新：2026-04-20

## 这是什么

这个仓库的核心目标不是做一个通用的运筹优化框架，而是完成 [`docs/problem_statement/fleet_assignment_problem_statement.docx`](docs/problem_statement/fleet_assignment_problem_statement.docx) 对应的大作业题目：

- 并购前后收益比较
- 旅客行程选择行为分析
- 并购后机型分配方案设计
- 机队使用情况分析与调整建议

把这个仓库看成“为完成题目而搭建的分析与建模代码库”会更准确。

## 先看什么

接手这个项目时，推荐按下面顺序获取上下文：

1. [`docs/problem_statement/README.md`](docs/problem_statement/README.md)
2. [`src/modeling/README.md`](src/modeling/README.md)
3. [`src/demand_estimation/README.md`](src/demand_estimation/README.md)
4. [`task.md`](task.md)

如果只想最快把握现状，前 3 个文件已经足够。

## 当前结论

- 仓库结构重构已完成，主目录稳定为 `data / src / results / docs / archive`。
- `src/` 下当前主流程脚本已经改到新路径，且做过语法检查。
- 当前需求处理存在两条路线，但地位并不对等：
  - `RF` 路线：基于题目第 2 问的影响因素分析来还原需求，属于当前答题主线。
  - `EM` 路线：还原结果更稳健，且结果和影子价格都能跑出来，但不符合题目“通过第二问分析来还原需求”的要求，因此更适合作为对照或稳健性参考。
- 当前正式答题模型仍是 `RF + fleet_assignment_main.py`，并将 `Monte Carlo` 固定为轻量 `5` 场景波动刻画。
- 高场景数 `Monte Carlo` 的边际价值被认为较低，因此不再作为主线追求方向。
- `archive/` 是历史资产区，不是当前开发入口。

## 当前主线结构

### 题目来源

- 题目正文与要求：[`docs/problem_statement/fleet_assignment_problem_statement.docx`](docs/problem_statement/fleet_assignment_problem_statement.docx)
- 开发者摘要：[`docs/problem_statement/README.md`](docs/problem_statement/README.md)

### 数据主线

- 原始输入：[`data/raw`](data/raw)
- 中间结果：[`data/interim`](data/interim)
- 模型直接输入：[`data/model_input`](data/model_input)

### 代码主线

- 预处理：[`src/preprocessing`](src/preprocessing)
- 需求分析与还原：[`src/demand_estimation`](src/demand_estimation)
- 机型分配建模：[`src/modeling`](src/modeling)
- 诊断与后分析：[`src/analysis`](src/analysis)
- 可视化：[`src/visualization`](src/visualization)

### 结果主线

- 结构化运行结果：[`results/runs`](results/runs)
- 图形输出：[`results/figures`](results/figures)
- 网络 HTML：[`results/network`](results/network)

## 现在最重要的事实

### 1. 当前权威任务来源是题目文档，不是代码

代码里保留了多版建模尝试，但“什么算完成”应由题目要求决定。任何后续开发都应围绕题目四个问题组织，而不是围绕某个脚本本身组织。

### 2. 当前主线应以题意为准，`RF` 是答题主线，`EM` 是参考线

- [`src/modeling/fleet_assignment_main.py`](src/modeling/fleet_assignment_main.py) 读取 `data/model_input/demand/product_info_rf_predicted.json`
- [`src/modeling/fleet_assignment_robust.py`](src/modeling/fleet_assignment_robust.py) 读取 `data/model_input/demand/product_info_em_restored.json`

这不只是“模型形式不同”，还意味着两者的项目角色不同：

- `RF + main model` 更符合题目要求，是当前默认答题主线。
- `EM + robust model` 更像对照实验或稳健性补充，不宜直接替代题目主线。

### 3. `Monte Carlo` 已经尝试，但当前是阻塞点

项目已经尝试在需求还原之后进一步模拟需求波动，高场景数 `Monte Carlo` 方案会因为内存问题失败，表现为运行时 `out of memory`。

因此当前状态是：

- “需求还原”已经有可用结果。
- “需求波动模拟”保留为轻量版本，默认场景数固定为 `5`。
- 任何接手开发的人都不应再把“大规模场景扩展”当成主要工作方向。

### 4. 网络输入目前是已沉淀产物，不是完整可重建产物

当前建模所依赖的这三份 JSON 已存在：

- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`
- `data/model_input/network/super_flight_schedule.json`

但当前 `src/` 里没有一条完整、清晰、单一入口的脚本去重新生成这三份文件。它们现在更像“已整理好的项目资产”。开发者在改模型前，需要先意识到这一点。

### 5. 结果目录保存的是“历史实验状态”，不全是当前代码刚跑出来的

特别是：

- `results/runs/model_current/` 对应当前主模型目录
- `results/runs/robustness/` 对应稳健模型结果
- `results/runs/variants/` 是历史版本试验
- `results/runs/root_current/` 含部分旧式输出，如 `assignment.csv`

不要默认所有结果目录都来自同一版代码。

## 当前代码地图

| 区域 | 当前作用 | 接手时的重点 |
| --- | --- | --- |
| [`src/preprocessing`](src/preprocessing) | 从原始航班与产品销售表生成中间表 | 看清哪些中间表仍在被后续脚本使用 |
| [`src/demand_estimation`](src/demand_estimation) | 建立 RF 主线与 EM 对照线 | 先确认题目要求决定了 RF 才是正式答题路线 |
| [`src/modeling`](src/modeling) | 当前最核心的优化模型代码 | 优先读主模型，再读稳健模型，并注意 Monte Carlo 当前 OOM |
| [`src/analysis`](src/analysis) | 截断分析与结果诊断 | 主要服务题目解释与报告支撑 |
| [`src/visualization`](src/visualization) | 生成网络图和结果图 | 多数是展示层，不是核心建模层 |
| [`archive`](archive) | 保留旧脚本与旧资源 | 除非追溯来源，否则不要优先改这里 |

## 推荐把它理解成三层

1. `题目层`  
   定义最终要回答什么问题。

2. `资产层`  
   包括原始数据、中间数据、模型输入 JSON 和历史结果。

3. `求解层`  
   包括需求还原、机型分配模型、分析与可视化脚本。

后续开发最容易出问题的地方，通常不是求解器，而是“题目目标、输入口径、波动模拟状态、结果目录”这四者没有对齐。

## 当前开发重点

当前开发重点已经从“继续改模型结构”切换为“按第四问完善输出端”。  
具体规格见：

- [`docs/final_model_spec.md`](docs/final_model_spec.md)
- [`docs/question4_output_plan.md`](docs/question4_output_plan.md)

## 当前已补的接管文档

- [`docs/problem_statement/README.md`](docs/problem_statement/README.md)
- [`src/preprocessing/README.md`](src/preprocessing/README.md)
- [`src/demand_estimation/README.md`](src/demand_estimation/README.md)
- [`src/modeling/README.md`](src/modeling/README.md)
- [`src/modeling/variants/README.md`](src/modeling/variants/README.md)
- [`src/analysis/README.md`](src/analysis/README.md)
- [`src/visualization/README.md`](src/visualization/README.md)
- [`task.md`](task.md)
