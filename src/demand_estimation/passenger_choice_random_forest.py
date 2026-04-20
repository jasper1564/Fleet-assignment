"""
Question 2: passenger choice analysis and demand restoration with Random Forest.

This script now uses a four-stage workflow:
1. Detect likely censoring from the RD booking-curve structure.
2. Train a behavior model (near_ratio) on uncensored products only.
3. Recover demand for censored products and build final_demand.
4. Train a second demand model on final_demand to answer:
   "which product features affect total demand?"

Important modeling assumptions:
- We do not assume true censoring labels are known.
- Censoring is inferred from RD columns and booking-curve shape, not from exogenous
  product features.
- The near_ratio model is a behavior model. The final_demand model is the demand model.
- The reliable window is an empirical parameter and is only used for censored products.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold

warnings.filterwarnings("ignore")

matplotlib.rcParams["font.family"] = "SimHei"
matplotlib.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parents[2]

PRODUCTS_INPUT = ROOT / "data" / "raw" / "booking" / "itinerary_sales_by_rd.csv"
SCHEDULE_INPUT = ROOT / "data" / "raw" / "schedule" / "flight_schedule.csv"
MARKET_SHARE_INPUT = ROOT / "data" / "raw" / "reference" / "market_share_by_od.csv"

INTERIM_DIR = ROOT / "data" / "interim" / "passenger_choice"
FIGURE_DIR = ROOT / "results" / "figures" / "passenger_choice"

CORRECTED_DEMAND_OUTPUT = INTERIM_DIR / "corrected_demand_random_forest.csv"
CENSORING_OUTPUT = INTERIM_DIR / "censoring_detection_random_forest.csv"
NEAR_IMPORTANCE_OUTPUT = INTERIM_DIR / "near_ratio_feature_importance.csv"
FINAL_IMPORTANCE_OUTPUT = INTERIM_DIR / "final_demand_feature_importance.csv"
METRICS_OUTPUT = INTERIM_DIR / "random_forest_model_metrics.csv"
FIGURE_OUTPUT = FIGURE_DIR / "random_forest_summary.png"

EPS = 1e-9

# Empirical parameters. These are intentionally explicit and easy to change.
RELIABLE_WINDOW_RD = 7
STRICT_RECENT_WINDOW_RD = 4
CLOSE_IN_WINDOW_RD = 6
SHOULDER_WINDOW_RD = 33
MIN_TOTAL_SALES_FOR_CENSOR_FLAG = 1.5
MAX_CLOSE_IN_SHARE_FOR_CENSOR_FLAG = 0.05
MIN_NEAR_RATIO_PRED = 0.01
MAX_NEAR_RATIO_PRED = 0.95
PERMUTATION_SAMPLE_MAX = 5000

RF_PARAMS = {
    "n_estimators": 400,
    "max_depth": 10,
    "min_samples_leaf": 20,
    "max_features": "sqrt",
    "random_state": 42,
    "n_jobs": -1,
}

FEATURE_LABELS = {
    "class_rank": "票价等级序号",
    "relative_fare": "相对票价",
    "n_stops": "中转次数",
    "duration_min": "飞行时长(分钟)",
    "dep_period": "起飞时段",
    "host_share": "主航司市场份额",
    "od_n_products": "OD产品数",
    "is_BA": "是否为BA航班",
    "arr_period": "到达时段",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw inputs used by the RF demand-estimation pipeline."""
    products = pd.read_csv(PRODUCTS_INPUT)
    schedule = pd.read_csv(SCHEDULE_INPUT)
    market = pd.read_csv(MARKET_SHARE_INPUT)
    return products, schedule, market


def build_rd_columns(df: pd.DataFrame) -> tuple[list[str], dict[str, int]]:
    """Return RD columns sorted from far-to-departure to near-to-departure."""
    rd_cols = [col for col in df.columns if col.startswith("RD") and col[2:].isdigit()]
    rd_cols = sorted(rd_cols, key=lambda col: int(col[2:]), reverse=True)
    rd_values = {col: int(col[2:]) for col in rd_cols}
    return rd_cols, rd_values


def select_rd_columns(
    rd_cols: list[str],
    rd_values: dict[str, int],
    min_rd: int | None = None,
    max_rd: int | None = None,
) -> list[str]:
    """Select RD columns by numeric RD range."""
    return [
        col
        for col in rd_cols
        if (min_rd is None or rd_values[col] >= min_rd)
        and (max_rd is None or rd_values[col] <= max_rd)
    ]


def sum_rd_window(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    """Safely sum a set of RD columns, returning zeros if the set is empty."""
    if not cols:
        return pd.Series(0.0, index=df.index)
    return df[cols].fillna(0.0).sum(axis=1)


def count_positive_rd(df: pd.DataFrame, cols: list[str], eps: float = EPS) -> pd.Series:
    """Count RD observations with strictly positive sales inside a window."""
    if not cols:
        return pd.Series(0, index=df.index, dtype=int)
    return (df[cols].fillna(0.0) > eps).sum(axis=1)


def compute_last_positive_rd(df: pd.DataFrame, rd_cols: list[str], rd_values: dict[str, int]) -> pd.Series:
    """
    Find the closest-to-departure RD bucket with observed positive sales.

    If the closest positive booking appears far from departure, the curve may be truncated.
    """
    closest_first = sorted(rd_cols, key=lambda col: rd_values[col])
    result = []
    for _, row in df[closest_first].fillna(0.0).iterrows():
        last_positive = np.nan
        for col in closest_first:
            if row[col] > EPS:
                last_positive = rd_values[col]
                break
        result.append(last_positive)
    return pd.Series(result, index=df.index, dtype="float64")


def detect_censoring(
    df: pd.DataFrame,
    rd_cols: list[str],
    rd_values: dict[str, int],
    reliable_window_rd: int = RELIABLE_WINDOW_RD,
    strict_recent_window_rd: int = STRICT_RECENT_WINDOW_RD,
    close_in_window_rd: int = CLOSE_IN_WINDOW_RD,
    shoulder_window_rd: int = SHOULDER_WINDOW_RD,
    min_total_sales_for_flag: float = MIN_TOTAL_SALES_FOR_CENSOR_FLAG,
    max_close_in_share_for_flag: float = MAX_CLOSE_IN_SHARE_FOR_CENSOR_FLAG,
) -> pd.DataFrame:
    """
    Rule-based censoring detection driven only by RD structure.

    This is an empirical identification step, not a supervised classifier.
    The rules deliberately rely on booking-curve shape rather than exogenous product features.
    """
    out = df.copy()

    strict_recent_cols = select_rd_columns(
        rd_cols, rd_values, min_rd=None, max_rd=strict_recent_window_rd
    )
    close_in_cols = select_rd_columns(
        rd_cols, rd_values, min_rd=None, max_rd=close_in_window_rd
    )
    reliable_cols = select_rd_columns(
        rd_cols, rd_values, min_rd=reliable_window_rd, max_rd=None
    )
    shoulder_cols = select_rd_columns(
        rd_cols, rd_values, min_rd=reliable_window_rd, max_rd=shoulder_window_rd
    )

    out["sales_total"] = sum_rd_window(out, rd_cols)
    out["sales_reliable"] = sum_rd_window(out, reliable_cols)
    out["sales_close_in"] = sum_rd_window(out, close_in_cols)
    out["sales_recent"] = sum_rd_window(out, strict_recent_cols)
    out["sales_shoulder"] = sum_rd_window(out, shoulder_cols)

    out["positive_close_in_obs"] = count_positive_rd(out, close_in_cols)
    out["positive_recent_obs"] = count_positive_rd(out, strict_recent_cols)
    out["last_positive_rd"] = compute_last_positive_rd(out, rd_cols, rd_values)

    out["close_in_share"] = np.where(
        out["sales_total"] > 0,
        out["sales_close_in"] / out["sales_total"],
        np.nan,
    )
    out["reliable_share"] = np.where(
        out["sales_total"] > 0,
        out["sales_reliable"] / out["sales_total"],
        np.nan,
    )

    # Individual shape signals kept as separate columns for transparency.
    out["signal_last_positive_far"] = out["last_positive_rd"].fillna(-1) >= reliable_window_rd
    out["signal_recent_blank"] = out["sales_recent"] <= EPS
    out["signal_close_in_blank"] = out["sales_close_in"] <= EPS
    out["signal_close_in_share_low"] = out["close_in_share"].fillna(0.0) <= max_close_in_share_for_flag
    out["signal_shoulder_has_sales"] = out["sales_shoulder"] > EPS
    out["signal_nontrivial_sales"] = out["sales_total"] >= min_total_sales_for_flag

    signal_cols = [
        "signal_last_positive_far",
        "signal_recent_blank",
        "signal_close_in_share_low",
        "signal_shoulder_has_sales",
        "signal_nontrivial_sales",
    ]
    out["censoring_signal_count"] = out[signal_cols].sum(axis=1)

    censored_mask = (
        out["signal_last_positive_far"]
        & out["signal_recent_blank"]
        & out["signal_shoulder_has_sales"]
        & out["signal_nontrivial_sales"]
        & (out["signal_close_in_blank"] | out["signal_close_in_share_low"])
    )
    out["censoring_status"] = np.where(censored_mask, "censored", "uncensored")

    def build_reason(row: pd.Series) -> str:
        reasons = []
        if row["signal_last_positive_far"]:
            reasons.append("last_positive_rd_far_from_departure")
        if row["signal_recent_blank"]:
            reasons.append("recent_window_has_no_sales")
        if row["signal_close_in_blank"]:
            reasons.append("close_in_window_is_blank")
        elif row["signal_close_in_share_low"]:
            reasons.append("close_in_share_is_very_low")
        if row["signal_shoulder_has_sales"]:
            reasons.append("shoulder_window_still_has_sales")
        if row["signal_nontrivial_sales"]:
            reasons.append("total_sales_is_nontrivial")
        if not reasons:
            reasons.append("no_censoring_signal_triggered")
        return ";".join(reasons)

    out["censoring_reason"] = out.apply(build_reason, axis=1)
    return out


def count_stops(row: pd.Series) -> int:
    """Count itinerary stops based on Flight2 and Flight3."""
    stops = 0
    if pd.notna(row.get("Flight2")) and str(row["Flight2"]).strip() != ".":
        stops += 1
    if pd.notna(row.get("Flight3")) and str(row["Flight3"]).strip() != ".":
        stops += 1
    return stops


def hhmm_utc_min(time_value: float | int, utc_offset_hours: float | int) -> int:
    """Convert HHMM and UTC offset to minutes on a common UTC-like axis."""
    hhmm = int(time_value)
    hour, minute = divmod(hhmm, 100)
    return hour * 60 + minute - int(float(utc_offset_hours)) * 60


def build_features(
    df: pd.DataFrame, schedule: pd.DataFrame, market: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    """
    Build exogenous features only.

    We intentionally do not use censoring flags, observed demand totals, or other
    post-outcome variables as predictive features.
    """
    out = df.copy()

    out["Fare"] = pd.to_numeric(out["Fare"], errors="coerce")

    class_rank = (
        out.groupby("Class")["Fare"].median().sort_values().rank(method="first").astype(int)
    )
    out["class_rank"] = out["Class"].map(class_rank)

    od_avg_fare = out.groupby(["Origin", "Destination"])["Fare"].transform("mean")
    out["relative_fare"] = out["Fare"] / (od_avg_fare + EPS)

    out["n_stops"] = out.apply(count_stops, axis=1)
    out["flight1_id"] = out["Flight1"].astype(str).str[:6]

    sch = (
        schedule.sort_values(["flight", "deptime"])
        .groupby("flight", as_index=False)
        .first()
        .copy()
    )
    sch["duration_min"] = sch.apply(
        lambda row: hhmm_utc_min(row["arrtime"], row["arroff"])
        - hhmm_utc_min(row["deptime"], row["depoff"]),
        axis=1,
    )
    sch.loc[sch["duration_min"] < 0, "duration_min"] += 1440

    out = out.merge(
        sch[["flight", "duration_min", "deptime", "arrtime"]].rename(
            columns={"flight": "flight1_id"}
        ),
        on="flight1_id",
        how="left",
    )

    out["dep_hour"] = pd.to_numeric(out["deptime"], errors="coerce").fillna(0).astype(int) // 100
    out["dep_period"] = pd.cut(
        out["dep_hour"],
        bins=[-1, 5, 11, 17, 24],
        labels=[0, 1, 2, 3],
    ).astype(float)

    out["arr_hour"] = pd.to_numeric(out["arrtime"], errors="coerce").fillna(0).astype(int) // 100
    out["arr_period"] = pd.cut(
        out["arr_hour"],
        bins=[-1, 5, 11, 17, 24],
        labels=[0, 1, 2, 3],
    ).astype(float)

    market_df = market.rename(columns={"Org": "Origin", "Des": "Destination"})
    out = out.merge(market_df, on=["Origin", "Destination"], how="left")
    out["host_share"] = pd.to_numeric(out["Host_share"], errors="coerce")
    out["host_share"] = out["host_share"].fillna(out["host_share"].median())

    out["od_n_products"] = out.groupby(["Origin", "Destination"])["Fare"].transform("count")
    out["is_BA"] = out["Flight1"].astype(str).str.startswith("BA").astype(int)

    feature_cols = list(FEATURE_LABELS.keys())
    for col in feature_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[col] = out[col].fillna(out[col].median())

    return out, feature_cols


def fit_random_forest_model(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    train_mask: pd.Series,
    model_name: str,
    clip_bounds: tuple[float, float] | None = None,
    log_target: bool = False,
) -> dict[str, object]:
    """
    Train a RandomForestRegressor with cross-validation and importance outputs.

    Parameters
    ----------
    clip_bounds:
        Optional bounds applied after inverse-transforming predictions.
    log_target:
        If True, fit on log1p(target) and transform predictions back to the original scale.
    """
    train_df = df.loc[train_mask, feature_cols + [target_col]].dropna().copy()
    if train_df.empty:
        raise ValueError(f"{model_name}: no training rows available after filtering.")

    n_splits = min(5, len(train_df))
    if n_splits < 2:
        raise ValueError(f"{model_name}: not enough rows for cross-validation.")

    X = train_df[feature_cols]
    y_true = train_df[target_col].astype(float).to_numpy()
    y_fit = np.log1p(y_true) if log_target else y_true.copy()

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    oof_pred = np.zeros(len(train_df), dtype=float)

    for fold_id, (train_idx, valid_idx) in enumerate(kf.split(X), start=1):
        model = RandomForestRegressor(**RF_PARAMS)
        model.fit(X.iloc[train_idx], y_fit[train_idx])
        fold_pred = model.predict(X.iloc[valid_idx])
        if log_target:
            fold_pred = np.expm1(fold_pred)
        if clip_bounds is not None:
            lower, upper = clip_bounds
            fold_pred = clip_series_bounds(pd.Series(fold_pred), lower, upper).to_numpy()
        oof_pred[valid_idx] = fold_pred

        fold_r2 = r2_score(y_true[valid_idx], fold_pred)
        fold_mae = mean_absolute_error(y_true[valid_idx], fold_pred)
        print(f"{model_name} - Fold {fold_id}: R2={fold_r2:.4f}, MAE={fold_mae:.4f}")

    overall_r2 = r2_score(y_true, oof_pred)
    overall_mae = mean_absolute_error(y_true, oof_pred)
    print(f"{model_name} - OOF R2={overall_r2:.4f}, OOF MAE={overall_mae:.4f}")

    final_model = RandomForestRegressor(**RF_PARAMS)
    final_model.fit(X, y_fit)

    perm_sample = train_df.sample(
        n=min(PERMUTATION_SAMPLE_MAX, len(train_df)),
        random_state=42,
    )
    X_perm = perm_sample[feature_cols]
    y_perm = np.log1p(perm_sample[target_col].astype(float).to_numpy()) if log_target else perm_sample[
        target_col
    ].astype(float).to_numpy()
    perm = permutation_importance(
        final_model,
        X_perm,
        y_perm,
        n_repeats=10,
        random_state=42,
        n_jobs=1,
    )

    importance_df = pd.DataFrame(
        {
            "feature": feature_cols,
            "description": [FEATURE_LABELS[col] for col in feature_cols],
            "mdi_importance": final_model.feature_importances_,
            "permutation_importance": perm.importances_mean,
        }
    )
    importance_df["rank_score"] = (
        importance_df["mdi_importance"].rank(ascending=False)
        + importance_df["permutation_importance"].rank(ascending=False)
    ) / 2.0
    importance_df = importance_df.sort_values(
        ["rank_score", "permutation_importance", "mdi_importance"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    importance_df["model_name"] = model_name
    importance_df["target"] = target_col

    metrics = {
        "model_name": model_name,
        "target": target_col,
        "train_rows": len(train_df),
        "r2": overall_r2,
        "mae": overall_mae,
        "log_target": log_target,
    }

    return {
        "model": final_model,
        "train_index": train_df.index,
        "feature_cols": feature_cols,
        "target_col": target_col,
        "clip_bounds": clip_bounds,
        "log_target": log_target,
        "oof_pred": pd.Series(oof_pred, index=train_df.index, name=f"{model_name}_oof_pred"),
        "importance_df": importance_df,
        "metrics": metrics,
    }


def predict_from_bundle(bundle: dict[str, object], df: pd.DataFrame) -> pd.Series:
    """Generate predictions on the original target scale from a trained model bundle."""
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    clip_bounds = bundle["clip_bounds"]
    log_target = bundle["log_target"]

    pred = model.predict(df[feature_cols])
    if log_target:
        pred = np.expm1(pred)
    pred_series = pd.Series(pred, index=df.index, dtype=float)
    if clip_bounds is not None:
        lower, upper = clip_bounds
        pred_series = clip_series_bounds(pred_series, lower, upper)
    return pred_series


def train_near_ratio_model(df: pd.DataFrame, feature_cols: list[str]) -> dict[str, object]:
    """Behavior model: fit X -> near_ratio using uncensored products only."""
    train_mask = (
        (df["censoring_status"] == "uncensored")
        & (df["sales_total"] > 0)
        & df["near_ratio"].notna()
    )
    return fit_random_forest_model(
        df=df,
        feature_cols=feature_cols,
        target_col="near_ratio",
        train_mask=train_mask,
        model_name="near_ratio_model",
        clip_bounds=(MIN_NEAR_RATIO_PRED, MAX_NEAR_RATIO_PRED),
        log_target=False,
    )


def recover_demand_for_censored_products(
    df: pd.DataFrame,
    near_ratio_bundle: dict[str, object],
    reliable_window_rd: int = RELIABLE_WINDOW_RD,
) -> pd.DataFrame:
    """
    Recover demand using the behavior model.

    For uncensored products:
        final_demand = sales_total
    For censored products:
        corrected_demand = max(sales_total, reliable_sales / (1 - pred_near_ratio))

    Here reliable_sales refers to the observed sales outside the empirical close-in window.
    The reliable window is configurable because the RD grid is sparse and the cutoff is
    an operational approximation rather than a true latent censoring boundary.
    """
    out = df.copy()

    out["pred_near_ratio"] = predict_from_bundle(near_ratio_bundle, out)
    out["pred_near_ratio"] = out["pred_near_ratio"].clip(
        lower=MIN_NEAR_RATIO_PRED, upper=MAX_NEAR_RATIO_PRED
    )

    out["reliable_window_rd"] = reliable_window_rd
    out["reliable_sales_for_recovery"] = np.where(
        out["censoring_status"] == "censored",
        out["sales_reliable"],
        out["sales_total"],
    )
    out["corrected_demand"] = np.where(
        out["censoring_status"] == "censored",
        np.maximum(
            out["sales_total"],
            out["reliable_sales_for_recovery"] / (1.0 - out["pred_near_ratio"]).clip(lower=0.05),
        ),
        out["sales_total"],
    )
    out["final_demand"] = np.where(
        out["censoring_status"] == "censored",
        out["corrected_demand"],
        out["sales_total"],
    )
    out["demand_uplift_pct"] = np.where(
        out["sales_total"] > 0,
        out["final_demand"] / out["sales_total"] - 1.0,
        0.0,
    )
    return out


def train_final_demand_model(df: pd.DataFrame, feature_cols: list[str]) -> dict[str, object]:
    """Demand model: fit X -> final_demand on the restored full-demand target."""
    train_mask = (df["final_demand"] > 0) & df["final_demand"].notna()
    return fit_random_forest_model(
        df=df,
        feature_cols=feature_cols,
        target_col="final_demand",
        train_mask=train_mask,
        model_name="final_demand_model",
        clip_bounds=None,
        log_target=True,
    )


def clip_series_bounds(series: pd.Series, lower: float | None, upper: float | None) -> pd.Series:
    """Clip a pandas Series while allowing one-sided bounds."""
    if lower is None and upper is None:
        return series
    if upper is None:
        return series.clip(lower=lower)
    if lower is None:
        return series.clip(upper=upper)
    return series.clip(lower=lower, upper=upper)


def plot_results(
    df: pd.DataFrame,
    near_ratio_bundle: dict[str, object],
    final_demand_bundle: dict[str, object],
) -> None:
    """Create a compact summary figure for censoring, behavior, and demand modeling."""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    near_imp = near_ratio_bundle["importance_df"].head(10).iloc[::-1]
    demand_imp = final_demand_bundle["importance_df"].head(10).iloc[::-1]

    near_actual = df.loc[near_ratio_bundle["train_index"], "near_ratio"]
    near_oof = near_ratio_bundle["oof_pred"]
    final_actual = df.loc[final_demand_bundle["train_index"], "final_demand"]
    final_oof = final_demand_bundle["oof_pred"]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    censor_counts = df["censoring_status"].value_counts().reindex(["uncensored", "censored"]).fillna(0)
    axes[0, 0].bar(
        ["uncensored", "censored"],
        censor_counts.values,
        color=["#2e8b57", "#d35454"],
    )
    axes[0, 0].set_title("规则识别的截断样本数量")
    axes[0, 0].set_ylabel("产品数")

    axes[0, 1].scatter(near_actual, near_oof, alpha=0.35, s=18, color="#2c7fb8")
    near_min = min(float(near_actual.min()), float(near_oof.min()))
    near_max = max(float(near_actual.max()), float(near_oof.max()))
    axes[0, 1].plot([near_min, near_max], [near_min, near_max], "--", color="gray")
    axes[0, 1].set_title("行为模型: near_ratio OOF预测")
    axes[0, 1].set_xlabel("实际 near_ratio")
    axes[0, 1].set_ylabel("预测 near_ratio")

    axes[1, 0].barh(
        near_imp["description"],
        near_imp["permutation_importance"],
        color="#f39c12",
        alpha=0.9,
    )
    axes[1, 0].set_title("行为模型特征重要性 Top 10")
    axes[1, 0].set_xlabel("Permutation importance")

    axes[1, 1].barh(
        demand_imp["description"],
        demand_imp["permutation_importance"],
        color="#16a085",
        alpha=0.9,
    )
    axes[1, 1].set_title("需求模型特征重要性 Top 10")
    axes[1, 1].set_xlabel("Permutation importance")

    plt.tight_layout()
    plt.savefig(FIGURE_OUTPUT, dpi=150)
    plt.close(fig)

    # Save an extra scatter for final demand inside the same file is enough for this stage.
    # The demand-model numeric evaluation is preserved in the metrics CSV.
    print(f"Saved figure: {FIGURE_OUTPUT}")


def save_outputs(
    df: pd.DataFrame,
    near_ratio_bundle: dict[str, object],
    final_demand_bundle: dict[str, object],
) -> None:
    """Persist row-level outputs, detection diagnostics, metrics, and importances."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    censor_cols = [
        "Origin",
        "Destination",
        "Flight1",
        "Flight2",
        "Flight3",
        "Class",
        "Fare",
        "sales_total",
        "sales_reliable",
        "sales_close_in",
        "sales_recent",
        "sales_shoulder",
        "last_positive_rd",
        "close_in_share",
        "reliable_share",
        "positive_recent_obs",
        "positive_close_in_obs",
        "censoring_signal_count",
        "censoring_status",
        "censoring_reason",
    ]
    df[censor_cols].to_csv(CENSORING_OUTPUT, index=False, encoding="utf-8-sig")

    main_cols = [
        "Origin",
        "Destination",
        "Flight1",
        "Flight2",
        "Flight3",
        "Class",
        "Fare",
        "sales_reliable",
        "sales_close_in",
        "sales_total",
        "near_ratio",
        "pred_near_ratio",
        "censoring_status",
        "censoring_reason",
        "reliable_window_rd",
        "reliable_sales_for_recovery",
        "corrected_demand",
        "final_demand",
        "pred_final_demand",
        "demand_uplift_pct",
        "class_rank",
        "relative_fare",
        "n_stops",
        "duration_min",
        "dep_period",
        "host_share",
        "od_n_products",
        "is_BA",
        "arr_period",
    ]
    df[main_cols].to_csv(CORRECTED_DEMAND_OUTPUT, index=False, encoding="utf-8-sig")

    near_ratio_bundle["importance_df"].to_csv(
        NEAR_IMPORTANCE_OUTPUT, index=False, encoding="utf-8-sig"
    )
    final_demand_bundle["importance_df"].to_csv(
        FINAL_IMPORTANCE_OUTPUT, index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(
        [near_ratio_bundle["metrics"], final_demand_bundle["metrics"]]
    ).to_csv(METRICS_OUTPUT, index=False, encoding="utf-8-sig")

    print(f"Saved row-level output: {CORRECTED_DEMAND_OUTPUT}")
    print(f"Saved censoring output: {CENSORING_OUTPUT}")
    print(f"Saved near-ratio importance: {NEAR_IMPORTANCE_OUTPUT}")
    print(f"Saved final-demand importance: {FINAL_IMPORTANCE_OUTPUT}")
    print(f"Saved model metrics: {METRICS_OUTPUT}")


def print_summary(
    df: pd.DataFrame,
    near_ratio_bundle: dict[str, object],
    final_demand_bundle: dict[str, object],
) -> None:
    """Print a concise textual summary of the new workflow."""
    censored_count = int((df["censoring_status"] == "censored").sum())
    uncensored_count = int((df["censoring_status"] == "uncensored").sum())
    mean_total_sales = float(df["sales_total"].mean())
    mean_final_demand = float(df["final_demand"].mean())

    print("\n" + "=" * 72)
    print("Two-stage correction + demand modeling summary")
    print("=" * 72)
    print(f"Uncensored products: {uncensored_count}")
    print(f"Censored products:   {censored_count}")
    print(f"Mean observed sales_total: {mean_total_sales:.3f}")
    print(f"Mean restored final_demand: {mean_final_demand:.3f}")
    print(
        f"Near-ratio model OOF: R2={near_ratio_bundle['metrics']['r2']:.4f}, "
        f"MAE={near_ratio_bundle['metrics']['mae']:.4f}"
    )
    print(
        f"Final-demand model OOF: R2={final_demand_bundle['metrics']['r2']:.4f}, "
        f"MAE={final_demand_bundle['metrics']['mae']:.4f}"
    )

    print("\nTop drivers of near_ratio:")
    for _, row in near_ratio_bundle["importance_df"].head(5).iterrows():
        print(f"  - {row['description']} ({row['feature']})")

    print("\nTop drivers of final_demand:")
    for _, row in final_demand_bundle["importance_df"].head(5).iterrows():
        print(f"  - {row['description']} ({row['feature']})")


def main() -> None:
    """Run the full staged Random Forest demand-restoration workflow."""
    products, schedule, market = load_data()
    rd_cols, rd_values = build_rd_columns(products)

    df = detect_censoring(products, rd_cols, rd_values)

    near_cols = select_rd_columns(rd_cols, rd_values, min_rd=None, max_rd=RELIABLE_WINDOW_RD - 1)
    df["sales_near"] = sum_rd_window(df, near_cols)
    df["near_ratio"] = np.where(
        df["sales_total"] > 0,
        df["sales_near"] / df["sales_total"],
        np.nan,
    )

    df, feature_cols = build_features(df, schedule, market)

    near_ratio_bundle = train_near_ratio_model(df, feature_cols)
    df = recover_demand_for_censored_products(df, near_ratio_bundle)

    final_demand_bundle = train_final_demand_model(df, feature_cols)
    df["pred_final_demand"] = clip_series_bounds(
        predict_from_bundle(final_demand_bundle, df),
        lower=0.0,
        upper=None,
    )

    save_outputs(df, near_ratio_bundle, final_demand_bundle)
    plot_results(df, near_ratio_bundle, final_demand_bundle)
    print_summary(df, near_ratio_bundle, final_demand_bundle)


if __name__ == "__main__":
    main()
