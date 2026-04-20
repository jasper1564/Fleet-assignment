# `passenger_choice_random_forest.py`

## Purpose

This script is the core implementation for Question 2. It no longer stops at
"which features affect near-term booking share". It now uses a staged workflow
to answer the real question:

`features -> total demand`

while still preserving a behavior-model layer based on `near_ratio`.

## Current Workflow

1. Detect likely censoring from RD booking-curve structure.
2. Train a Random Forest behavior model on uncensored products only:
   `X -> near_ratio`
3. Recover demand for censored products and construct `final_demand`.
4. Train a second Random Forest demand model on restored demand:
   `X -> final_demand`

## Key Principle

- Censoring is inferred from RD columns, not predicted from exogenous features.
- `near_ratio` is a behavior variable, not the final business answer.
- `final_demand` is the target used to answer which features drive total demand.

## Inputs

- `data/raw/booking/itinerary_sales_by_rd.csv`
- `data/raw/schedule/flight_schedule.csv`
- `data/raw/reference/market_share_by_od.csv`

## Outputs

- `data/interim/passenger_choice/censoring_detection_random_forest.csv`
- `data/interim/passenger_choice/corrected_demand_random_forest.csv`
- `data/interim/passenger_choice/near_ratio_feature_importance.csv`
- `data/interim/passenger_choice/final_demand_feature_importance.csv`
- `data/interim/passenger_choice/random_forest_model_metrics.csv`
- `results/figures/passenger_choice/random_forest_summary.png`

## Downstream Role

- `merge_rf_demand_into_products.py` now prefers `final_demand`
- `products_csv_to_product_info_json.py` continues to consume the merged
  `Total_Demand`
- `fleet_assignment_main.py` ultimately uses the RF-restored demand route

## Current Run Summary

The latest calibrated run uses the following empirical censoring thresholds:

- `RELIABLE_WINDOW_RD = 7`
- `CLOSE_IN_WINDOW_RD = 6`
- `STRICT_RECENT_WINDOW_RD = 4`
- `MIN_TOTAL_SALES_FOR_CENSOR_FLAG = 1.5`
- `MAX_CLOSE_IN_SHARE_FOR_CENSOR_FLAG = 0.05`

Under this setting, the current RF run produced:

- Total products: `47,190`
- Effective products with positive observed sales: `20,053`
- Detected censored products: `2,199`
- Detected censored share among effective products: `10.97%`

Demand restoration totals:

- Observed total demand (`sales_total` sum): `82,025.68`
- Restored total demand (`final_demand` sum): `84,974.02`
- Absolute uplift: `2,948.34`
- Overall uplift vs observed demand: `3.59%`

For the censored subset only:

- Observed demand sum: `13,029.29`
- Restored demand sum: `15,977.63`
- Absolute uplift: `2,948.34`
- Aggregate uplift vs censored observed demand: `22.63%`
- Mean per-product uplift: `26.66%`
- Median per-product uplift: `19.53%`

Model performance:

- Behavior model `X -> near_ratio`
  - OOF `R² = 0.3717`
  - OOF `MAE = 0.2558`
- Demand model `X -> final_demand`
  - OOF `R² = 0.3487`
  - OOF `MAE = 2.9727`

Interpretation:

- The behavior model is used to infer how much a product depends on close-in sales.
- The demand model is the actual model used to answer which features drive total demand.
- The restored demand uplift is concentrated entirely in the censored subset; uncensored
  products keep `final_demand = sales_total`.

## Data Findings

One important finding from the current RF run is that the data issue is not only
"censoring in positive-sales products". There is also a large zero-demand mass in
the raw product table.

Current data facts:

- Total products: `47,190`
- Positive-sales products: `20,053`
- Zero-sales products: `27,137`
- Zero-sales share: `57.51%`

This zero-demand mass is structurally uneven rather than random:

- By stop count:
  - `n_stops = 0`: zero-sales share `17.63%`
  - `n_stops = 1`: zero-sales share `67.74%`
  - `n_stops = 2`: zero-sales share `78.91%`
- By fare class, zero-sales share varies widely and is especially high in some
  long-tail classes such as `S`, `B`, and `M`.

Interpretation:

- Many zero-sales products are likely true long-tail or weak products.
- Therefore, "zero sales" cannot be treated as equivalent to "missing demand".
- The current RF mainline only restores demand for products with positive observed
  sales and censoring signals. This is intentional and conservative.

## Deferred Zero-Demand Recovery Path

We evaluated whether the current demand model could be used to fill all zero-sales
products directly via `pred_final_demand`, and the conclusion is: not yet.

Why this path is deferred:

- The current demand model is trained on positive-demand products only.
- It does not distinguish between:
  - true-zero demand products
  - false-zero / potentially missing-demand products
- If all zero-sales products were directly imputed using current
  `pred_final_demand`, the additional restored demand would be about `19,997.39`,
  which would lift total demand from `84,974.02` to about `104,971.41`.
- That is an extra `23.53%` on top of the current RF-restored total, and
  `27.97%` above raw observed demand, which is too aggressive to merge into the
  mainline without a separate screening design.

Current project decision:

- Keep the current RF mainline focused on censoring-aware restoration only.
- Do not activate global zero-demand imputation in the main demand pipeline yet.
- Keep zero-demand recovery as a future branch for separate design and validation.

Recommended future design:

1. First identify which zero-sales products are plausible false zeros.
2. Use additional screening rules before any demand imputation.
3. Only then evaluate whether a separate RF branch for zero-demand restoration is
   justified.

## Feature Importance

Recommended importance metric for explanation: `permutation_importance`.

Behavior model (`near_ratio`) top drivers:

1. `class_rank` - `0.2894`
2. `relative_fare` - `0.1868`
3. `od_n_products` - `0.0685`
4. `duration_min` - `0.0467`
5. `host_share` - `0.0465`
6. `n_stops` - `0.0246`
7. `arr_period` - `0.0161`
8. `dep_period` - `0.0145`
9. `is_BA` - `0.0080`

Demand model (`final_demand`) top drivers:

1. `n_stops` - `0.8725`
2. `relative_fare` - `0.1325`
3. `class_rank` - `0.1070`
4. `host_share` - `0.0767`
5. `duration_min` - `0.0731`
6. `od_n_products` - `0.0421`
7. `is_BA` - `0.0411`
8. `dep_period` - `0.0074`
9. `arr_period` - `0.0054`

Interpretation:

- Close-in booking behavior is driven mainly by price-related variables.
- Total demand is driven most strongly by itinerary complexity, especially `n_stops`,
  and then by price competitiveness and market environment.

## Notes

- The reliable window is still an empirical parameter, but it is now used only
  inside the censoring-aware recovery step rather than as a universal hardcoded
  truncation rule.
- The script keeps all major intermediate results so the restoration logic is
  auditable instead of being a one-step black box.
