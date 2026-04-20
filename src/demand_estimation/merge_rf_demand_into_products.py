import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PRODUCTS_INPUT = ROOT / "data" / "interim" / "products" / "products_with_total_demand.csv"
CORRECTED_DEMAND_INPUT = ROOT / "data" / "interim" / "passenger_choice" / "corrected_demand_random_forest.csv"
RF_PRODUCTS_OUTPUT = ROOT / "data" / "interim" / "passenger_choice" / "products_with_rf_demand.csv"


def resolve_demand_columns(df_q2: pd.DataFrame) -> list[str]:
    """
    Collect all usable RF demand columns.

    Preference order is:
    1. pred_final_demand: factor-based prediction from the demand model
    2. final_demand: censoring-aware restored demand
    3. corrected_demand: legacy corrected field
    """
    demand_cols = [
        col for col in ["pred_final_demand", "final_demand", "corrected_demand"]
        if col in df_q2.columns
    ]
    if not demand_cols:
        raise ValueError(
            "None of 'pred_final_demand', 'final_demand', or 'corrected_demand' exists in the RF output."
        )
    return demand_cols


def update_demand_values(processed_path: Path, q2_path: Path, output_path: Path) -> None:
    """
    Merge RF-restored demand back into the processed product table.

    Matching is still done by itinerary identity columns.

    Conservative merge rule:
    - For censored products only, allow RF-driven restoration.
    - For uncensored products, keep the observed Total_Demand unchanged.
    - Even for censored products, never drop below the observed Total_Demand.
    """
    print("Reading files...")
    df_processed = pd.read_csv(processed_path)
    df_q2 = pd.read_csv(q2_path)

    demand_cols = resolve_demand_columns(df_q2)
    print(f"Using RF demand columns: {', '.join(demand_cols)}")

    match_keys = ["Org", "Des", "Flight1", "Flight2", "Flight3", "Fare"]

    df_q2_subset = df_q2[
        [
            "Origin",
            "Destination",
            "Flight1",
            "Flight2",
            "Flight3",
            "Fare",
            "censoring_status",
            *demand_cols,
        ]
    ].rename(
        columns={
            "Origin": "Org",
            "Destination": "Des",
        }
    )

    before_count = len(df_q2_subset)
    agg_map = {col: "mean" for col in demand_cols}
    agg_map["censoring_status"] = lambda values: (
        "censored" if (values == "censored").any() else "uncensored"
    )
    df_q2_unique = df_q2_subset.groupby(match_keys, as_index=False).agg(agg_map)
    after_count = len(df_q2_unique)

    if before_count > after_count:
        print(
            f"Detected {before_count - after_count} duplicate RF rows; averaged demand by matching keys."
        )

    print("Merging restored demand into processed products...")
    merged_df = pd.merge(
        df_processed,
        df_q2_unique,
        on=match_keys,
        how="left",
        validate="many_to_one",
    )

    print("Updating Total_Demand...")
    candidate_cols = ["Total_Demand", *demand_cols]
    restored_candidates = merged_df[candidate_cols].max(axis=1, skipna=True)
    merged_df["Total_Demand"] = merged_df["Total_Demand"].where(
        merged_df["censoring_status"].fillna("uncensored") != "censored",
        restored_candidates,
    )

    final_df = merged_df.drop(columns=["censoring_status", *demand_cols])
    final_df.to_csv(output_path, index=False)

    print(f"Saved merged products: {output_path}")
    print(f"Original rows: {len(df_processed)}")
    print(f"Final rows:    {len(final_df)}")
    print(f"Restored total demand: {final_df['Total_Demand'].sum():,.2f}")

    if len(df_processed) != len(final_df):
        print("Warning: row count changed after merge. Please inspect matching keys.")


if __name__ == "__main__":
    try:
        update_demand_values(
            processed_path=PROCESSED_PRODUCTS_INPUT,
            q2_path=CORRECTED_DEMAND_INPUT,
            output_path=RF_PRODUCTS_OUTPUT,
        )
    except Exception as exc:
        print(f"Error: {exc}")
