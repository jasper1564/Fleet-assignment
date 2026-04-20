# Modeling Variants

这个目录保存的是历史变体和对照版本，不是当前首选开发入口。

## 文件说明

| 文件 | 当前角色 | 需求输入 | 结果目录 |
| --- | --- | --- | --- |
| [`fleet_assignment_v3_1.py`](fleet_assignment_v3_1.py) | 历史 Monte Carlo 版本 | `product_info_rf_predicted.json` | `results/runs/variants/v3_1/` |
| [`fleet_assignment_v3_1_original_restore.py`](fleet_assignment_v3_1_original_restore.py) | 恢复用保留版本 | `product_info_rf_predicted.json` | `results/runs/variants/v3_1_original_restore/` |
| [`fleet_assignment_v3_2.py`](fleet_assignment_v3_2.py) | 较新的历史变体，输出摘要更丰富 | `product_info_rf_predicted.json` | `results/runs/variants/v3_2/` |

## 什么时候看这里

- 想比较不同建模版本的输出差异时。
- 想追溯某个字段或某张结果表最早来自哪个版本时。
- 想把当前主模型中的某些逻辑回滚或借鉴回来时。

## 不建议的做法

- 不要一上来就在这里继续叠加新版本。
- 不要在没确认目标版本前同时修改多个变体。

## 当前建议

默认把这里视为“历史对照区”，而把上一级的 [`../fleet_assignment_main.py`](../fleet_assignment_main.py) 视为主开发入口。
