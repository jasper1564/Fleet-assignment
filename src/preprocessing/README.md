# Preprocessing Module

这个目录目前只有一个关键脚本，但它承担了从原始表到后续需求建模中间表的入口作用。

单文件说明见：[`build_processed_inputs.md`](build_processed_inputs.md)

## 文件说明

| 文件 | 作用 | 主要输入 | 主要输出 |
| --- | --- | --- | --- |
| [`build_processed_inputs.py`](build_processed_inputs.py) | 处理航班时刻、累计产品需求、产品-航段映射与经停航班打包信息 | `data/raw/schedule/flight_schedule.csv`, `data/raw/booking/itinerary_sales_by_rd.csv` | `data/interim/network/processed_schedule.csv`, `data/interim/products/products_with_total_demand.csv`, `data/interim/network/product_leg_mapping.csv` |

## 这个脚本实际做了什么

- 把当地时刻转成 UTC 分钟，并计算飞行时长与是否跨夜。
- 对产品销售表中的 `RD*` 列求和，得到 `Total_Demand`。
- 为产品生成 `ProductID`。
- 从 `Flight1/2/3` 中抽取航段编号，生成产品到航段的长表映射。
- 对经停航班生成 `Super_Flight_ID` 概念。

## 下游依赖

- `products_with_total_demand.csv` 会被需求修正与需求还原分支使用。
- 这里输出的中间表属于“需求处理链路”的基础资产。

## 当前要注意的点

- 这个脚本并不会直接重建 `data/model_input/network/` 下的三个 JSON。
- 也就是说，当前预处理链路和当前网络 JSON 资产之间不是完全打通的。
- 如果有人打算做真正端到端重建，通常要先补齐这一段。
