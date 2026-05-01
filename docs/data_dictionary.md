# Data Dictionary

## Unit of observation

The unit of observation is:

**store × product × week**

Each row represents one product sold in one store during one week.

---

## Store variables

| Variable | Description |
|---|---|
| store_id | Unique store identifier |
| region | Store region |
| store_size | Store size: small, medium, large |
| urbanicity | Urban, suburban, or rural location |
| baseline_demand | Average store-level demand |
| local_income_index | Synthetic local income index |
| competition_intensity | Level of nearby competition |

---

## Product variables

| Variable | Description |
|---|---|
| product_id | Unique product identifier |
| category | Product category |
| brand_tier | Premium, mainstream, or value |
| base_price | Regular product price |
| margin_rate | Gross margin rate |
| price_elasticity | Product sensitivity to price changes |
| baseline_popularity | Product-level baseline demand |

---

## Time variables

| Variable | Description |
|---|---|
| week | Week number |
| month | Month number |
| season | Season label |
| holiday_flag | Whether the week includes a holiday period |
| seasonal_demand_index | Synthetic seasonal demand multiplier |

---

## Treatment variables

| Variable | Description |
|---|---|
| promotion_flag | Whether the observation received a promotion |
| discount_depth | Size of the discount |
| promo_type | Type of promotion: display, coupon, or price cut |
| treatment_probability | Probability of promotion assignment |

---

## Outcome variables

| Variable | Description |
|---|---|
| units_sold | Observed units sold |
| revenue | Observed revenue |
| gross_profit | Revenue after product margin |
| promo_cost | Cost of running the promotion |
| net_profit | Gross profit minus promotion cost |
| treatment_effect_true | Synthetic benchmark causal effect for promoted rows; zero for non-promoted rows |
| incremental_units_true | Synthetic benchmark incremental units for promoted rows; zero for non-promoted rows |
| incremental_profit_true | Synthetic benchmark incremental profit for promoted rows; zero for non-promoted rows |

The three `_true` columns are synthetic benchmark columns. They are not available in real business data and must not be used as model features.

---

## Hidden logic

The synthetic dataset includes two worlds:

1. **Observed world** — what an analyst sees.
2. **Ground truth** — the true synthetic treatment effect known by design.

This makes it possible to show how much naive analysis overestimates or underestimates the real promotion effect.
