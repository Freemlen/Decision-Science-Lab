# Methodology Audit

## Scope and outcome

This upgrade audits the existing synthetic retail case; it does not replace the data-generating process or add a model search. The main corrections are an explicitly defined ATT, an ATT-oriented outcome-regression estimator, transparent weighting diagnostics, and separation of oracle knowledge from actionable business evidence.

The original generator is retained. The original notebook and memo are preserved in [`notebooks/archive/decision_science_lab_case_study_original.ipynb`](../notebooks/archive/decision_science_lab_case_study_original.ipynb) and [`reports/archive/decision_memo_original.md`](../reports/archive/decision_memo_original.md). Original figures remain in [`reports/figures`](../reports/figures). Their presence preserves history; their estimates and recommendation labels are not the current conclusions. Current numerical results and figures are in [`reports/methodology_upgrade`](../reports/methodology_upgrade).

## Findings and corrections

| Finding in the original case | Assessment and current treatment |
|---|---|
| Ground-truth ATT was averaged only over promoted rows. | Correct aggregation. The definition is now precise: finite treated average expected profit effect for realized promotion versions, rounded to cents. Control zeros are placeholders, not evidence of zero untreated-row effects. |
| Additive pooled OLS treatment coefficient was presented as regression adjustment for ATT. | Not generally ATT under heterogeneous effects. It remains a historical comparator; control-only outcome regression followed by averaging residuals over treated rows is the new ATT-oriented estimator. |
| Actual regression and propensity feature whitelists excluded oracle and post-treatment fields. | No such feature leakage was found in the original fitted models. The defensive blocked list omitted observed outcomes such as units, revenue, gross profit, and net profit. The new whitelist, expanded blocked list, and perturbation test protect the boundary explicitly. |
| ATT weighting used the correct odds formula with scores clipped to `[0.02, 0.98]`, without a separate raw comparison. | The odds formula and normalized control mean were correct. Raw weighting is now shown separately, with the old clipping threshold retained as a labelled sensitivity. Clipping is not an ATT-validity guarantee. |
| Weighted SMDs recomputed the control variance after weighting and covered only seven numeric covariates. | Before/after values changed both the mean difference and its scale. SMDs now use a fixed unweighted pooled SD and cover every baseline numeric predictor and categorical level. |
| Overlap was mainly communicated through plots. | Added score quantiles by arm, treated rows outside the control score range, control ESS, weight quantiles/maxima, threshold counts, and weight share carried by the top 1% of controls. |
| Segment recommendation labels were calculated directly from true synthetic effects. | These were oracle-derived action labels, unavailable in real analysis. The active analysis generates no such policy. The remaining oracle table is explicitly descriptive and can motivate hypotheses for an experiment only. |
| Rank-based quantile segments used `rank(method="first")`. | This could divide identical covariate values across bands by row order. The current illustration uses fixed numeric intervals so tied values stay together. |

## Ground truth and estimators

The generator constructs no-promotion mean demand `lambda0`, then adds the stored rounded expected incremental units for each received promotion. Expected promotion profit applies the discounted unit price, regular unit cost, fixed promotion cost, and variable promotion cost to this mean. `incremental_profit_true` is the promoted-minus-no-promotion expected profit contrast, stored for treated rows and rounded to cents.

Observed units are a Poisson draw. Revenue, gross profit, and promotion cost are rounded separately in the observed accounting path. Therefore the benchmark is a rounded expected contrast with a cent-scale accounting approximation, not an exact contrast of expected rounded accounting quantities or paired realized potential outcomes. This distinction is far smaller than the reported estimation errors but matters for the estimand's definition.

The new control regression estimates:

```text
m0_hat = linear regression of net_profit on baseline X, fitted on controls only
ATT_hat = mean(net_profit - m0_hat(X) among treated rows)
```

It targets the treated distribution without assuming a constant treatment effect. It still needs an adequate model for the untreated outcome. The simulator contains multiplicative and nonlinear mean-demand terms absent from this main-effects regression, so exact specification and unbiasedness are not claimed. A deterministic heterogeneous-effect test demonstrates why this differs from a treatment coefficient: its ATT is 7.4, control regression returns 7.4, and pooled additive OLS returns 5.0.

Raw propensity weighting uses fitted logistic odds on controls and a separately normalized weighted control mean. Its intended target is ATT under the identification and propensity-model conditions. The logistic model is not correct by construction: the true assignment process clips a logistic probability at 0.03 and 0.88, whereas the fitted ordinary logistic model has no such floor or ceiling. This produces fitted probabilities close to one and very large control weights. It is a model and finite-sample diagnostic problem despite structural positivity in the simulator.

The specification and five seeds were fixed before inspecting their new estimates. Oracle fields are removed before estimation; evaluation reads the benchmark after fitting. No model, seed, weight threshold, or policy is selected to match known truth. Full assumptions are in [causal_assumptions.md](causal_assumptions.md).

## Five fixed replications

Seeds **42, 101, 202, 303, and 404** each generate 52,000 rows. Each seed redraws store and product attributes, treatment assignments, promotion versions, and sales noise. These are five independent generator replications, not five bootstrap samples of one retailer. The finite treated target itself changes by seed.

The following values are rounded from [`estimates_by_seed.csv`](../reports/methodology_upgrade/estimates_by_seed.csv). Units are synthetic profit per promoted store-product-week.

| Seed | Expected ATT | Naive | Pooled OLS coefficient | Control regression ATT | Raw propensity ATT | Clipped sensitivity |
|---|---:|---:|---:|---:|---:|---:|
| 42 | -14.59 | 1.81 | -15.50 | -15.68 | -29.26 | -22.27 |
| 101 | -15.58 | 5.34 | -18.36 | -16.96 | -32.55 | -27.64 |
| 202 | -16.99 | 9.01 | -17.74 | -17.59 | -44.48 | -29.90 |
| 303 | -14.20 | 10.11 | -16.57 | -14.37 | -36.45 | -27.31 |
| 404 | -10.78 | 11.65 | -11.54 | -9.47 | -29.04 | -18.72 |

Error is `estimate - that seed's expected ATT`. These five-run summaries come from [`robustness_summary.csv`](../reports/methodology_upgrade/robustness_summary.csv).

| Method | Mean error | MAE | RMSE | Error SD | Error range |
|---|---:|---:|---:|---:|---:|
| Naive | 22.01 | 22.01 | 22.26 | 3.68 | 16.40 to 26.01 |
| Pooled OLS coefficient, historical | -1.51 | 1.51 | 1.75 | 0.98 | -2.77 to -0.74 |
| Control regression ATT | -0.38 | 0.91 | 1.02 | 1.06 | -1.38 to 1.31 |
| Raw propensity ATT | -19.93 | 19.93 | 20.43 | 5.04 | -27.49 to -14.67 |
| Clipped propensity sensitivity | -10.74 | 10.74 | 11.01 | 2.70 | -13.11 to -7.68 |

SD uses `ddof=1`. The error SD is more informative about recovery than the estimate SD because the target varies across seeds; both are exported. A single-run discrepancy is an **estimation error**, not measured statistical bias. Five replications are too few to establish general bias, coverage, or a stable ranking across data-generating processes.

The naive estimate has the wrong sign in all five runs. Control regression has the smallest MAE in this bounded check, with nonzero errors in both directions. The weighting specification performs poorly; its failure remains visible. Pooled OLS being close to truth in these examples does not repair its estimand mismatch.

## What the diagnostics reveal

For seed 42, 35,467 control rows reduce to a raw weight ESS of **471.70 (1.33%)**. The maximum control weight is **515.40**, and the top 1% of controls carry **43.51%** of total control weight. The maximum absolute SMD decreases from **1.017 to 0.524**, leaving substantial measured imbalance.

Across the five seeds, raw control ESS ranges from **304.93 to 914.20 (0.84% to 2.56%)**, maximum control weights range from **211.27 to 937.79**, and maximum absolute weighted SMD ranges from **0.392 to 0.656**. These are reasons to distrust the precision and adjustment quality of this weighting specification. Near-complete overlap of the minimum/maximum score ranges alone is insufficient.

Clipping at `[0.02, 0.98]` caps control weights at 49. For seed 42 it raises ESS to **1,710.27** and reduces maximum absolute SMD to **0.270**, but its error remains **-7.68**. Across seeds, clipped ESS is only **4.00% to 5.42%** of control count and maximum absolute SMD remains **0.195 to 0.351**. Better weight concentration does not establish valid ATT recovery. Full values are in [`diagnostics_by_seed.csv`](../reports/methodology_upgrade/diagnostics_by_seed.csv) and [`balance_by_seed.csv`](../reports/methodology_upgrade/balance_by_seed.csv).

SMD denominators are the original unweighted pooled SDs, with `ddof=0`, and do not change after weighting. ESS is a descriptive measure of weight concentration, not an independent cluster count or a standard-error calculation. The repeated store-product-week structure requires deliberate uncertainty design before confidence intervals would be defensible.

## Business interpretation and remaining limits

An analyst could calculate the observed profit comparisons, model-based point estimates, and their diagnostic weaknesses without access to synthetic truth. An analyst could not know the exact ATT, estimator errors, or oracle segment effects. The current [decision memo](../reports/decision_memo.md) keeps these evidence levels separate.

The oracle margin/discount illustration may suggest a hypothesis about testing promotion designs with different economics. It does not establish the causal effect of changing discount within a margin band, identify an optimal policy, or authorize stopping a real segment. Discount is part of the assigned treatment version; no segment-specific causal estimator or policy evaluation is performed.

The case still has one stylized generator, measured baseline predictors, no unobserved confounding, no stockouts or substitution, and no treatment carryover. Only five seeds are evaluated, with no confidence intervals or clustered uncertainty estimates. The outcome model is simple and potentially misspecified; the propensity specification demonstrably needs improvement before use in a substantive analysis. These are explicit limitations of the portfolio demonstration, not evidence of real-world effectiveness.

## Reproduction and tests

Run `python -m unittest discover -s tests -v` for compact deterministic checks, then `python -m src.run_analysis` to regenerate the fixed five-seed audit. The tests cover seeded data generation, panel invariants, independent reconstruction of oracle expected profit, treated-only benchmark aggregation, heterogeneous-effect estimand alignment, feature-leakage invariance, ATT odds and normalization, ESS scaling, fixed-scale SMDs, full categorical-level balance, input validation, and error-summary arithmetic.

For a clean environment, follow the [README](../README.md). Dependencies are pinned for the tested Python 3.12 scientific stack. `scripts/check_reproduction.py` compares regenerated numeric reports with the committed references using explicit numerical tolerances; runtime, image bytes, and solver iteration counts are not required to be identical across platforms. The run manifest records seeds, package versions, elapsed time, and source hashes. Reproduction checks establish implementation consistency, not causal identification.
