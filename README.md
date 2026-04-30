# Decision Science Lab: Causal Analytics for Retail Promotions

A compact portfolio case study demonstrating causal inference, experimentation thinking, and decision-oriented analytics on synthetic retail promotion data.

## 1. Business decision

A retailer runs promotions across stores and products. Sales often look higher during promotions, but the key business question is:

**Should the retailer continue, stop, or target retail promotions?**

The goal is not only to estimate whether promotions increase sales, but to understand whether they create **incremental net profit**.

## 2. Why naive analysis is misleading

A simple comparison between promoted and non-promoted observations can be biased because promotions are not assigned randomly.

Promotions are more likely to be launched for:

- high-demand stores;
- popular products;
- seasonal periods;
- strategically important categories;
- situations where managers already expect higher sales.

Because of this, promoted observations may have higher sales even without the promotion.

The project demonstrates how naive uplift can overestimate the true business impact.

## 3. Project goal

This project uses synthetic retail data with known ground truth to compare:

- naive promotion effect estimates;
- causal estimates adjusted for confounding;
- true synthetic treatment effects.

The final output is a business recommendation about where promotions should continue, where they should be limited, and how a better experiment could be designed.

## 4. Unit of analysis

The unit of observation is:

**store × product × week**

Each row represents one product in one store during one week.

## 5. Treatment

The treatment is:

**promotion_flag**

It indicates whether a product-store-week was exposed to a promotion.

Promotion assignment is intentionally non-random to simulate realistic selection bias.

## 6. Primary outcome

The primary business outcome is:

**incremental net profit**

Supporting metrics include:

- units sold;
- revenue;
- gross profit;
- net profit;
- true treatment effect;
- estimated treatment effect.

## 7. MVP methods

The first version of the project includes:

1. Naive promoted vs non-promoted comparison
2. Regression adjustment
3. Propensity score weighting
4. Segment-level treatment effect analysis
5. Decision memo with business recommendation

## 8. Expected final recommendation

The final recommendation will answer:

- where promotions create incremental profit;
- where promotions mostly subsidize existing demand;
- which product-store segments should be targeted;
- what kind of randomized experiment should be run next.

## 9. Scope

This is a compact portfolio case study, not a production ML system.

Included:

- synthetic data generation;
- causal assumptions;
- baseline analysis;
- causal effect estimation;
- business interpretation;
- decision memo.

Not included in v1:

- production ML pipeline;
- real customer data;
- large dashboard;
- MLflow / Airflow / feature store;
- causal forests / Double ML / bandits;
- full retail demand simulation.

## 10. AI-augmented workflow

AI is used as an analytical assistant for:

- ideation;
- code drafting;
- documentation;
- assumption stress-testing;
- review;
- portfolio packaging.

Final causal assumptions, method selection, interpretation, and business recommendations are owned by the analyst.