# `fleet_assignment_main.py`

最后更新：2026-04-23

## 为什么存在

这是当前最接近“正式答题主模型入口”的机型分配模型文件。

## 它依赖什么

### 需求输入

- `data/model_input/demand/product_info_rf_predicted.json`

### 网络输入

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 机队参考

- `data/raw/reference/fleet_family_master.csv`

## 它在做什么

1. 读取产品需求、票价、航班任务和机场事件网络。
2. 读取机队规模、座位数和飞行成本。
3. 生成轻量 Monte Carlo 需求场景。
4. 建立机型分配优化模型。
5. 输出收益、销量、负载率、影子价格、地面停放和摘要表。

## 结果目录

- 正式默认目录：`results/runs/model_current/`（20 场景）
- 20 场景原始运行目录：`results/runs/model_mc20_2026-04-23/`
- 原 5 场景归档目录：`results/runs/model_current_5scenario_archive_2026-04-23/`

`fleet_assignment_main.py` 支持通过 `RESULTS_DIR` 环境变量指定输出目录。默认不传时写入 `results/runs/model_current/`，且默认场景数为 `20`。

## 当前这条线为什么重要

- 它直接承接题目第 2 问的 RF 需求恢复结果。
- 它是题目第 3 问机型分配方案的正式主线。
- 它输出的结构化表格又反过来支撑题目第 4 问分析。

## 当前真实状态

- 这条线使用的是基于第 2 问影响因素分析得到的 RF 需求恢复结果。
- 因为题目要求“通过第二问分析来还原需求”，所以这条线应被视为正式答题主线。
- Monte Carlo 目前采用 `20` 场景作为正式主线，用于比原 `5` 场景更稳健地刻画需求波动。
- 原 `5` 场景结果已归档到 `results/runs/model_current_5scenario_archive_2026-04-23/`。
- 当前主结果目录已经可以稳定支撑第 4 问：
  - `fleet_summary.csv`
  - `task_summary.csv`
  - `leg_value_analysis.csv`
  - `product_assignment_analysis.csv`
  - `task_adjustment_candidates.csv`
  - `leg_adjustment_candidates.csv`
  - `scenario_summary.csv`

## 20 场景正式主线

当前正式主线的复现命令：

```powershell
python src/modeling/fleet_assignment_main.py
```

如需另存一次实验结果，可额外设置 `RESULTS_DIR` 与 `EXPERIMENT_NAME`。

关键结果：

- 总收入 `11,902,969.36`
- 总成本 `6,455,770.83`
- 总利润 `5,447,198.52`
- 总未满足需求 `13,539.85`
- 加权载客率 `87.49%`
- 相比原 5 场景归档结果，总利润变化约 `-0.32%`

统一口径见：

- [`../../docs/monte_carlo_20_scenario_handoff.md`](../../docs/monte_carlo_20_scenario_handoff.md)

## 当前解释结果时最关键的一点

当前模型对机队数量采用的是“使用量不超过可用量”的约束，而不是“所有飞机必须出动”的约束。  
因此，某些机型出现 `0` 使用，不必然意味着模型失效；在当前目标函数下，它也可能只是说明这些机型在现有任务结构里性价比较低。

这个发现已经在第 4 问文档中单独记录：

- [`docs/question4_additional_findings.md`](../../docs/question4_additional_findings.md)

## 当前开发热点

- 需求场景生成参数
- 任务与航段映射逻辑
- 目标函数与输出摘要
- 机队成本、座位和收益连接方式
- 模型摘要中的求解状态与结果口径解释

## 当前主要风险

- 改需求输入文件，相当于同时改了实验口径。
- 改网络 JSON，等于改了任务图结构。
- 更大规模 Monte Carlo 场景扩展仍可能 OOM。
- 结果目录里已有历史文件，不应直接当作当前代码唯一真相。
- 继续扩展场景数做对照时应设置独立 `RESULTS_DIR`，避免误覆盖当前 20 场景主线。
