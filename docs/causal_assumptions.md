# Causal Assumptions

## Business question

Should the retailer continue, stop, or target retail promotions?

The goal is to estimate whether promotions create incremental net profit, not only whether sales are higher during promotion periods.

## Treatment

The treatment is:

**promotion_flag**

It indicates whether a given store-product-week was exposed to a promotion.

## Outcome and estimand

The observed outcome is:

**net_profit**

This is the observed gross profit after promotion cost.

The causal estimand is:

**ATT-like incremental effect of promotion on net_profit among promoted rows**

Incremental net profit is a causal contrast between observed promoted profit and the counterfactual profit that would have occurred without promotion. It is not directly observed in real business data.

Supporting outcomes:

- units sold
- revenue
- gross profit

## Why naive analysis is biased

Promotions are not assigned randomly.

In a realistic retail setting, promotions are more likely to be launched for:

- stores with higher baseline demand;
- popular products;
- seasonal periods;
- holidays;
- strategic categories;
- cases where managers already expect higher sales.

Because of this, promoted observations may have higher sales even without the promotion.

A simple promoted vs non-promoted comparison can therefore overestimate the true effect of promotions.

## Main confounders

The main observed confounders are:

- store baseline demand
- product popularity
- seasonality
- holiday flag
- product category
- store size
- local income index
- competition intensity
- brand tier
- price elasticity

## Identification assumption

The main identification assumption is:

**Conditional on observed store, product, and time characteristics, promotion assignment is treated as as-good-as-random.**

This means that after controlling for these variables, promoted and non-promoted observations are assumed to be comparable.

## Synthetic ground truth

Because the dataset is synthetic, the true synthetic ATT among promoted rows is known.

This allows the project to compare:

- naive effect estimate;
- regression-adjusted estimate;
- propensity score weighted estimate;
- true synthetic ATT among promoted rows.

## Main limitation

In real-world data, unobserved manager expectations, competitor activity, stockouts, and substitution effects could still bias the estimate.

These are intentionally excluded from the MVP scope.
