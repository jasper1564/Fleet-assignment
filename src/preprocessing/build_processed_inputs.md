# `build_processed_inputs.py`

## 为什么存在

这个脚本是原始航班表和原始产品销售表进入分析链路的第一步。它把后续需求分析会反复使用的一些基础字段先整理出来。

## 它做什么

1. 读取原始航班与产品数据。
2. 把航班起降时间统一转成 UTC 分钟。
3. 计算飞行时长和是否跨夜。
4. 汇总产品的 `RD*` 销售列，生成 `Total_Demand`。
5. 为每个产品生成 `ProductID`。
6. 解析 `Flight1/2/3`，构造产品到航段的映射表。
7. 为经停航班生成 `Super_Flight_ID`。

## 输入

- `data/raw/schedule/flight_schedule.csv`
- `data/raw/booking/itinerary_sales_by_rd.csv`

## 输出

- `data/interim/network/processed_schedule.csv`
- `data/interim/products/products_with_total_demand.csv`
- `data/interim/network/product_leg_mapping.csv`

## 下游谁会用

- `products_with_total_demand.csv` 是需求修正和需求恢复的共同上游。
- 这个脚本是需求链路的基础，但不是当前模型输入 JSON 的完整生成器。

## 开发时要注意

- 航班号提取使用了正则，默认假设航班号格式是“2 个字母 + 数字”。
- 当前脚本没有把 `data/model_input/network/` 三个 JSON 一起重建出来。
- 如果以后要打通端到端流程，这个脚本通常会成为网络输入生成链路的起点。
