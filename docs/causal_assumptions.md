# Causal Assumptions and Estimand

## Business question and unit

Does the existing promotion mix increase net profit among the store-product-weeks that received it? The unit is a **store × product × week**. Treatment `T` is `promotion_flag`, outcome `Y` is `net_profit`, and `X` contains only the baseline covariates listed in [the data dictionary](data_dictionary.md).

Net profit includes the price discount, product cost, and promotion cost. Higher sales or higher observed profit in promoted rows does not establish positive incremental profit.

## The target: ATT for the existing promotion mix

The population target is the average treatment effect on treated rows, `ATT = E[Y(1) - Y(0) | T = 1]`. Promotion has multiple versions: display, coupon, and price cut, with different discounts and costs. Here `Y(1)` refers to receiving the promotion version under the simulator's existing assignment mechanism. The analysis does not estimate the effect of one specified discount, a different promotion mix, or a new targeting policy.

For a generated dataset, the evaluation benchmark is the **finite treated average of expected profit effects for the realized promotion versions**:

```text
benchmark ATT = mean(incremental_profit_true among promotion_flag == 1)
```

The generator computes the benchmark from mean unit demand, without the sampled Poisson sales noise. Its stored contrast is rounded to cents. Observed revenue, gross profit, and promotion costs are rounded separately, so the benchmark is a rounded mean-outcome contrast with a cent-scale accounting approximation; it is not an exact expectation of every rounded accounting operation. It is also not an average of realized individual potential-outcome differences: paired noisy potential outcomes are not generated.

Zero values in `_true` columns for control rows are placeholders. They do not mean that these rows would have zero effect if promoted. Averaging `incremental_profit_true` over all rows gives promotion prevalence times the benchmark ATT, **not ATE**.

## Identification assumptions

1. **Consistency and a defined intervention.** Observed outcomes correspond to the received promotion version or no promotion. Conclusions refer to the existing mix, rather than an unspecified universal promotion treatment.
2. **Conditional exchangeability for the untreated outcome.** `E[Y(0) | X, T = 1] = E[Y(0) | X, T = 0]`. For ATT, this is the comparison needed to reconstruct treated rows' untreated outcome. In the simulator, assignment depends on observed baseline demand, popularity, seasonality, holidays, category, and competition, with independent outcome noise.
3. **Support for treated rows.** For covariate profiles represented among treated rows, controls must be possible. The generator clips true assignment probabilities to `[0.03, 0.88]`, so it has no structural positivity failure. Finite samples, high dimensional covariates, and inaccurate estimated scores can still make adjustment unstable.
4. **No interference or carryover.** A row's promotion does not affect another row's sales or later demand in this generator. Real retail promotions can violate this through substitution, stockouts, demand shifting, and spillovers.
5. **Adequate measurement and model specification.** Baseline predictors are available without measurement error in the synthetic setting. Real demand, popularity, or elasticity measures must be constructed using information available before treatment. Identification assumptions alone do not make the fitted regression or propensity model correct.

These assumptions are designed into the simulator. They cannot be established for a real retailer by recovering synthetic truth, inspecting an overlap plot, or obtaining small SMDs.

## What each estimator measures

| Method | Definition and interpretation |
|---|---|
| Naive difference | Mean `Y` in treated rows minus mean `Y` in controls. A descriptive baseline; selection on baseline demand confounds it. |
| Pooled OLS coefficient | Coefficient on `T` in an additive regression of `Y` on `T` and `X`. Retained as a historical comparison. With heterogeneous effects it is generally not ATT, even if it happens to be numerically close. |
| Control regression ATT | Fit `m0(X) = E[Y given X, T = 0]` on controls and compute `mean(Y - m0_hat(X) among T = 1)`. This standardizes the untreated prediction to the treated covariate distribution and does not impose a common treatment slope. It requires an adequate untreated-outcome model and support. |
| Propensity ATT, raw | Fit `e_hat(X) = P(T = 1 given X)` from baseline predictors. Use weight 1 for treated rows and `e_hat / (1 - e_hat)` for controls; subtract the normalized weighted control mean from the treated mean. This targets ATT when the identification assumptions and propensity model are adequate. |
| Propensity ATT, clipped sensitivity | Repeat with estimated scores clipped to `[0.02, 0.98]`, as in the original analysis. This changes the control reweighting and introduces a bias/variance tradeoff. It is not guaranteed to preserve the original ATT target or correct a misspecified model. |

The new outcome model is deliberately a simple main-effects linear regression. The generator's untreated profit includes products and nonlinear functions of covariates, so the regression is not correctly specified by construction. Its small errors in five replications do not establish unbiasedness.

The propensity model is a main-effects logistic regression. The true assignment mechanism is a **clipped** logistic function; an ordinary logistic model cannot exactly represent its floor and ceiling. Fitted scores near one can therefore create extreme odds weights despite the true probabilities being bounded away from one. The raw and clipped diagnostics expose this limitation rather than resolving it by selecting a model against oracle outcomes.

## Leakage boundary and diagnostics

Models use an explicit baseline whitelist. Outcomes, promotion versions, discounts, costs, true assignment probabilities, and synthetic effect columns cannot become predictors. Oracle truth is used only after fitting for evaluation and in a separately labelled simulator illustration. It is never a feature, tuning objective, or policy label.

SMDs compare treated means with unweighted or weighted control means using the same baseline pooled standard deviation, `sqrt((Var(X|T=1) + Var(X|T=0)) / 2)`, throughout. Variances use `ddof=0`; all numeric covariates and all categorical levels are included. The `0.10` guide is descriptive, not a test of identification.

Control effective sample size is `(sum(w))² / sum(w²)`. It describes weight concentration; it is not the number of independent stores, products, or clusters. Score distributions, weight quantiles, maximum weights, and the top 1% weight share accompany it. A broad overlap of score ranges can coexist with serious imbalance and extreme weights.

Five fixed seeds provide an inexpensive sensitivity check. Error means, error standard deviations, and ranges are descriptive summaries of those runs. The project makes no confidence-interval, coverage, cluster-adjusted uncertainty, or real-world causal-validity claim.

See [the methodology audit](methodology_audit.md) for the observed failures, numerical results, and preserved historical artifacts.
