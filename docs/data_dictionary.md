# Data Dictionary

The synthetic panel has **50 stores × 20 products × 52 weeks = 52,000 rows** per seed. The unique key is `(store_id, product_id, week)`. Monetary values are synthetic units, with no claimed currency or real retailer. Baseline store and product attributes repeat across weeks; row count does not imply that many independent business units.

## Keys and baseline predictors

Every variable marked **X** belongs to the explicit estimator whitelist. Store and product IDs identify rows but are not regression predictors. In a real analysis, any estimated baseline measure must be based only on information available before promotion assignment; its availability here is a simulation assumption.

| Variable | Role | Definition |
|---|---|---|
| `store_id` | Key | Store identifier. |
| `product_id` | Key | Product identifier. |
| `week` | Key, X | Week index from 1 to 52. |
| `region` | X | Northeast, South, Midwest, or West. |
| `store_size` | X | Small, medium, or large. |
| `urbanicity` | X | Rural, suburban, or urban. |
| `baseline_demand` | X | Synthetic store-level demand before promotion. |
| `local_income_index` | X | Synthetic store-level income index. |
| `competition_intensity` | X | Store-level competition index, bounded between 0.05 and 0.95. |
| `category` | X | Beverages, snacks, household, personal care, or frozen food. |
| `brand_tier` | X | Value, mainstream, or premium. |
| `base_price` | X | Regular unit price before discount. |
| `margin_rate` | X | Regular gross margin fraction; unit cost is `base_price * (1 - margin_rate)`. |
| `price_elasticity` | X | Synthetic product-level price sensitivity, assigned before treatment. |
| `baseline_popularity` | X | Product-level baseline demand multiplier. |
| `month` | X | Approximate month index derived from the 52-week index; not an actual dated calendar. |
| `season` | X | Season label derived from that month index. |
| `holiday_flag` | X | Indicator for the simulator's fixed holiday weeks. |
| `seasonal_demand_index` | X | Baseline demand multiplier combining season, annual cycle, and holidays. |

Categorical predictors are `region`, `store_size`, `urbanicity`, `category`, `brand_tier`, and `season`. Regression uses one reference level per category. Balance diagnostics retain **every level**, including reference levels.

## Treatment and observed outcomes

| Variable | Role | Definition |
|---|---|---|
| `promotion_flag` | Treatment T | 1 if the row receives a promotion, otherwise 0. Used as the propensity response, to define comparison groups, and as the historical pooled OLS treatment regressor. |
| `promo_type` | Treatment version; excluded from X | Display, coupon, or price cut for treated rows; `none` for controls. Sampled after assignment. |
| `discount_depth` | Treatment version; excluded from X | Discount fraction, rounded to three decimals; zero for controls. Sampled after assignment. |
| `units_sold` | Observed outcome; excluded from X | Poisson draw around expected units under the received treatment. |
| `revenue` | Observed outcome; excluded from X | `units_sold * base_price * (1 - discount_depth)`, rounded to cents. |
| `gross_profit` | Observed outcome; excluded from X | Revenue minus `units_sold * base_price * (1 - margin_rate)`, rounded to cents. |
| `promo_cost` | Observed treatment cost; excluded from X | Fixed promotion cost plus a version-specific rate times units sold and base price; zero for controls and rounded to cents. |
| `net_profit` | Primary outcome Y; excluded from X | Gross profit minus promotion cost, rounded to cents. |

Discount and promotion type are components of the treatment received, not baseline confounders for the existing binary-treatment ATT. Their use as adjustment features would change the question and can introduce post-treatment bias. The observed outcome is a response, never an input feature.

## Simulator-only fields

These fields are not available to an analyst observing real sales. They are excluded from model fitting even though they appear in the generated CSV.

| Variable | Definition and permitted use |
|---|---|
| `treatment_probability` | True assignment probability from a logistic score clipped to `[0.03, 0.88]`. Assignment uses the unrounded probability; the exported value is rounded to four decimals. Used only to describe and verify the generator, never as an estimated propensity predictor or weighting input. |
| `treatment_effect_true` | Relative unit lift for the received promotion, rounded to four decimals; zero placeholder for controls. This is a fractional units effect, **not a profit effect**. |
| `incremental_units_true` | Mean units without promotion times the unrounded relative lift, rounded to two decimals for treated rows; zero placeholder for controls. This rounded quantity enters the Poisson mean. |
| `incremental_profit_true` | Expected profit with the received promotion minus expected profit without promotion, rounded to cents for treated rows; zero placeholder for controls. Used only for evaluation and the explicitly labelled oracle illustration. |

The benchmark is the mean of `incremental_profit_true` **among promoted rows only**. It averages expected effects for the realized treated rows and their existing promotion versions. It excludes sampled sales noise and is not a paired realized potential-outcome contrast. Separate cent rounding of observed accounting quantities creates a small distinction from the exact expected rounded observed outcome. Control placeholders do not provide counterfactual effects and cannot be used to calculate ATE.

## Derived analysis outputs

| Output | Meaning |
|---|---|
| Estimated propensity | Model-fitted promotion probability using X only; distinct from `treatment_probability`. |
| Raw ATT weight | 1 for treated rows; estimated propensity odds for controls. |
| Clipped ATT weight | Same formula after clipping estimated scores to `[0.02, 0.98]`; a labelled sensitivity analysis. |
| Estimation error | Estimate minus that seed's benchmark ATT; available only for synthetic evaluation. |
| `margin_band` | Fixed oracle-illustration intervals: at most 0.35, above 0.35 through 0.45, and above 0.45. |
| `discount_band` | Fixed oracle-illustration intervals: at most 0.12, above 0.12 through 0.18, and above 0.18. |

The fixed bands keep identical values in the same group. The oracle segment table is a description of simulated treatment versions, not an estimated segment policy or a causal comparison between discount bands. No truth-based action labels are generated by the current analysis.

See [causal assumptions](causal_assumptions.md) and [the methodology audit](methodology_audit.md) for estimator conditions and limitations.
