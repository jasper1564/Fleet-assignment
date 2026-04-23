from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
RUN_DIR = Path(os.getenv("QUESTION4_RUN_DIR", BASE_DIR / "results" / "runs" / "model_current"))
_default_baseline_dir = BASE_DIR / "results" / "runs" / "model_current_5scenario_archive_2026-04-23"
if not _default_baseline_dir.exists():
    _default_baseline_dir = BASE_DIR / "results" / "runs" / "model_current"
BASELINE_RUN_DIR = Path(os.getenv("QUESTION4_BASELINE_RUN_DIR", _default_baseline_dir))
OUTPUT_DIR = Path(os.getenv("QUESTION4_ANALYSIS_DIR", BASE_DIR / "results" / "analysis" / "question4_current"))

if not RUN_DIR.is_absolute():
    RUN_DIR = BASE_DIR / RUN_DIR
if not BASELINE_RUN_DIR.is_absolute():
    BASELINE_RUN_DIR = BASE_DIR / BASELINE_RUN_DIR
if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = BASE_DIR / OUTPUT_DIR

TABLE_DIR = OUTPUT_DIR / "tables"


def fmt_num(value: float | int | str, digits: int = 2) -> str:
    return f"{float(value):,.{digits}f}"


def fmt_int(value: float | int | str) -> str:
    return f"{int(round(float(value))):,}"


def fmt_pct(value: float | int | str, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}%"


def md_table(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    view = df.loc[:, columns].copy()
    if max_rows is not None:
        view = view.head(max_rows)
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for _, row in view.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                values.append(f"{value:,.2f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *rows])


def read_results(run_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "scenario": pd.read_csv(run_dir / "scenario_summary.csv"),
        "fleet": pd.read_csv(run_dir / "fleet_summary.csv"),
        "task": pd.read_csv(run_dir / "task_summary.csv"),
        "task_adjustments": pd.read_csv(run_dir / "task_adjustment_candidates.csv"),
        "leg_adjustments": pd.read_csv(run_dir / "leg_adjustment_candidates.csv"),
        "products": pd.read_csv(run_dir / "product_assignment_analysis.csv"),
    }


def task_line(row: pd.Series) -> str:
    return (
        f"- `{row['Task']}` `{row['Origin']} -> {row['Destination']}`，"
        f"机型 `{row['Assigned_Fleet']}`，载客率 `{float(row['Expected_Load(%)']):.2f}%`，"
        f"利润 `{float(row['Profit']):,.2f}`"
    )


def review_line(row: pd.Series) -> str:
    return (
        f"- `{row['Task']}` `{row['Origin']} -> {row['Destination']}`，"
        f"载客率 `{float(row['Expected_Load(%)']):.2f}%`，利润 `{float(row['Profit']):,.2f}`"
    )


def leg_line(row: pd.Series) -> str:
    return (
        f"- `{row['Leg']}`，机型 `{row['Assigned_Fleet']}`，"
        f"载客率 `{float(row['Load_Factor(%)']):.2f}%`，"
        f"瓶颈频率 `{float(row['Bottleneck_Freq(%)']):.2f}%`，"
        f"影子价格 `{float(row['Shadow_Price']):.4f}`，"
        f"价值分 `{float(row['Value_Score']):,.2f}`"
    )


def unmet_leg_line(row: pd.Series) -> str:
    return f"- `{row['Bottleneck_Leg']}`：未满足需求 `{float(row['Unmet']):,.2f}`"


def build_outputs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    current = read_results(RUN_DIR)
    baseline = read_results(BASELINE_RUN_DIR)

    scenario = current["scenario"].iloc[0]
    baseline_scenario = baseline["scenario"].iloc[0]
    fleet = current["fleet"]
    baseline_fleet = baseline["fleet"]
    task = current["task"]
    baseline_task = baseline["task"]
    task_adjustments = current["task_adjustments"]
    leg_adjustments = current["leg_adjustments"]
    products = current["products"]

    comparison_rows = []
    for label, column in [
        ("总收入", "Total_Revenue"),
        ("总成本", "Total_Cost"),
        ("总利润", "Total_Profit"),
        ("总未满足需求", "Total_Unmet_Demand"),
        ("平均载客率", "Average_Load_Factor(%)"),
        ("加权载客率", "Weighted_Load_Factor(%)"),
        ("高影子价格航段数", "High_Shadow_Price_Leg_Count"),
    ]:
        baseline_value = float(baseline_scenario[column])
        current_value = float(scenario[column])
        comparison_rows.append(
            {
                "指标": label,
                "5场景结果": baseline_value,
                "20场景结果": current_value,
                "变化": current_value - baseline_value,
            }
        )
    scenario_comparison = pd.DataFrame(comparison_rows)
    scenario_comparison[["5场景结果", "20场景结果", "变化"]] = scenario_comparison[
        ["5场景结果", "20场景结果", "变化"]
    ].round(2)
    scenario_comparison.to_csv(TABLE_DIR / "scenario_comparison.csv", index=False, encoding="utf-8-sig")

    fleet_comparison = baseline_fleet[
        ["Fleet", "Used_Aircraft", "Assigned_Task_Count", "Weighted_Load(%)", "Attributed_Profit", "Utilization_Tag"]
    ].merge(
        fleet[
            [
                "Fleet",
                "Used_Aircraft",
                "Assigned_Task_Count",
                "Weighted_Load(%)",
                "Attributed_Profit",
                "Utilization_Tag",
            ]
        ],
        on="Fleet",
        suffixes=("_5sc", "_20sc"),
    )
    fleet_comparison["Used_Aircraft_Delta"] = (
        fleet_comparison["Used_Aircraft_20sc"] - fleet_comparison["Used_Aircraft_5sc"]
    )
    fleet_comparison["Assigned_Task_Delta"] = (
        fleet_comparison["Assigned_Task_Count_20sc"] - fleet_comparison["Assigned_Task_Count_5sc"]
    )
    fleet_comparison["Profit_Delta"] = (
        fleet_comparison["Attributed_Profit_20sc"] - fleet_comparison["Attributed_Profit_5sc"]
    )
    numeric_comparison_cols = fleet_comparison.select_dtypes(include="number").columns
    fleet_comparison[numeric_comparison_cols] = fleet_comparison[numeric_comparison_cols].round(2)
    fleet_comparison.to_csv(TABLE_DIR / "fleet_usage_comparison.csv", index=False, encoding="utf-8-sig")

    baseline_assign = baseline_task[
        ["Task", "Origin", "Destination", "Assigned_Fleet", "Expected_Load(%)", "Profit"]
    ].rename(
        columns={
            "Assigned_Fleet": "Assigned_Fleet_5sc",
            "Expected_Load(%)": "Expected_Load_5sc",
            "Profit": "Profit_5sc",
        }
    )
    current_assign = task[["Task", "Assigned_Fleet", "Expected_Load(%)", "Profit"]].rename(
        columns={
            "Assigned_Fleet": "Assigned_Fleet_20sc",
            "Expected_Load(%)": "Expected_Load_20sc",
            "Profit": "Profit_20sc",
        }
    )
    task_changes = baseline_assign.merge(current_assign, on="Task")
    task_changes = task_changes[task_changes["Assigned_Fleet_5sc"] != task_changes["Assigned_Fleet_20sc"]].copy()
    task_changes["Transition"] = task_changes["Assigned_Fleet_5sc"] + " -> " + task_changes["Assigned_Fleet_20sc"]
    task_changes.to_csv(TABLE_DIR / "task_fleet_changes.csv", index=False, encoding="utf-8-sig")
    transition_counts = task_changes["Transition"].value_counts().rename_axis("Transition").reset_index(name="Task_Count")
    transition_counts.to_csv(TABLE_DIR / "task_fleet_transition_counts.csv", index=False, encoding="utf-8-sig")

    tags = sorted(set(task_adjustments["Recommendation_Tag"]) | set(leg_adjustments["Recommendation_Tag"]))
    recommendation_counts = pd.DataFrame({"Recommendation_Tag": tags})
    recommendation_counts["Task_Count"] = (
        recommendation_counts["Recommendation_Tag"].map(task_adjustments["Recommendation_Tag"].value_counts()).fillna(0).astype(int)
    )
    recommendation_counts["Leg_Count"] = (
        recommendation_counts["Recommendation_Tag"].map(leg_adjustments["Recommendation_Tag"].value_counts()).fillna(0).astype(int)
    )
    recommendation_counts.to_csv(TABLE_DIR / "recommendation_counts.csv", index=False, encoding="utf-8-sig")

    top_up = task_adjustments[task_adjustments["Recommendation_Tag"] == "Upgauge_or_AddCapacity"].sort_values(
        "Profit", ascending=False
    )
    review = task_adjustments[task_adjustments["Recommendation_Tag"] == "Review_Schedule"].sort_values("Profit")
    downgrade = task_adjustments[task_adjustments["Recommendation_Tag"] == "Downgauge"].sort_values("Expected_Load(%)")
    top_legs = leg_adjustments.sort_values("Value_Score", ascending=False)
    top_unmet_legs = products.groupby("Bottleneck_Leg", as_index=False)["Unmet"].sum().sort_values(
        "Unmet", ascending=False
    )
    top_unmet_products = products.sort_values("Unmet", ascending=False)

    top_up.head(10).to_csv(TABLE_DIR / "top_upgauge_tasks.csv", index=False, encoding="utf-8-sig")
    review.to_csv(TABLE_DIR / "review_schedule_tasks.csv", index=False, encoding="utf-8-sig")
    downgrade.head(15).to_csv(TABLE_DIR / "top_downgauge_tasks.csv", index=False, encoding="utf-8-sig")
    top_legs.head(15).to_csv(TABLE_DIR / "top_bottleneck_legs.csv", index=False, encoding="utf-8-sig")
    top_unmet_legs.head(15).to_csv(TABLE_DIR / "top_unmet_legs.csv", index=False, encoding="utf-8-sig")
    top_unmet_products.head(15).to_csv(TABLE_DIR / "top_unmet_products.csv", index=False, encoding="utf-8-sig")

    available_aircraft = fleet["Available_Aircraft"].sum()
    used_aircraft = fleet["Used_Aircraft"].sum()
    used_rate = used_aircraft / available_aircraft * 100
    used_fleet_count = int((fleet["Used_Aircraft"] > 0).sum())
    unused_fleet_count = int((fleet["Used_Aircraft"] <= 0).sum())
    unused_available = fleet.loc[fleet["Used_Aircraft"] <= 0, "Available_Aircraft"].sum()

    core_names = ["F16C0Y165", "F0C0Y76"]
    core = fleet[fleet["Fleet"].isin(core_names)].copy()
    core_profit = core["Attributed_Profit"].sum()
    attributed_profit_sum = fleet["Attributed_Profit"].sum()
    core_attr_share = core_profit / attributed_profit_sum * 100 if attributed_profit_sum else 0
    core_total_profit_share = core_profit / float(scenario["Total_Profit"]) * 100
    core_shadow = core["Positive_Shadow_Leg_Count"].sum()
    shadow_total = fleet["Positive_Shadow_Leg_Count"].sum()
    core_shadow_share = core_shadow / shadow_total * 100 if shadow_total else 0

    secondary = fleet[fleet["Fleet"].isin(["F12C12Y48", "F0C0Y72"])][
        [
            "Fleet",
            "Available_Aircraft",
            "Used_Aircraft",
            "Utilization_Rate(%)",
            "Assigned_Task_Count",
            "Weighted_Load(%)",
            "Attributed_Profit",
            "Positive_Shadow_Leg_Count",
        ]
    ]
    underused = fleet[fleet["Used_Aircraft"] <= 0][
        ["Fleet", "Available_Aircraft", "Used_Aircraft", "Assigned_Task_Count", "Attributed_Profit", "Utilization_Tag"]
    ]
    core_display = core[
        [
            "Fleet",
            "Available_Aircraft",
            "Used_Aircraft",
            "Utilization_Rate(%)",
            "Assigned_Task_Count",
            "Weighted_Load(%)",
            "Attributed_Profit",
            "Positive_Shadow_Leg_Count",
        ]
    ]

    def tag_count(df: pd.DataFrame, tag: str) -> int:
        return int((df["Recommendation_Tag"] == tag).sum())

    task_up = tag_count(task_adjustments, "Upgauge_or_AddCapacity")
    task_down = tag_count(task_adjustments, "Downgauge")
    task_review = tag_count(task_adjustments, "Review_Schedule")
    leg_up = tag_count(leg_adjustments, "Upgauge_or_AddCapacity")
    leg_down = tag_count(leg_adjustments, "Downgauge")
    leg_review = tag_count(leg_adjustments, "Review_Schedule")

    up_lines = "\n".join(task_line(row) for _, row in top_up.head(6).iterrows())
    down_lines = "\n".join(review_line(row) for _, row in downgrade.head(6).iterrows())
    review_lines = "\n".join(review_line(row) for _, row in review.iterrows())
    leg_lines = "\n".join(leg_line(row) for _, row in top_legs.head(8).iterrows())
    unmet_leg_lines = "\n".join(unmet_leg_line(row) for _, row in top_unmet_legs.head(8).iterrows())
    transition_lines = "\n".join(
        f"- `{row['Transition']}`：`{int(row['Task_Count'])}` 个任务"
        for _, row in transition_counts.head(8).iterrows()
    )

    profit_delta = float(scenario["Total_Profit"]) - float(baseline_scenario["Total_Profit"])
    unmet_delta = float(baseline_scenario["Total_Unmet_Demand"]) - float(scenario["Total_Unmet_Demand"])

    report = f"""# 第四问结果分析：20 场景 Monte Carlo 主线

最后更新：2026-04-23

本文基于当前正式 20 场景 Monte Carlo 结果目录 `results/runs/model_current`，按照现有第四问的分析思路，对“各机型使用情况以及是否需要进一步调整机队或航班计划”进行复核。原 5 场景结果仅作为归档对照，保存在 `results/runs/model_current_5scenario_archive_2026-04-23`。

## 一、结论先行

20 场景结果作为当前正式主线，强化了“结构性调整优先”的结论。当前网络不是所有飞机都不够，而是少数主力机型继续偏紧，同时部分机型完全闲置；航班计划层面仍然存在大量高价值瓶颈航段，需要定向增容、换大机型或释放主力机型资源。

与原 5 场景归档结果相比，20 场景下机型分配发生了小幅重排：`{len(task)}` 个任务中有 `{len(task_changes)}` 个任务更换机型，占比约 `{len(task_changes) / len(task) * 100:.2f}%`。但主力结构仍然稳定，核心仍是 `F16C0Y165` 与 `F0C0Y76`。

## 二、总体方案画像

根据 `scenario_summary.csv`，20 场景结果为：

- 场景数：`{int(scenario['Scenario_Count'])}`
- 需求波动系数：`{float(scenario['Demand_CV']):.2f}`
- 需求分布：`{scenario['Demand_Distribution']}`
- 总收入：`{fmt_num(scenario['Total_Revenue'])}`
- 总成本：`{fmt_num(scenario['Total_Cost'])}`
- 总利润：`{fmt_num(scenario['Total_Profit'])}`
- 总未满足需求：`{fmt_num(scenario['Total_Unmet_Demand'])}`
- 平均载客率：`{fmt_pct(scenario['Average_Load_Factor(%)'])}`
- 加权载客率：`{fmt_pct(scenario['Weighted_Load_Factor(%)'])}`
- 高影子价格航段数：`{fmt_int(scenario['High_Shadow_Price_Leg_Count'])}`

相对原 5 场景归档结果，20 场景总利润变化 `{fmt_num(profit_delta)}`，约占 5 场景利润的 `{profit_delta / float(baseline_scenario['Total_Profit']) * 100:.2f}%`；总未满足需求减少 `{fmt_num(unmet_delta)}`；加权载客率几乎不变。这说明增加场景数后，结果存在边际调整，但总体经营画像稳定。

## 三、机型使用情况

20 场景下，总可用飞机 `{fmt_int(available_aircraft)}` 架，实际使用 `{fmt_int(used_aircraft)}` 架，整体使用占比 `{used_rate:.2f}%`。有实际使用的机型 `{used_fleet_count}` 类，完全未使用的机型 `{unused_fleet_count}` 类；完全未使用机型对应可用飞机 `{fmt_int(unused_available)}` 架。

### 1. 核心主力机型

`F16C0Y165` 与 `F0C0Y76` 仍是当前网络的绝对主力。两者合计归因利润 `{fmt_num(core_profit)}`，占机型归因利润口径的 `{core_attr_share:.2f}%`，占总方案利润的 `{core_total_profit_share:.2f}%`。两者还承载了 `{fmt_int(core_shadow)}` 个正影子价格航段，占机型汇总正影子价格航段的 `{core_shadow_share:.2f}%`。

{md_table(core_display, ['Fleet', 'Available_Aircraft', 'Used_Aircraft', 'Utilization_Rate(%)', 'Assigned_Task_Count', 'Weighted_Load(%)', 'Attributed_Profit', 'Positive_Shadow_Leg_Count'])}

管理含义是：如果要补运力，优先级仍应集中在 `F16C0Y165` 与 `F0C0Y76`，而不是平均扩充全部机型。

### 2. 补充性机型

`F12C12Y48` 与 `F0C0Y72` 继续承担补充运力。它们也有较高使用率，但利润贡献和瓶颈承载能力明显弱于两类核心主力。

{md_table(secondary, ['Fleet', 'Available_Aircraft', 'Used_Aircraft', 'Utilization_Rate(%)', 'Assigned_Task_Count', 'Weighted_Load(%)', 'Attributed_Profit', 'Positive_Shadow_Leg_Count'])}

### 3. 闲置机型

20 场景结果中，以下机型完全未使用：

{md_table(underused, ['Fleet', 'Available_Aircraft', 'Used_Aircraft', 'Assigned_Task_Count', 'Attributed_Profit', 'Utilization_Tag'])}

其中 `F12C0Y112` 在 5 场景结果中还使用 1 架、承担 2 个任务，但在 20 场景结果中降为 0 使用。这说明它属于边际适配机型，场景数增加后被更高性价比或更高适配性的机型替代。

## 四、机型分配变化

20 场景相比 5 场景共有 `{len(task_changes)}` 个任务更换机型。主要迁移方向如下：

{transition_lines}

这类变化不是整体方案重构，而是边际航班的重新平衡。尤其是 `F0C0Y76` 的任务数从 `342` 增至 `349`，`F16C0Y165` 的使用飞机数从 `44` 降至 `42`，说明 20 场景下模型更倾向于把部分中等容量任务交给 `F0C0Y76`，同时减少少数大机型占用。

完整任务变化清单见 `tables/task_fleet_changes.csv`。

## 五、航班计划调整信号

20 场景下，调整信号仍以“增容或换大机型”为主：

- 任务层面：`{task_up}` 个任务建议 `Upgauge_or_AddCapacity`，`{task_down}` 个任务建议 `Downgauge`，`{task_review}` 个任务建议 `Review_Schedule`
- 航段层面：`{leg_up}` 个航段建议 `Upgauge_or_AddCapacity`，`{leg_down}` 个航段建议 `Downgauge`，`{leg_review}` 个航段建议 `Review_Schedule`

### 1. 优先增容任务

以下任务同时具备高利润和高容量压力，适合优先考虑换大机型、补班或释放主力运力：

{up_lines}

### 2. 高价值瓶颈航段

以下航段在价值分、影子价格、瓶颈频率上表现突出，是后续航班计划调整的重点：

{leg_lines}

### 3. 可考虑降级的任务

以下任务载客率较低，更适合考虑换小机型或释放主力资源，而不是继续占用更高价值运力：

{down_lines}

### 4. 应进入班次复核的任务

以下任务被标记为 `Review_Schedule`，通常是低载客率且利润较弱或亏损的对象：

{review_lines}

这类任务不一定要立刻取消，但应结合网络连接价值、时刻价值和服务约束进一步复核。

## 六、未满足需求集中位置

未满足需求仍不是均匀分布，而是集中在少数瓶颈航段。按 `Bottleneck_Leg` 聚合后，未满足需求最高的航段为：

{unmet_leg_lines}

这支持一个重要管理判断：后续调整不应平均加容量，而应围绕这些瓶颈航段定向增容。

## 七、图表说明

本次 20 场景分析对应的 5 张图输出在 `figures/` 目录：

- `figures/question4_fleet_portrait.png`：机队使用画像
- `figures/question4_adjustment_actions.png`：调整建议总览
- `figures/question4_bottleneck_legs.png`：瓶颈航段识别
- `figures/question4_unmet_demand.png`：未满足需求集中位置
- `figures/question4_fleet_cost_effectiveness.png`：机型使用与性价比

## 八、最终回答口径

基于 20 场景结果，第四问可以表述为：当前并购后机队使用明显分化，`F16C0Y165` 与 `F0C0Y76` 仍是核心主力机型，承担大部分利润和瓶颈航段；多类机型完全闲置，说明问题不是总机队规模不足，而是机型结构与网络需求之间存在错配。因此需要进一步调整机队与航班计划，但调整重点应是结构优化、主力机型释放和关键瓶颈航段定向增容，而不是简单扩大总机队规模。
"""

    figure_notes = """# 第四问图示说明：20 场景 Monte Carlo 主线

最后更新：2026-04-23

本说明对应 `results/analysis/question4_mc20_2026-04-23/figures` 下的 5 张图。图形逻辑沿用原第四问分析，输入结果为当前正式 20 场景 Monte Carlo 主线。

## 1. 机队使用画像

![机队使用画像](figures/question4_fleet_portrait.png)

这张图展示各机型利润贡献、利用率、加权载客率和瓶颈承载情况。20 场景下，`F16C0Y165` 与 `F0C0Y76` 仍位于高利用率、高载运压力、高瓶颈承载区域，是网络核心主力机型。

## 2. 调整建议总览

![调整建议总览](figures/question4_adjustment_actions.png)

这张图汇总任务和航段层面的增容、降级、复核信号。20 场景下，增容或换大机型仍是最主要信号，说明当前最需要的是定向补容量，而不是全局重排。

## 3. 瓶颈航段识别

![瓶颈航段识别](figures/question4_bottleneck_legs.png)

这张图从影子价格和收入贡献两个维度识别关键航段。右上区域的航段既赚钱又稀缺，最适合作为后续增容或换大机型的候选对象。

## 4. 未满足需求集中位置

![未满足需求集中位置](figures/question4_unmet_demand.png)

这张图说明未满足需求主要集中在少数瓶颈航段，而不是均匀分布在全网络。该图支撑“围绕瓶颈点定向调整”的建议。

## 5. 机型使用与性价比

![机型使用与性价比](figures/question4_fleet_cost_effectiveness.png)

这张图解释为什么部分机型会 0 使用。20 场景下，完全闲置机型仍集中在较低性价比或低适配区域，因此闲置更像是成本效率筛选结果，而不是求解异常。

## 6. 合并结论

五张图共同支持的结论是：20 场景结果下，第四问仍应围绕“主力机型紧张、闲置机型不宜盲目扩充、关键瓶颈航段定向增容、低载客率任务降级或复核”展开。
"""

    comparison = f"""# 5 场景归档与 20 场景主线对照

最后更新：2026-04-23

本文件用于说明当前 20 场景主线相对原 5 场景归档结果的变化。

## 一、总体指标变化

{md_table(scenario_comparison, ['指标', '5场景结果', '20场景结果', '变化'])}

## 二、机型使用变化

{md_table(fleet_comparison[['Fleet', 'Used_Aircraft_5sc', 'Used_Aircraft_20sc', 'Used_Aircraft_Delta', 'Assigned_Task_Count_5sc', 'Assigned_Task_Count_20sc', 'Assigned_Task_Delta', 'Profit_Delta']], ['Fleet', 'Used_Aircraft_5sc', 'Used_Aircraft_20sc', 'Used_Aircraft_Delta', 'Assigned_Task_Count_5sc', 'Assigned_Task_Count_20sc', 'Assigned_Task_Delta', 'Profit_Delta'])}

## 三、任务分配变化

20 场景相对原 5 场景共有 `{len(task_changes)}` 个任务更换机型，占全部 `{len(task)}` 个任务的 `{len(task_changes) / len(task) * 100:.2f}%`。

{transition_lines}

完整清单见 `tables/task_fleet_changes.csv`。

## 四、解释

20 场景结果说明方案存在少量边际调整，但核心判断没有改变。主力机型仍集中在 `F16C0Y165` 与 `F0C0Y76`，大量闲置机型仍未进入最优方案，高价值瓶颈航段仍需要定向增容。因此，当前正式主线采用 20 场景，同时将原 5 场景保留为归档对照。
"""

    (OUTPUT_DIR / "question4_analysis.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "figure_notes.md").write_text(figure_notes, encoding="utf-8")
    (OUTPUT_DIR / "comparison_with_5_scenarios.md").write_text(comparison, encoding="utf-8")


if __name__ == "__main__":
    build_outputs()
    print(f"Saved question 4 report to: {OUTPUT_DIR}")
