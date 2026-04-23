# Question 4 Output Plan

最后更新：2026-04-23

这个文件原本用于规划第 4 问的输出结构。  
截至当前版本，这套规划已经落地完成，因此本文件现在改为“归档说明”，用来回答两件事：

1. 当初第 4 问是按什么思路设计出来的
2. 现在这套规划具体落到了哪些正式交付件

## 一、当前状态

第 4 问主线已经完成，当前正式交付件为：

- [`question4_answer.md`](question4_answer.md)
- [`question4_current_analysis.md`](question4_current_analysis.md)
- [`question4_figure_notes.md`](question4_figure_notes.md)
- [`question4_additional_findings.md`](question4_additional_findings.md)
- [`../results/figures/question4`](../results/figures/question4)

当前正式交付件已经切换为 20 场景 Monte Carlo 主线；原 5 场景结果与图表保留为归档对照。

## 二、原始规划思路

第 4 问不再被理解为“再做一个优化模型”，而是基于问题三主模型结果，构建一个面向管理层的解释模块。  
核心目标始终是回答：

- 各机型现在用得合不合理
- 哪些航段和任务是核心瓶颈
- 哪些资源最值得追加容量
- 哪些机型或任务需要复核

## 三、规划与当前交付的对应关系

### 1. 机型使用情况分析

当前已落地到：

- [`../results/runs/model_current/fleet_summary.csv`](../results/runs/model_current/fleet_summary.csv)
- [`question4_answer.md`](question4_answer.md)
- [`../results/figures/question4/question4_fleet_portrait.png`](../results/figures/question4/question4_fleet_portrait.png)

### 2. 航段与任务价值评估

当前已落地到：

- [`../results/runs/model_current/task_summary.csv`](../results/runs/model_current/task_summary.csv)
- [`../results/runs/model_current/leg_value_analysis.csv`](../results/runs/model_current/leg_value_analysis.csv)
- [`../results/runs/model_current/product_assignment_analysis.csv`](../results/runs/model_current/product_assignment_analysis.csv)
- [`../results/figures/question4/question4_bottleneck_legs.png`](../results/figures/question4/question4_bottleneck_legs.png)
- [`../results/figures/question4/question4_unmet_demand.png`](../results/figures/question4/question4_unmet_demand.png)

### 3. 调整建议分析

当前已落地到：

- [`../results/runs/model_current/task_adjustment_candidates.csv`](../results/runs/model_current/task_adjustment_candidates.csv)
- [`../results/runs/model_current/leg_adjustment_candidates.csv`](../results/runs/model_current/leg_adjustment_candidates.csv)
- [`../results/figures/question4/question4_adjustment_actions.png`](../results/figures/question4/question4_adjustment_actions.png)

### 4. 闲置机型解释补充

当前已落地到：

- [`question4_additional_findings.md`](question4_additional_findings.md)
- [`../results/figures/question4/question4_fleet_cost_effectiveness.png`](../results/figures/question4/question4_fleet_cost_effectiveness.png)

## 四、当前推荐引用链路

如果只是为了快速写报告，当前推荐直接使用：

1. [`question4_answer.md`](question4_answer.md)
2. [`question4_figure_notes.md`](question4_figure_notes.md)
3. [`question4_additional_findings.md`](question4_additional_findings.md)

如果还需要理解更完整的分析推导过程，再补读：

4. [`question4_current_analysis.md`](question4_current_analysis.md)

## 五、当前剩余工作

从项目主线角度看，第 4 问已经完成。后续若继续扩展，只属于可选增强，例如：

- 将文字再压缩成更适合直接交作业的终稿
- 与问题一、问题三做更强的对照叙事
- 补更细的灵敏度说明
