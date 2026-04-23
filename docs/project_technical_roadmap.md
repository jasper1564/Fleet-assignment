# 项目技术路线图

最后更新：2026-04-23

这份文档用于把当前仓库已经完成的整套方法串成一条清晰的技术路线，方便写报告、做答辩或向别人解释“这个项目到底是怎么一步步做完的”。

## 一页版概括

整套项目的正式技术路线可以概括为：

> 先基于原始历史销售数据回答并购前后收益变化；再利用 `RD` 结构识别截断并用 `Random Forest` 恢复产品需求；随后将恢复后的需求、网络输入和机队参考信息一起送入机型分配主模型；最后基于优化结果分析机队使用结构、识别瓶颈资源，并提出调整建议。

这条路线同时满足了题目四个问题，但四个问题并不是完全并列、彼此独立的四段工作，而是形成了“历史分析 + 需求恢复 + 运力优化 + 管理解释”的前后衔接链条。

## 总体分层

### 1. 题目目标层

题目要求回答四个问题：

1. 并购前后收益比较
2. 旅客行程选择行为与需求影响因素分析
3. 并购后机型分配优化
4. 机队使用情况分析与调整建议

这四个问题决定了整个项目不能只做一个优化模型，也不能只做一个统计分析，而必须形成从数据、需求、优化到解释的完整链路。

### 2. 原始数据层

项目当前主线使用的核心原始数据包括：

- `data/raw/schedule/flight_schedule.csv`
- `data/raw/booking/itinerary_sales_by_rd.csv`
- `data/raw/reference/fleet_family_master.csv`
- `data/raw/reference/market_share_by_od.csv`

它们分别提供航班计划、产品销售曲线、机队参考参数和市场参考信息，是后续所有分析与建模的共同基础。

### 3. 共享预处理层

这一层的目标不是直接回答题目，而是把后续多个问题都要用到的基础输入整理出来。当前主线对应：

- [`src/preprocessing/build_processed_inputs.py`](../src/preprocessing/build_processed_inputs.py)
- [`src/preprocessing/build_processed_inputs.md`](../src/preprocessing/build_processed_inputs.md)

这一层完成的事情主要包括：

- 统一航班、航段、任务和机场时间线结构
- 构建网络输入 `JSON`
- 整理后续优化模型共用的基础输入
- 保持历史销售口径与优化输入口径分离，避免题目一与题目三混口径

这一层的关键输出包括：

- `data/model_input/network/super_flight_schedule.json`
- `data/model_input/network/airport_timeline.json`
- `data/model_input/network/leg_to_products.json`

### 4. 问题一的历史收益分析支线

问题一并不依赖优化模型，而是直接基于历史销售数据回答“并购前后收益如何变化”。当前正式口径是：

- 主口径：原始历史销量
- 对照口径：`RF` 恢复后的需求版本

对应脚本与文档为：

- [`src/analysis/analyze_question1_revenue.py`](../src/analysis/analyze_question1_revenue.py)
- [`docs/question1_answer.md`](question1_answer.md)

这一支线的作用是：

- 回答历史收益变化，而不是回答优化后的利润变化
- 拆解新增收益的来源
- 说明网络扩张与联程协同的贡献

所以在技术路线上，问题一是“独立分析支线”，而不是通往机型优化的前置步骤。

### 5. 问题二的需求恢复主线

问题二是整套项目的建模转折点。项目最终没有停留在“解释近期购票占比”，而是升级成了“截断识别 + 行为建模 + 需求恢复 + 总需求解释”的两阶段 `Random Forest` 框架。

当前主线对应：

- [`src/demand_estimation/passenger_choice_random_forest.py`](../src/demand_estimation/passenger_choice_random_forest.py)
- [`src/demand_estimation/passenger_choice_random_forest.md`](../src/demand_estimation/passenger_choice_random_forest.md)

核心逻辑是：

1. 先基于 `RD30 ... RD1` 的结构规则识别产品是否可能被截断
2. 仅用未截断样本训练 `near_ratio` 行为模型
3. 对被截断产品恢复 `corrected_demand`
4. 形成最终用于建模的 `final_demand`
5. 再基于 `final_demand` 回答“哪些特征影响总需求”

这一层最关键的工程结果，是把需求恢复结果同步到正式模型输入：

- `data/model_input/demand/product_info_rf_predicted.json`

这意味着问题二不再只是解释性分析，而是直接成为问题三的需求输入层。

### 6. 问题三的机型分配优化主线

问题三使用的是当前正式主模型：

- [`src/modeling/fleet_assignment_main.py`](../src/modeling/fleet_assignment_main.py)
- [`src/modeling/fleet_assignment_main.md`](../src/modeling/fleet_assignment_main.md)

这一层将三类信息合并起来：

- 来自问题二的恢复后需求
- 来自预处理层的网络结构输入
- 来自参考表的机队参数

然后求解并购后的机型分配方案，并输出：

- 收入
- 成本
- 利润
- 未满足需求
- 装载率
- 影子价格
- 机型使用汇总
- 调整候选表

当前正式结果目录为：

- [`results/runs/model_current`](../results/runs/model_current)（20 场景）

20 场景原始运行和 5 场景归档目录为：

- [`results/runs/model_mc20_2026-04-23`](../results/runs/model_mc20_2026-04-23)
- [`results/runs/model_current_5scenario_archive_2026-04-23`](../results/runs/model_current_5scenario_archive_2026-04-23)
- [`docs/monte_carlo_20_scenario_handoff.md`](monte_carlo_20_scenario_handoff.md)

当前 `model_current` 已经采用 20 场景结果作为正式主线。

因此，技术路线上最关键的“主干”其实是：

`共享预处理 -> RF 需求恢复 -> fleet_assignment_main.py`

### 7. 问题四的结果解释层

问题四最终没有再单独建一个新的优化模型，而是转化成对问题三结果的结构化解释模块。当前对应：

- [`docs/question4_answer.md`](question4_answer.md)
- [`docs/question4_current_analysis.md`](question4_current_analysis.md)
- [`docs/question4_figure_notes.md`](question4_figure_notes.md)
- [`docs/question4_additional_findings.md`](question4_additional_findings.md)
- [`src/analysis/plot_question4_results.py`](../src/analysis/plot_question4_results.py)
- 20 场景分析包：[`results/analysis/question4_mc20_2026-04-23`](../results/analysis/question4_mc20_2026-04-23)

这一层重点回答的是：

- 哪些机型是真正的主力资源
- 哪些航段是瓶颈航段
- 未满足需求集中在什么位置
- 为什么会出现部分机型 `0` 使用
- 后续应该优先增容、降级还是复核班次

因此，问题四在技术路线上属于“优化结果解释层”，而不是“第二个优化层”。

## 正式主线与对照支线

### 当前正式主线

- 问题一：原始历史销量口径回答并购前后收益变化
- 问题二：`Random Forest` 两阶段需求恢复
- 问题三：`fleet_assignment_main.py`
- 问题四：基于问题三结果的管理解释与调整建议

### 当前对照/扩展线

- 问题一中的 `RF` 收入口径：仅作为对照
- 问题二中的 `EM` 需求恢复：保留为统计对照，不作为正式主线
- 问题三中的 `robust` 与 `variants`：作为稳健性或历史版本补充
- `Monte Carlo`：正式结果采用 20 场景，原 5 场景作为归档对照；仍不作为当前主要卖点
- “零需求恢复”：保留为未来扩展方向，尚未并入正式主线

## 推荐在报告里怎么讲

如果要把整套路线压缩成一段正式表述，推荐直接这样写：

> 本项目首先基于原始销售数据分析并购前后历史收益变化，随后基于 `RD` 订座曲线结构识别销售截断并利用随机森林恢复产品真实需求，再将恢复后的需求与网络、机队输入共同送入机型分配主模型，求解并购后的最优机型分配方案，最后围绕优化结果分析机队使用结构、识别瓶颈航段并提出调整建议。

如果要在答辩里更口语化一点，也可以说：

> 我们先回答历史上并购有没有带来收益提升，再解决“销量数据不完整导致需求看不清”的问题，然后用恢复后的需求去做机型分配优化，最后再解释优化结果为什么会这样，并给出机队和航班计划的调整建议。

## 配套路线图

当前已经配套生成了一张可直接用于汇报或文档排版的技术路线图：

- 图片：[`results/figures/project/project_technical_roadmap.png`](../results/figures/project/project_technical_roadmap.png)
- 矢量版：[`results/figures/project/project_technical_roadmap.svg`](../results/figures/project/project_technical_roadmap.svg)
- 生成脚本：[`src/analysis/plot_project_technical_roadmap.py`](../src/analysis/plot_project_technical_roadmap.py)

如果后续要继续压缩成一页 `PPT`，建议就沿着这张图从左到右讲，不需要再重新发明一套叙述结构。
