# Decision Science Lab: Causal Analytics for Retail Promotions

A compact portfolio case study demonstrating causal inference, experimentation thinking, and decision-oriented analytics on synthetic retail promotion data.

The project shows how naive promotion analysis can be misleading when promotions are assigned non-randomly, and how causal methods can translate analysis into a business recommendation.

---

## Business question

A retailer runs promotions across stores and products.

Observed sales and profit often look higher during promotions, but the key business question is:

**Should the retailer continue, stop, or target retail promotions?**

The goal is not only to estimate whether promotions increase sales, but whether they create **incremental net profit**.

---

## Key result

Naive analysis suggests that promotions are slightly profitable.

However, because promotions were assigned to stronger store-product-week observations, this comparison is biased.

After adjusting for observed confounders, the ATT-like effect among promoted rows becomes negative and close to the synthetic ground-truth benchmark.

| Estimate | Value | Interpretation |
|---|---:|---|
| Naive promoted vs non-promoted difference | +1.81 | Promotions look slightly profitable |
| Regression-adjusted estimate | -15.50 | Close to true synthetic ATT among promoted rows |
| Propensity score weighted ATT | -22.27 | Correct direction, less stable due to overlap/weights |
| True synthetic ATT among promoted rows | -14.59 | Ground-truth benchmark |

**Main conclusion:** blanket promotions should not be continued based only on naive observed profit comparisons.

---

## Business recommendation

The retailer should move from blanket promotions to targeted promotions.

The strongest positive pocket in the synthetic data is:

| Segment | Avg. true incremental profit | Positive share | Recommendation |
|---|---:|---:|---|
| High-margin / low-discount promotions | +6.27 | 55.5% | Target / continue |

Recommended action:

1. Stop using naive promoted vs non-promoted comparisons as the main decision rule.
2. Limit blanket promotions, especially high-discount and low-margin promotions.
3. Target promotions toward high-margin, low-discount contexts.
4. Validate the targeting rule with a blocked randomized experiment.
5. Use incremental net profit as the primary success metric.

---

## How to read this project

1. Read `README.md` for the overview.
2. Open `notebooks/decision_science_lab_case_study.ipynb` for the full analysis.
3. Read `reports/decision_memo.md` for the business recommendation.
4. Read `docs/causal_assumptions.md` for the causal assumptions.
5. Read `docs/data_dictionary.md` for variable definitions.

---

## Why naive analysis is misleading

Promotions are not assigned randomly.

In this synthetic retail setting, promotions are more likely to be launched for:

- high-demand stores;
- popular products;
- seasonal periods;
- holiday weeks;
- strategic product categories.

These same factors also increase observed sales and profit.

As a result, promoted observations can look better even when the true incremental effect of promotion is negative.

---

## Synthetic data design

The unit of observation is:

**store × product × week**

The dataset contains:

- 50 stores;
- 20 products;
- 52 weeks;
- 52,000 rows.

The synthetic data includes:

- store characteristics;
- product characteristics;
- time and seasonality variables;
- non-random promotion assignment;
- observed sales and profit outcomes;
- hidden synthetic ground truth.

Because the data is synthetic, the true synthetic ATT among promoted rows is known. This allows the project to compare naive estimates, causal estimates, and the synthetic benchmark.

---

## Methods

The MVP includes:

1. **Naive comparison**  
   Compares promoted vs non-promoted observations.

2. **Regression adjustment**  
   Estimates the ATT-like effect of promotion while controlling for observed pre-treatment confounders.

3. **Propensity score weighting**  
   Reweights control observations to look more similar to promoted observations for an ATT-style comparison.

4. **Segment-level treatment effect analysis**  
   Identifies where promotions may still create positive incremental profit.

5. **Decision memo**  
   Translates the analysis into a business recommendation.

---

## Project structure

```text
decision-science-lab/
│
├── README.md
├── requirements.txt
│
├── data/
│   └── retail_promotions_synthetic.csv
│
├── notebooks/
│   └── decision_science_lab_case_study.ipynb
│
├── reports/
│   ├── decision_memo.md
│   └── figures/
│
├── docs/
│   ├── causal_assumptions.md
│   └── data_dictionary.md
│
└── src/
    └── generate_synthetic_data.py
```

---

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/generate_synthetic_data.py
jupyter notebook notebooks/decision_science_lab_case_study.ipynb
```
