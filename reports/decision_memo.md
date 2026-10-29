# Decision memo: how to evaluate retail promotions

**Scope:** fictional retailer, synthetic data only. Monetary values are per promoted store–product–week. This memo supersedes the [original memo](archive/decision_memo_original.md), retained unchanged.

## Decision

Do not justify promotion expansion using a comparison of observed promoted and non-promoted profit. The next actionable step is a prespecified randomized experiment measuring incremental net profit. This analysis does not establish which real promotions should continue or stop.

## Evidence available to an analyst

For the reference dataset (seed 42), the unadjusted profit difference is **+1.81**. The ATT-oriented control-outcome regression is **−15.68**: fit expected profit without promotion on controls, then average observed profit minus that prediction over promoted rows. This is evidence conditional on measured confounders, overlap and the outcome model, not a proven effect.

The previous pooled regression coefficient is **−15.50**. It remains a historical comparison, but with heterogeneous effects it is not generally the average effect among promoted rows. A similar number does not make its estimand correct.

Raw propensity weighting gives **−29.26** and the historical clipped sensitivity gives **−22.27**. Neither weighting result is suitable for a business point recommendation: after weighting, maximum absolute SMD is **0.524** (raw) / **0.270** (clipped), and control ESS is **472** / **1,710** out of **35,467**. Raw weights concentrate **43.51%** of mass in the top 1% of controls. These diagnostics can be computed without knowing causal truth; agreement on a negative sign is not independent validation.

## Evidence available only to the simulator's evaluator

The expected ATT for the realized treated rows and promotion versions is **−14.59**. The oracle averages expected profit differences before intermediate cashflow rounding, with the benchmark then stored to cents, rather than paired realized outcomes. The rounding discrepancy from expected rounded outcomes is at most about 0.025 per row. This benchmark is unavailable in a real promotion dataset.

Five fixed independent seeds redraw the retail panel and outcomes. The regression ATT's errors range **−1.38 to +1.31**, with **MAE 0.91** and **RMSE 1.02**. The naive comparison has **MAE 22.01**; raw weighting has **MAE 19.93**, and clipped weighting **10.74**. Five runs do not establish confidence intervals, a general method ranking or real-world causal validity. The linear outcome model can still be misspecified.

The simulator bounds actual treatment probabilities between 0.03 and 0.88. The fitted logistic model misses the clipped shape, producing much more extreme odds. This helps explain poor balance and error; it is distinct from a structural lack of overlap in the simulator.

## Segments are hypotheses, not a targeting policy

The [oracle margin/discount table](methodology_upgrade/oracle_segments_seed42.csv) is descriptive. With fixed value bands, seed 42's high-margin (`>0.45`), low-discount (`<=0.12`) cell has 509 promoted rows and oracle mean expected effect **+13.62**. That number comes from hidden synthetic truth, not an estimated segment treatment effect. It cannot justify a deployment rule, causal ranking of discounts or a profitability promise.

No action labels, targeting rules or trained policies are derived from `_true` columns. Realized discount and promotion type are parts of treatment; grouping on them is not baseline covariate adjustment. The plausible hypothesis to test is whether specified shallow-discount designs preserve more incremental profit in products with higher pre-treatment margin.

## Proposed next experiment

1. Define eligible stores/products and promotion packages before assignment. Randomize no promotion versus specified packages; discount/type must be assigned, not retrospectively selected.
2. Use a small number of prespecified blocks, such as category and prior demand/margin bands. Choose randomization units that limit spillovers and substitution; account for repeated store/product measurements and possible carryover.
3. Measure net profit including discount and promotion costs over a prespecified horizon. Track stockouts and substitution as guardrails, rather than conditioning the primary estimate on post-treatment outcomes.
4. Set sample size using independent-unit variation and an economically meaningful minimum effect. Predefine cluster-aware analysis, confidence intervals, stopping rules and limited segment comparisons.
5. Decide on rollout only after the experiment. Its eligible-population or package-specific effect will be a new estimand, not automatically this historical-mix ATT.

No power, sample-size, ROI or rollout claim is supplied from these synthetic five-run results. This project excludes corporate data and production integration; it demonstrates measurement discipline and transparent uncertainty.
