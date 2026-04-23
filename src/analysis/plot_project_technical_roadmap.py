from __future__ import annotations

from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "results" / "figures" / "project"


COLORS = {
    "paper": "#F6F1E8",
    "panel": "#FFFDF8",
    "ink": "#24313A",
    "muted": "#71808D",
    "grid": "#D8D4CB",
    "teal": "#2F7E90",
    "teal_light": "#D7ECE7",
    "gold": "#E8C468",
    "gold_light": "#FBF2D7",
    "orange": "#E58A2B",
    "orange_light": "#FBE7D4",
    "rose": "#C65B4B",
    "rose_light": "#F9DFDA",
    "slate": "#8C97A4",
    "slate_light": "#EEF1F5",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": COLORS["paper"],
            "axes.facecolor": COLORS["paper"],
            "savefig.facecolor": COLORS["paper"],
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
            "axes.unicode_minus": False,
        }
    )


def add_shadow(patch: FancyBboxPatch) -> None:
    patch.set_path_effects(
        [
            pe.withSimplePatchShadow(offset=(2.0, -2.0), shadow_rgbFace="#C8C1B6", alpha=0.18),
            pe.Normal(),
        ]
    )


def draw_card(
    ax: plt.Axes,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: list[str],
    facecolor: str,
    edgecolor: str,
    chip_text: str,
    chip_color: str,
    dashed: bool = False,
    title_size: float = 14,
    body_size: float = 10.2,
) -> None:
    card = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.8,rounding_size=3.8",
        linewidth=1.8,
        edgecolor=edgecolor,
        facecolor=facecolor,
        linestyle="--" if dashed else "-",
    )
    add_shadow(card)
    ax.add_patch(card)

    chip_w = max(10.0, 0.46 * len(chip_text) + 6.0)
    chip = FancyBboxPatch(
        (x + 2.0, y + h - 6.2),
        chip_w,
        4.4,
        boxstyle="round,pad=0.25,rounding_size=2.0",
        linewidth=0,
        facecolor=chip_color,
    )
    ax.add_patch(chip)
    ax.text(
        x + 2.0 + chip_w / 2.0,
        y + h - 4.05,
        chip_text,
        ha="center",
        va="center",
        fontsize=9.4,
        color="white" if chip_color != COLORS["gold"] else COLORS["ink"],
        fontweight="bold",
    )

    ax.text(
        x + 2.0,
        y + h - 10.2,
        title,
        ha="left",
        va="top",
        fontsize=title_size,
        fontweight="bold",
        color=COLORS["ink"],
    )

    start_y = y + h - 15.0
    step = min(4.1, max(3.1, (h - 17.0) / max(len(lines), 1)))
    for idx, line in enumerate(lines):
        ax.text(
            x + 2.3,
            start_y - idx * step,
            f"- {line}",
            ha="left",
            va="top",
            fontsize=body_size,
            color=COLORS["ink"],
        )


def connect(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str,
    lw: float = 2.2,
    dashed: bool = False,
    rad: float = 0.0,
    label: str | None = None,
    label_offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=14,
        linewidth=lw,
        color=color,
        linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=6,
        shrinkB=6,
    )
    ax.add_patch(arrow)

    if label:
        mid_x = (start[0] + end[0]) / 2 + label_offset[0]
        mid_y = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            mid_x,
            mid_y,
            label,
            fontsize=9.2,
            color=color,
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.2",
                "facecolor": COLORS["paper"],
                "edgecolor": "none",
            },
        )


def draw_legend(ax: plt.Axes) -> None:
    box = FancyBboxPatch(
        (118.0, 83.0),
        28.0,
        11.0,
        boxstyle="round,pad=0.7,rounding_size=3.2",
        linewidth=1.2,
        edgecolor=COLORS["grid"],
        facecolor=COLORS["panel"],
    )
    add_shadow(box)
    ax.add_patch(box)
    ax.text(120.0, 91.0, "图例", fontsize=11.2, fontweight="bold", color=COLORS["ink"])

    ax.plot([120.0, 127.0], [87.8, 87.8], color=COLORS["teal"], linewidth=2.4)
    ax.text(128.5, 87.8, "正式建模主线", va="center", fontsize=9.5, color=COLORS["ink"])

    ax.plot([120.0, 127.0], [85.0, 85.0], color=COLORS["gold"], linewidth=2.4)
    ax.text(128.5, 85.0, "正式分析支线", va="center", fontsize=9.5, color=COLORS["ink"])

    ax.plot([120.0, 127.0], [82.2, 82.2], color=COLORS["slate"], linewidth=2.4, linestyle="--")
    ax.text(128.5, 82.2, "对照 / 扩展路径", va="center", fontsize=9.5, color=COLORS["ink"])


def draw_footer(ax: plt.Axes) -> None:
    footer = FancyBboxPatch(
        (31.0, 4.0),
        114.0,
        12.5,
        boxstyle="round,pad=0.8,rounding_size=3.8",
        linewidth=1.5,
        edgecolor=COLORS["grid"],
        facecolor=COLORS["panel"],
    )
    add_shadow(footer)
    ax.add_patch(footer)

    ax.text(34.0, 13.1, "最终交付层", fontsize=12.6, fontweight="bold", color=COLORS["ink"])
    ax.text(
        34.0,
        9.4,
        "答题文档、结构化结果表、模型说明、项目图表与管理建议在这一层集中交付。",
        fontsize=10.1,
        color=COLORS["ink"],
    )
    ax.text(
        34.0,
        6.3,
        "核心载体：docs/question1_answer.md、passenger_choice_random_forest.md、results/runs/model_current、docs/question4_answer.md",
        fontsize=9.3,
        color=COLORS["muted"],
    )


def build_figure() -> plt.Figure:
    fig = plt.figure(figsize=(19, 10))
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92])
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 100)
    ax.axis("off")

    fig.text(0.04, 0.95, "项目技术路线图", fontsize=24, fontweight="bold", color=COLORS["ink"])
    fig.text(
        0.04,
        0.915,
        "从原始数据、需求恢复到机型分配优化与结果解释，形成“历史分析 + 建模主线 + 管理解读”的完整闭环。",
        fontsize=11.8,
        color=COLORS["muted"],
    )

    ax.text(4.0, 89.5, "项目起点", fontsize=12.0, fontweight="bold", color=COLORS["muted"])
    ax.text(31.0, 89.5, "共享基础层", fontsize=12.0, fontweight="bold", color=COLORS["muted"])
    ax.text(61.0, 89.5, "问题主线与支线", fontsize=12.0, fontweight="bold", color=COLORS["muted"])
    ax.text(93.0, 89.5, "优化求解", fontsize=12.0, fontweight="bold", color=COLORS["muted"])
    ax.text(121.0, 89.5, "结果解释", fontsize=12.0, fontweight="bold", color=COLORS["muted"])

    draw_card(
        ax,
        x=5.0,
        y=56.0,
        w=20.0,
        h=28.0,
        title="题目目标与四个问题",
        lines=[
            "问题1 并购前后收益比较",
            "问题2 旅客行为与需求恢复",
            "问题3 并购后机型分配",
            "问题4 机队使用与调整建议",
        ],
        facecolor=COLORS["panel"],
        edgecolor=COLORS["grid"],
        chip_text="项目目标层",
        chip_color=COLORS["ink"],
    )

    draw_card(
        ax,
        x=5.0,
        y=24.0,
        w=20.0,
        h=24.0,
        title="原始数据层",
        lines=[
            "flight_schedule.csv",
            "itinerary_sales_by_rd.csv",
            "fleet_family_master.csv",
            "market_share_by_od.csv",
        ],
        facecolor=COLORS["panel"],
        edgecolor=COLORS["grid"],
        chip_text="原始输入",
        chip_color=COLORS["ink"],
    )

    draw_card(
        ax,
        x=31.0,
        y=56.0,
        w=24.0,
        h=28.0,
        title="共享预处理与输入构建",
        lines=[
            "统一航班、航段、任务结构",
            "构建网络输入 JSON",
            "沉淀模型共享输入层",
            "保持历史口径与优化口径分离",
        ],
        facecolor=COLORS["teal_light"],
        edgecolor=COLORS["teal"],
        chip_text="共享基础层",
        chip_color=COLORS["teal"],
    )

    draw_card(
        ax,
        x=61.0,
        y=56.0,
        w=26.0,
        h=28.0,
        title="问题二：RF 两阶段需求恢复",
        lines=[
            "基于 RD 结构规则识别截断",
            "未截断样本训练 near_ratio",
            "恢复 corrected_demand / final_demand",
            "输出 product_info_rf_predicted.json",
        ],
        facecolor=COLORS["teal_light"],
        edgecolor=COLORS["teal"],
        chip_text="正式建模主线",
        chip_color=COLORS["teal"],
    )

    draw_card(
        ax,
        x=93.0,
        y=56.0,
        w=22.0,
        h=28.0,
        title="问题三：机型分配优化",
        lines=[
            "fleet_assignment_main.py",
            "需求 + 网络 + 机队联合求解",
            "输出收入、成本、利润",
            "输出机队、任务与影子价格结果",
        ],
        facecolor=COLORS["teal_light"],
        edgecolor=COLORS["teal"],
        chip_text="正式建模主线",
        chip_color=COLORS["teal"],
    )

    draw_card(
        ax,
        x=121.0,
        y=56.0,
        w=24.0,
        h=28.0,
        title="问题四：结果解释与建议",
        lines=[
            "机队画像与瓶颈识别",
            "未满足需求集中分析",
            "机型性价比与闲置解释",
            "形成调整建议与汇报图表",
        ],
        facecolor=COLORS["orange_light"],
        edgecolor=COLORS["orange"],
        chip_text="正式解释层",
        chip_color=COLORS["orange"],
    )

    draw_card(
        ax,
        x=61.0,
        y=22.0,
        w=26.0,
        h=22.0,
        title="问题一：历史收益比较",
        lines=[
            "原始历史销量口径为主",
            "比较并购前后收入变化",
            "拆解 B 网络与协同贡献",
            "RF 收入口径仅作对照",
        ],
        facecolor=COLORS["gold_light"],
        edgecolor=COLORS["gold"],
        chip_text="正式分析支线",
        chip_color=COLORS["gold"],
    )

    draw_card(
        ax,
        x=93.0,
        y=26.0,
        w=22.0,
        h=14.0,
        title="EM 统计恢复对照",
        lines=[
            "保留为对照与稳健性补充",
            "不作为当前正式主线",
        ],
        facecolor=COLORS["slate_light"],
        edgecolor=COLORS["slate"],
        chip_text="对照路径",
        chip_color=COLORS["slate"],
        dashed=True,
        title_size=12.2,
        body_size=9.4,
    )

    draw_card(
        ax,
        x=121.0,
        y=26.0,
        w=24.0,
        h=14.0,
        title="5 场景 / robust 对照",
        lines=[
            "20 场景已并入正式主线",
            "5 场景归档与历史变体",
            "保留为补充而非主要卖点",
        ],
        facecolor=COLORS["slate_light"],
        edgecolor=COLORS["slate"],
        chip_text="对照路径",
        chip_color=COLORS["slate"],
        dashed=True,
        title_size=12.0,
        body_size=9.2,
    )

    connect(ax, (15.0, 56.0), (15.0, 48.0), color=COLORS["ink"], lw=2.1)
    connect(ax, (25.0, 36.0), (31.0, 70.0), color=COLORS["teal"], lw=2.4, rad=0.08, label="共享基础输入", label_offset=(0.0, 3.0))
    connect(ax, (55.0, 70.0), (61.0, 70.0), color=COLORS["teal"], lw=2.5, label="RD 结构与特征工程", label_offset=(0.0, 3.0))
    connect(ax, (87.0, 70.0), (93.0, 70.0), color=COLORS["teal"], lw=2.5, label="RF 需求 JSON", label_offset=(0.0, 3.0))
    connect(ax, (115.0, 70.0), (121.0, 70.0), color=COLORS["orange"], lw=2.5, label="优化结果解释", label_offset=(0.0, 3.0))

    connect(ax, (25.0, 31.0), (61.0, 33.0), color=COLORS["gold"], lw=2.4, rad=-0.06, label="原始历史销量口径", label_offset=(0.0, 2.5))
    connect(ax, (74.0, 56.0), (104.0, 40.0), color=COLORS["slate"], lw=2.0, dashed=True, rad=0.05)
    connect(ax, (104.0, 56.0), (133.0, 40.0), color=COLORS["slate"], lw=2.0, dashed=True, rad=0.05)
    connect(ax, (74.0, 22.0), (74.0, 16.0), color=COLORS["gold"], lw=2.2)
    connect(ax, (133.0, 26.0), (133.0, 16.0), color=COLORS["orange"], lw=2.2)

    ax.text(
        96.0,
        50.0,
        "问题三同时接收两类输入：\n来自问题二的恢复需求 + 来自预处理层的网络结构。",
        fontsize=9.2,
        color=COLORS["muted"],
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": COLORS["paper"], "edgecolor": "none"},
    )

    ax.text(
        47.0,
        46.5,
        "问题一是正式答题的一部分，\n但它回答的是历史收益，而不是优化利润。",
        fontsize=9.3,
        color=COLORS["muted"],
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": COLORS["paper"], "edgecolor": "none"},
    )

    draw_legend(ax)
    draw_footer(ax)
    return fig


def save_figure(fig: plt.Figure) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / "project_technical_roadmap.png", dpi=240, bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "project_technical_roadmap.svg", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    configure_style()
    fig = build_figure()
    save_figure(fig)
    print(f"Saved roadmap figures to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
