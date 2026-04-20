"""
第二问：旅客行程选择行为分析 —— 影响机票销售因素识别
算法：随机森林（Random Forest）

建模逻辑：
  目标变量：near_ratio = sales_near / sales_total（近期销量占比）
    → 衡量"该产品有多依赖临近出发的销售"
    → 这是截断损失的直接代理变量，也反映旅客购票行为特征

  特征：全部为外生特征（产品属性 + 市场环境）
    → 剔除高度共线性特征（如绝对票价、log票价等），防止重要性稀释
    → 目的是找到"是什么核心属性导致产品更多在临近出发时售出"

  需求还原：
    corrected_demand = max(sales_total, sales_reliable / (1 - predicted_near_ratio))
"""

import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.inspection import permutation_importance

matplotlib.rcParams["font.family"] = "SimHei"
matplotlib.rcParams["axes.unicode_minus"] = False

# ──────────────────────────────────────────
# 1. 数据加载
# ──────────────────────────────────────────
products = pd.read_csv("data_fam_products.csv")
schedule = pd.read_csv("data_fam_schedule.csv")
market   = pd.read_csv("data_fam_market_share.csv")

rd_cols = sorted(
    [c for c in products.columns if c.startswith("RD")],
    key=lambda x: int(x[2:]), reverse=True
)

TRUNC = 14
rd_reliable = [c for c in rd_cols if int(c[2:]) >= TRUNC]
rd_near     = [c for c in rd_cols if int(c[2:]) <  TRUNC]

products["sales_reliable"] = products[rd_reliable].sum(axis=1)
products["sales_near"]     = products[rd_near].sum(axis=1)
products["sales_total"]    = products[rd_cols].sum(axis=1)

# 目标变量：近期销量占比（截断区比例越高 → 截断损失越大）
products["near_ratio"] = (
    products["sales_near"] / products["sales_total"].replace(0, np.nan)
)

df = products[products["sales_total"] > 0].copy()
print(f"建模样本量：{len(df)} 条（过滤零销量后）")

# ──────────────────────────────────────────
# 2. 纯外生特征工程
# ──────────────────────────────────────────

# ── A. 价格层级与相对竞争力 ──
df["Fare"] = df["Fare"]  # 保留用于最终输出

# 票价等级 → 按各等级在数据集内 Fare 中位数排序（数据驱动）
class_rank = (
    df.groupby("Class")["Fare"].median()
    .rank(method="first").astype(int)
    .rename("class_rank")
)
df["class_rank"] = df["Class"].map(class_rank)
print("\n票价等级序号映射（1=最低价等级）：")
print(class_rank.sort_values().to_dict())

# 相对票价：该产品票价 / 同OD市场平均票价
# 替代绝对票价，反映跨市场的真实价格竞争力
od_avg_fare = df.groupby(["Origin", "Destination"])["Fare"].transform("mean")
df["relative_fare"] = df["Fare"] / (od_avg_fare + 1e-9)

# ── B. 行程复杂度 ─────────────────────────
def count_stops(row):
    s = 0
    if pd.notna(row["Flight2"]) and str(row["Flight2"]).strip() != ".": s += 1
    if pd.notna(row["Flight3"]) and str(row["Flight3"]).strip() != ".": s += 1
    return s

df["n_stops"] = df.apply(count_stops, axis=1)

# 飞行时长（UTC分钟）
def hhmm_utc_min(t, off):
    h, m = int(t) // 100, int(t) % 100
    return h * 60 + m - int(off) * 60

sch = (
    schedule.sort_values(["flight", "deptime"])
    .groupby("flight").first().reset_index()
)
sch["duration_min"] = sch.apply(
    lambda r: hhmm_utc_min(r["arrtime"], r["arroff"])
              - hhmm_utc_min(r["deptime"], r["depoff"]), axis=1
)
sch.loc[sch["duration_min"] < 0, "duration_min"] += 1440

df["flight1_id"] = df["Flight1"].str[:6]
df = df.merge(
    sch[["flight", "duration_min", "deptime", "arrtime"]].rename(columns={"flight": "flight1_id"}),
    on="flight1_id", how="left"
)

# 起飞时段
df["dep_hour"]   = df["deptime"].fillna(0).astype(int) // 100
df["dep_period"] = pd.cut(
    df["dep_hour"], bins=[-1, 5, 11, 17, 24], labels=[0, 1, 2, 3]
).astype(float)

# ── C. 市场竞争环境 ───────────────────────
mkt = market.rename(columns={"Org": "Origin", "Des": "Destination"})
df  = df.merge(mkt, on=["Origin", "Destination"], how="left")
df["host_share"]    = df["Host_share"].fillna(df["Host_share"].median())
df["od_n_products"] = df.groupby(["Origin", "Destination"])["Fare"].transform("count")

# ── D. 来源航司 ───────────────────────────
df["is_BA"] = df["Flight1"].str.startswith("BA").astype(int)

# ── E. 补充深层特征 ───────────────────────
# (已删除 fare_time_pain 和 od_market_heat)

# 落地时段估算：直接使用 schedule 中的当地到达时间
df["arrtime"] = df["arrtime"].fillna(0).astype(int)
df["arr_hour"] = df["arrtime"] // 100   # arrtime 是 HHMM 整数，整除100得小时
df["arr_period"] = pd.cut(
    df["arr_hour"], bins=[-1, 5, 11, 17, 24], labels=[0, 1, 2, 3]
).astype(float)

# ──────────────────────────────────────────
# 【精简后】的核心特征字典
# 移除了 fare、log_fare、fare_time_pain、od_market_heat
# ──────────────────────────────────────────
FEATURES = {
    "class_rank":     "票价等级序号",
    "relative_fare":  "相对票价（vs OD均价）",
    "n_stops":        "中转次数",
    "duration_min":   "飞行时长（分钟）",
    "dep_period":     "起飞时段",
    "host_share":     "A公司市场份额",
    "od_n_products":  "同OD产品数",
    "is_BA":          "是否原B公司航班",
    "arr_period":     "落地到达时段",
}
feat_cols = list(FEATURES.keys())
print(f"\n特征数：{len(feat_cols)}（已剔除共线性特征，保证重要性评估无偏差）")

df_model = df[feat_cols + ["near_ratio", "sales_reliable", "sales_total", "Fare"]].dropna().copy()
X = df_model[feat_cols].values
y = df_model["near_ratio"].values
print(f"建模样本：{len(df_model)} 条")

# ──────────────────────────────────────────
# 3. 随机森林 5折CV
# ──────────────────────────────────────────
print("\n" + "─" * 50)
print("随机森林训练（5折CV）—— 目标：near_ratio（近期销量占比）")
print("─" * 50)

rf_params = dict(
    n_estimators=500,
    max_depth=10,
    min_samples_leaf=20,
    max_features="sqrt",
    random_state=42,
    n_jobs=-1,
)

kf  = KFold(n_splits=5, shuffle=True, random_state=42)
oof = np.zeros(len(X))
best_model, best_r2 = None, -np.inf

for fold, (tr, va) in enumerate(kf.split(X)):
    rf = RandomForestRegressor(**rf_params)
    rf.fit(X[tr], y[tr])
    oof[va] = rf.predict(X[va])
    r2  = r2_score(y[va], oof[va])
    mae = mean_absolute_error(y[va], oof[va])
    print(f"  Fold {fold+1}  R²={r2:.4f}  MAE(near_ratio)={mae:.4f}")
    if r2 > best_r2:
        best_r2, best_model = r2, rf

print(f"\n  总体 OOF  R²={r2_score(y, oof):.4f}")
print(f"  总体 OOF  MAE={mean_absolute_error(y, oof):.4f}")
print("  （R² 不高是合理的：外生特征无法完全解释随机购票行为，但能识别系统性规律）")

# ──────────────────────────────────────────
# 4. 特征重要性（MDI + 置换）
# ──────────────────────────────────────────
print("\n" + "─" * 50)
print("特征重要性")
print("─" * 50)

mdi_imp  = best_model.feature_importances_
perm     = permutation_importance(
    best_model, X, y, n_repeats=20, random_state=42, n_jobs=1
)
perm_imp = perm.importances_mean

imp_df = pd.DataFrame({
    "特征":       feat_cols,
    "说明":       [FEATURES[f] for f in feat_cols],
    "MDI重要性":  mdi_imp,
    "置换重要性": perm_imp,
})
imp_df["综合排名"] = (
    imp_df["MDI重要性"].rank(ascending=False) +
    imp_df["置换重要性"].rank(ascending=False)
) / 2
imp_df = imp_df.sort_values("综合排名").reset_index(drop=True)
imp_df.index += 1
print(imp_df[["特征", "说明", "MDI重要性", "置换重要性"]].to_string())

# ──────────────────────────────────────────
# 5. 可视化
# ──────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# 左：特征重要性
x_pos = np.arange(len(feat_cols))
w = 0.35
ax = axes[0]
ax.barh(x_pos + w/2, imp_df["MDI重要性"],  w, label="MDI",  color="#2980b9", alpha=0.85)
ax.barh(x_pos - w/2, imp_df["置换重要性"], w, label="置换", color="#e67e22", alpha=0.85)
ax.set_yticks(x_pos)
ax.set_yticklabels(imp_df["说明"], fontsize=9)
ax.set_xlabel("重要性得分")
ax.set_title("影响近期购票占比的外生因素重要性 (去共线性精简版)", fontsize=12)
ax.legend()
ax.invert_yaxis()

# 右：各票价等级的 near_ratio 箱线图
ax2 = axes[1]
class_order = (
    df.groupby("Class")["near_ratio"].median()
    .sort_values(ascending=False).index.tolist()
)
df_plot = df[df["near_ratio"].notna()]
ax2.boxplot(
    [df_plot[df_plot["Class"] == c]["near_ratio"].values for c in class_order],
    labels=class_order, patch_artist=True,
    boxprops=dict(facecolor="#aed6f1"),
    medianprops=dict(color="red", linewidth=2),
)
ax2.axhline(df_plot["near_ratio"].mean(), color="gray", ls="--", lw=1, label="全局均值")
ax2.set_xlabel("票价等级")
ax2.set_ylabel("近期销量占比（near_ratio）")
ax2.set_title("各票价等级近期销售占比分布\n（越高 → 截断损失越大）", fontsize=12)
ax2.legend()

plt.tight_layout()
plt.savefig("q2_random_forest.png", dpi=150)
plt.show()
print("✓ 图已保存：q2_random_forest.png")

# ──────────────────────────────────────────
# 6. 需求还原
#    corrected_demand = max(sales_total, sales_reliable / (1 - predicted_near_ratio))
# ──────────────────────────────────────────
pred_near = np.clip(best_model.predict(X), 0.01, 0.95)
df_model["pred_near_ratio"]  = pred_near
# 修改点：使用 max(观测总销量, 早期可靠销量/(1-预测占比))
df_model["corrected_demand"] = np.maximum(df_model["sales_total"], df_model["sales_reliable"] / (1 - pred_near))

print(f"\n需求还原统计：")
print(f"  观测总销量均值   : {df_model['sales_total'].mean():.3f}")
print(f"  还原后需求均值   : {df_model['corrected_demand'].mean():.3f}")
uplift = (df_model["corrected_demand"] / df_model["sales_total"].replace(0, np.nan) - 1).mean()
print(f"  平均修正幅度     : {uplift:.2%}")

for col in ["Origin", "Destination", "Flight1", "Flight2", "Flight3",
            "Class", "Fare", "sales_near", "sales_total"]:
    if col not in df_model.columns:
        df_model[col] = df.loc[df_model.index, col].values

out_cols = [
    "Origin", "Destination", "Flight1", "Flight2", "Flight3",
    "Class", "Fare", "sales_reliable", "sales_near", "sales_total",
    "pred_near_ratio", "corrected_demand",
    "n_stops", "duration_min", "dep_period", "host_share",
    "arr_period"
]
df_model[[c for c in out_cols if c in df_model.columns]].to_csv(
    "q2_corrected_demand.csv", index=False
)
print("✓ 已输出：q2_corrected_demand.csv")

# ──────────────────────────────────────────
# 7. 结论
# ──────────────────────────────────────────
print("\n" + "=" * 58)
print("【第二问结论】影响近期购票占比的因素（综合排名）")
print("（near_ratio 越高 → 该产品截断损失越大 → 需求被低估越多）")
print("=" * 58)
for _, row in imp_df.iterrows():
    print(f"  {int(row.name):>2}. {row['说明']:24s}  ({row['特征']})")