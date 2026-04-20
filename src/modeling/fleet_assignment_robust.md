# `fleet_assignment_robust.py`

## 为什么存在

这个文件承担的是“替代需求口径下的机型分配比较”角色，当前更适合被看成稳健性或敏感性分析模型。

## 它依赖什么

### 需求输入

- `data/model_input/demand/product_info_em_restored.json`

### 网络输入

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 机队参考

- `data/raw/reference/fleet_family_master.csv`

## 它和主模型最大的区别

- 需求口径不同：这里用的是 EM 恢复需求。
- EM 结果本身较稳健，而且结果与影子价格可以顺利跑出。
- 但这条线不符合题目“通过第二问影响因素分析来还原需求”的要求。
- 结果更适合做对照与稳健性解释。
- 当前输出结构比主模型更紧凑。

## 结果目录

- `results/runs/robustness/`

## 什么时候优先看它

- 想回答“如果采用恢复后的潜在需求，机型分配会怎样变化”时。
- 想给最终报告增加稳健性比较时。

## 开发时要注意

- 不要把它默认当成主模型的简单副本。
- 当前更合理的定位是“对照/稳健性补充”，不是默认正式答题主线。
