from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D


BASE_DIR = Path(__file__).resolve().parents[2]
_run_dir_override = os.getenv("QUESTION4_RUN_DIR")
RUN_DIR = Path(_run_dir_override) if _run_dir_override else BASE_DIR / "results" / "runs" / "model_current"
if not RUN_DIR.is_absolute():
    RUN_DIR = BASE_DIR / RUN_DIR
REFERENCE_PATH = BASE_DIR / "data" / "raw" / "reference" / "fleet_family_master.csv"
_output_dir_override = os.getenv("QUESTION4_OUTPUT_DIR")
OUTPUT_DIR = Path(_output_dir_override) if _output_dir_override else BASE_DIR / "results" / "figures" / "question4"
if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = BASE_DIR / OUTPUT_DIR


COLORS = {
    "ink": "#23313B",
    "teal": "#2A7F98",
    "teal_light": "#9FD3C7",
    "gold": "#E9C46A",
    "orange": "#F28C28",
    "red": "#C8553D",
    "olive": "#6A994E",
    "sand": "#FFFFFF",
    "cream": "#FFFFFF",
    "grid": "#D7D4CC",
    "muted": "#7C8A96",
}


def configure_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["sand"],
            "axes.facecolor": COLORS["cream"],
            "axes.edgecolor": COLORS["grid"],
            "axes.labelcolor": COLORS["ink"],
            "axes.titlecolor": COLORS["ink"],
            "xtick.color": COLORS["ink"],
            "ytick.color": COLORS["ink"],
            "text.color": COLORS["ink"],
            "grid.color": COLORS["grid"],
            "grid.linestyle": "--",
            "grid.alpha": 0.45,
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
        }
    )


def load_data() -> dict[str, pd.DataFrame]:
    fleet = pd.read_csv(RUN_DIR / "fleet_summary.csv")
    reference = pd.read_csv(REFERENCE_PATH, encoding="utf-8-sig")
    name_col, seat_col, count_col, cost_col = reference.columns
    reference = reference.rename(
        columns={
            name_col: "Fleet",
            seat_col: "Seats",
            count_col: "Reference_Count",
            cost_col: "Hourly_Cost",
        }
    )
    reference["Cost_Per_Seat_Hour"] = reference["Hourly_Cost"] / reference["Seats"]
    best_cost = float(reference["Cost_Per_Seat_Hour"].min())
    reference["Cost_Effectiveness_Index"] = best_cost / reference["Cost_Per_Seat_Hour"] * 100

    fleet = fleet.merge(
        reference[["Fleet", "Seats", "Hourly_Cost", "Cost_Per_Seat_Hour", "Cost_Effectiveness_Index"]],
        on="Fleet",
        how="left",
    )

    return {
        "scenario": pd.read_csv(RUN_DIR / "scenario_summary.csv"),
        "fleet": fleet,
        "task_adjustments": pd.read_csv(RUN_DIR / "task_adjustment_candidates.csv"),
        "leg_adjustments": pd.read_csv(RUN_DIR / "leg_adjustment_candidates.csv"),
        "products": pd.read_csv(RUN_DIR / "product_assignment_analysis.csv"),
    }


def recommendation_palette() -> dict[str, str]:
    return {
        "Upgauge_or_AddCapacity": COLORS["teal"],
        "Downgauge": COLORS["gold"],
        "Review_Schedule": COLORS["red"],
        "Keep": COLORS["muted"],
    }


def recommendation_label(tag: str) -> str:
    mapping = {
        "Upgauge_or_AddCapacity": "增容或换大机型",
        "Downgauge": "降级机型",
        "Review_Schedule": "复核班次",
        "Keep": "保持现状",
    }
    return mapping.get(tag, tag)


def fleet_palette(utilization_tag: pd.Series) -> list[str]:
    return [
        COLORS["teal"] if tag == "Tight" else COLORS["gold"] if tag == "Balanced" else COLORS["muted"]
        for tag in utilization_tag
    ]


def add_header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.06, 0.95, title, fontsize=22, fontweight="bold", color=COLORS["ink"])
    fig.text(0.06, 0.915, subtitle, fontsize=11.5, color=COLORS["muted"])


def save_figure(fig: plt.Figure, name: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / name, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_fleet_portrait(data: dict[str, pd.DataFrame]) -> None:
    scenario = data["scenario"].iloc[0]
    fleet = data["fleet"].copy().sort_values("Attributed_Profit", ascending=True)
    colors = fleet_palette(fleet["Utilization_Tag"])

    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.05, 1], wspace=0.16)
    ax_profit = fig.add_subplot(gs[0, 0])
    ax_scatter = fig.add_subplot(gs[0, 1])

    profits_m = fleet["Attributed_Profit"] / 1_000_000
    ax_profit.barh(fleet["Fleet"], profits_m, color=colors, edgecolor="none")
    ax_profit.set_title("机型利润贡献", loc="left", fontsize=15, fontweight="bold")
    ax_profit.set_xlabel("归因利润（百万元）")
    ax_profit.set_ylabel("")
    ax_profit.axvline(0, color=COLORS["grid"], linewidth=1)

    for idx, value in enumerate(profits_m):
        ax_profit.text(value + 0.03, idx, f"{value:.2f}", va="center", fontsize=10, color=COLORS["ink"])

    ax_profit.text(
        0.03,
        0.04,
        (
            f"网络总利润：{scenario['Total_Profit'] / 1_000_000:.2f} 百万\n"
            f"加权载客率：{scenario['Weighted_Load_Factor(%)']:.2f}%\n"
            f"高影子价格航段：{int(scenario['High_Shadow_Price_Leg_Count'])}"
        ),
        transform=ax_profit.transAxes,
        fontsize=10.5,
        color=COLORS["ink"],
        bbox={"boxstyle": "round,pad=0.45", "facecolor": COLORS["sand"], "edgecolor": "none"},
    )

    sizes = fleet["Positive_Shadow_Leg_Count"].fillna(0) * 6 + 80
    ax_scatter.scatter(
        fleet["Utilization_Rate(%)"],
        fleet["Weighted_Load(%)"],
        s=sizes,
        c=colors,
        alpha=0.9,
        linewidth=1.2,
        edgecolors=COLORS["cream"],
    )
    ax_scatter.set_title("利用率与载运压力", loc="left", fontsize=15, fontweight="bold")
    ax_scatter.set_xlabel("利用率（%）")
    ax_scatter.set_ylabel("加权载客率（%）")
    ax_scatter.set_xlim(-3, 105)
    ax_scatter.set_ylim(-3, 102)
    ax_scatter.axvline(80, color=COLORS["grid"], linewidth=1.2)
    ax_scatter.axhline(80, color=COLORS["grid"], linewidth=1.2)
    ax_scatter.text(82, 94, "核心且紧张", fontsize=10, color=COLORS["red"])
    ax_scatter.text(8, 10, "明显闲置", fontsize=10, color=COLORS["muted"])

    for _, row in fleet.iterrows():
        ax_scatter.annotate(
            row["Fleet"],
            (row["Utilization_Rate(%)"], row["Weighted_Load(%)"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=10,
        )

    legend_items = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["teal"], markersize=10, label="紧张"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["gold"], markersize=10, label="均衡"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["muted"], markersize=10, label="闲置"),
    ]
    ax_scatter.legend(handles=legend_items, loc="lower right", frameon=False, title="机型状态")

    add_header(
        fig,
        "机队使用画像",
        "当前方案受少数核心机型约束，而不是受总飞机数量约束。",
    )
    save_figure(fig, "question4_fleet_portrait.png")


def plot_adjustment_actions(data: dict[str, pd.DataFrame]) -> None:
    task_adj = data["task_adjustments"].copy()
    leg_adj = data["leg_adjustments"].copy()

    fig = plt.figure(figsize=(16, 9.2))
    gs = fig.add_gridspec(2, 2, left=0.07, right=0.98, top=0.96, bottom=0.08, hspace=0.28, wspace=0.22)
    ax_counts = fig.add_subplot(gs[0, 0])
    ax_up = fig.add_subplot(gs[0, 1])
    ax_review = fig.add_subplot(gs[1, 0])
    ax_down = fig.add_subplot(gs[1, 1])

    tags = ["Upgauge_or_AddCapacity", "Downgauge", "Review_Schedule"]
    task_counts = task_adj["Recommendation_Tag"].value_counts().reindex(tags, fill_value=0)
    leg_counts = leg_adj["Recommendation_Tag"].value_counts().reindex(tags, fill_value=0)
    positions = np.arange(len(tags))
    width = 0.34

    ax_counts.bar(positions - width / 2, task_counts.values, width=width, color=COLORS["teal"], label="任务")
    ax_counts.bar(positions + width / 2, leg_counts.values, width=width, color=COLORS["orange"], label="航段")
    ax_counts.set_xticks(positions)
    ax_counts.set_xticklabels(["增容", "降级", "复核"])
    ax_counts.set_title("调整信号数量", loc="left", fontsize=15, fontweight="bold")
    ax_counts.set_ylabel("数量")
    ax_counts.legend(frameon=False)

    for x, value in zip(positions - width / 2, task_counts.values):
        ax_counts.text(x, value + 8, f"{int(value)}", ha="center", fontsize=10)
    for x, value in zip(positions + width / 2, leg_counts.values):
        ax_counts.text(x, value + 8, f"{int(value)}", ha="center", fontsize=10)

    top_up = (
        task_adj[task_adj["Recommendation_Tag"] == "Upgauge_or_AddCapacity"]
        .sort_values("Profit", ascending=True)
        .tail(10)
        .copy()
    )
    top_up["Route"] = top_up["Origin"] + " -> " + top_up["Destination"]
    ax_up.barh(top_up["Task"] + "  " + top_up["Route"], top_up["Profit"] / 1000, color=COLORS["teal"])
    ax_up.set_title("最值得增容的任务", loc="left", fontsize=15, fontweight="bold")
    ax_up.set_xlabel("利润（千）")

    review = task_adj[task_adj["Recommendation_Tag"] == "Review_Schedule"].sort_values("Profit")
    review["Route"] = review["Origin"] + " -> " + review["Destination"]
    ax_review.barh(review["Task"] + "  " + review["Route"], review["Profit"] / 1000, color=COLORS["red"])
    ax_review.set_title("需要复核班次的任务", loc="left", fontsize=15, fontweight="bold")
    ax_review.set_xlabel("利润（千）")
    ax_review.axvline(0, color=COLORS["grid"], linewidth=1.2)

    down = task_adj[task_adj["Recommendation_Tag"] == "Downgauge"].copy().nlargest(35, "Profit")
    ax_down.scatter(
        down["Expected_Load(%)"],
        down["Profit"] / 1000,
        s=down["Profit"].clip(lower=0) / 20 + 30,
        c=COLORS["gold"],
        edgecolors=COLORS["cream"],
        alpha=0.85,
    )
    ax_down.set_title("可考虑降级机型的任务", loc="left", fontsize=15, fontweight="bold")
    ax_down.set_xlabel("期望载客率（%）")
    ax_down.set_ylabel("利润（千）")
    ax_down.axvline(70, color=COLORS["grid"], linewidth=1.1)

    for _, row in down.nsmallest(8, "Expected_Load(%)").iterrows():
        ax_down.annotate(
            row["Task"],
            (row["Expected_Load(%)"], row["Profit"] / 1000),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=9,
        )

    save_figure(fig, "question4_adjustment_actions.png")


def plot_leg_bottlenecks(data: dict[str, pd.DataFrame]) -> None:
    legs = data["leg_adjustments"].copy()
    palette = recommendation_palette()

    fig, ax = plt.subplots(figsize=(15, 8.4))
    ax.scatter(
        legs["Shadow_Price"],
        legs["Revenue_Contribution"] / 1000,
        s=legs["Product_Count"] * 3 + 25,
        c=legs["Recommendation_Tag"].map(palette).fillna(COLORS["muted"]),
        alpha=0.78,
        edgecolors=COLORS["cream"],
        linewidth=0.9,
    )
    ax.set_title("航段价值与稀缺性", loc="left", fontsize=16, fontweight="bold")
    ax.set_xlabel("影子价格")
    ax.set_ylabel("收入贡献（千）")
    ax.axvline(0, color=COLORS["grid"], linewidth=1.2)
    ax.axhline(0, color=COLORS["grid"], linewidth=1.2)

    top_legs = legs.nlargest(8, "Value_Score")
    for _, row in top_legs.iterrows():
        ax.annotate(
            row["Leg"],
            (row["Shadow_Price"], row["Revenue_Contribution"] / 1000),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
        )

    legend_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=palette[tag],
            markersize=10,
            label=recommendation_label(tag),
        )
        for tag in ["Upgauge_or_AddCapacity", "Downgauge", "Review_Schedule", "Keep"]
    ]
    ax.legend(handles=legend_handles, frameon=False, loc="upper left")
    save_figure(fig, "question4_bottleneck_legs.png")


def plot_unmet_demand(data: dict[str, pd.DataFrame]) -> None:
    products = data["products"].copy()

    top_legs = (
        products.groupby("Bottleneck_Leg", as_index=False)["Unmet"]
        .sum()
        .sort_values("Unmet", ascending=True)
        .tail(10)
    )
    top_products = products.sort_values("Unmet", ascending=True).tail(10).copy()

    fig = plt.figure(figsize=(16, 8))
    gs = fig.add_gridspec(1, 2, left=0.07, right=0.98, top=0.95, bottom=0.10, wspace=0.18)
    ax_legs = fig.add_subplot(gs[0, 0])
    ax_products = fig.add_subplot(gs[0, 1])

    ax_legs.barh(top_legs["Bottleneck_Leg"], top_legs["Unmet"], color=COLORS["orange"])
    ax_legs.set_title("瓶颈航段未满足需求 Top 10", loc="left", fontsize=15, fontweight="bold")
    ax_legs.set_xlabel("未满足需求总量")

    ax_products.barh(top_products["Product"], top_products["Unmet"], color=COLORS["red"])
    ax_products.set_title("未满足需求最高的产品 Top 10", loc="left", fontsize=15, fontweight="bold")
    ax_products.set_xlabel("未满足需求")
    save_figure(fig, "question4_unmet_demand.png")


def plot_fleet_cost_effectiveness(data: dict[str, pd.DataFrame]) -> None:
    fleet = data["fleet"].copy().sort_values("Cost_Effectiveness_Index")
    colors = fleet_palette(fleet["Utilization_Tag"])
    sizes = fleet["Attributed_Profit"].clip(lower=0) / 3500 + 120

    fig, ax = plt.subplots(figsize=(14.5, 8.4))
    ax.scatter(
        fleet["Cost_Effectiveness_Index"],
        fleet["Utilization_Rate(%)"],
        s=sizes,
        c=colors,
        alpha=0.9,
        linewidth=1.2,
        edgecolors=COLORS["cream"],
    )

    x_median = float(fleet["Cost_Effectiveness_Index"].median())
    ax.axvline(x_median, color=COLORS["grid"], linewidth=1.2)
    ax.axhline(50, color=COLORS["grid"], linewidth=1.2)
    ax.set_title("机型使用情况与性价比", loc="left", fontsize=16, fontweight="bold")
    ax.set_xlabel("性价比指数（越右越高，最优机型 = 100）")
    ax.set_ylabel("利用率（%）")

    for _, row in fleet.iterrows():
        ax.annotate(
            row["Fleet"],
            (row["Cost_Effectiveness_Index"], row["Utilization_Rate(%)"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=10,
        )

    legend_items = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["teal"], markersize=10, label="紧张"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["gold"], markersize=10, label="均衡"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS["muted"], markersize=10, label="闲置"),
    ]
    ax.legend(handles=legend_items, frameon=False, loc="upper right", title="机型状态")

    save_figure(fig, "question4_fleet_cost_effectiveness.png")


def main() -> None:
    configure_style()
    data = load_data()
    plot_fleet_portrait(data)
    plot_adjustment_actions(data)
    plot_leg_bottlenecks(data)
    plot_unmet_demand(data)
    plot_fleet_cost_effectiveness(data)
    print(f"Saved figures to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
