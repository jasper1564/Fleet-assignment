# `fleet_assignment_main.py`

## 为什么存在

这是当前最接近“主开发入口”的机型分配模型文件。

## 它依赖什么

### 需求输入

- `data/model_input/demand/product_info_rf_predicted.json`

### 网络输入

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 机队参考

- `data/raw/reference/fleet_family_master.csv`

## 它大致在做什么

1. 读取产品需求、票价、航班任务和机场事件网络。
2. 读取机队规模、座位数和飞行成本。
3. 生成 Monte Carlo 需求场景。
4. 建立机型分配优化模型。
5. 输出收益、销量、负载率、地面停放和摘要表。

## 结果目录

- `results/runs/model_current/`

## 为什么它重要

- 这是当前最适合继续演进成“最终答题模型”的文件。
- 它直接连接题目第 3 问和第 4 问。
- 也会反过来影响题目第 1 问和第 2 问最终怎么落到报告里。

## 当前真实状态

- 这条线使用的是基于第 2 问影响因素分析得到的 `RF` 需求还原结果。
- 因为题目要求通过第二问来还原需求，所以这条线应被视为正式答题主线。
- 文件里已经尝试加入 `Monte Carlo` 需求波动模拟。
- 但当前运行状态是：`Monte Carlo` 会导致 `out of memory`，所以“波动模拟”还不是稳定可用能力。

## 开发热点

- 需求场景生成参数
- 任务与航段映射逻辑
- 目标函数与输出摘要
- 机队成本、座位和收益连接方式

## 主要风险

- 改需求输入文件，相当于同时改了实验口径。
- 改网络 JSON 假设，相当于改了任务图结构。
- 当前 Monte Carlo 会 OOM，不能默认这部分已经可用于最终结果。
- 结果目录里已有历史文件，不应直接当作当前代码唯一真相。
