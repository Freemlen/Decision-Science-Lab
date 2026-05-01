"""Generate synthetic retail promotion data with known causal ground truth.

The data-generating process intentionally assigns promotions non-randomly.
Promotions are more likely in high-demand stores, popular products, seasonal
weeks, holidays, and strategic categories. This creates selection bias: promoted
rows tend to look better even before any causal promotion effect is added.
"""

from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
N_STORES = 50
N_PRODUCTS = 20
N_WEEKS = 52


def sigmoid(x: pd.Series) -> pd.Series:
    """Convert a linear score into a probability."""
    return 1 / (1 + np.exp(-x))


def build_store_table(rng: np.random.Generator) -> pd.DataFrame:
    """Create store-level confounders that affect treatment and outcomes."""
    stores = pd.DataFrame(
        {
            "store_id": [f"S{i:03d}" for i in range(1, N_STORES + 1)],
            "region": rng.choice(
                ["Northeast", "South", "Midwest", "West"],
                size=N_STORES,
                p=[0.22, 0.32, 0.24, 0.22],
            ),
            "store_size": rng.choice(
                ["small", "medium", "large"],
                size=N_STORES,
                p=[0.34, 0.46, 0.20],
            ),
            "urbanicity": rng.choice(
                ["rural", "suburban", "urban"],
                size=N_STORES,
                p=[0.24, 0.42, 0.34],
            ),
        }
    )

    size_factor = stores["store_size"].map({"small": 0.78, "medium": 1.00, "large": 1.36})
    urban_factor = stores["urbanicity"].map({"rural": 0.86, "suburban": 1.00, "urban": 1.16})
    region_factor = stores["region"].map(
        {"Northeast": 1.02, "South": 1.05, "Midwest": 0.96, "West": 1.00}
    )

    stores["baseline_demand"] = (
        rng.lognormal(mean=np.log(43), sigma=0.24, size=N_STORES)
        * size_factor
        * urban_factor
        * region_factor
    ).round(2)

    stores["local_income_index"] = (
        rng.normal(100, 10, size=N_STORES)
        + stores["urbanicity"].map({"rural": -7, "suburban": 1, "urban": 8})
        + stores["region"].map({"Northeast": 4, "South": -2, "Midwest": -1, "West": 3})
    ).round(1)

    stores["competition_intensity"] = np.clip(
        rng.normal(0.50, 0.18, size=N_STORES)
        + stores["urbanicity"].map({"rural": -0.10, "suburban": 0.02, "urban": 0.12}),
        0.05,
        0.95,
    ).round(2)

    return stores


def build_product_table(rng: np.random.Generator) -> pd.DataFrame:
    """Create product attributes that drive demand, promotion targeting, and profit."""
    category_params = {
        "beverages": {"price": 3.10, "margin": 0.42, "elasticity": -1.65, "popularity": 1.20},
        "snacks": {"price": 3.60, "margin": 0.38, "elasticity": -1.45, "popularity": 1.25},
        "household": {"price": 8.40, "margin": 0.30, "elasticity": -0.85, "popularity": 0.78},
        "personal_care": {"price": 6.80, "margin": 0.45, "elasticity": -1.05, "popularity": 0.82},
        "frozen_food": {"price": 5.30, "margin": 0.34, "elasticity": -1.25, "popularity": 0.95},
    }
    brand_factor = {"value": 0.82, "mainstream": 1.00, "premium": 1.30}
    brand_margin = {"value": -0.04, "mainstream": 0.00, "premium": 0.06}
    brand_popularity = {"value": 1.06, "mainstream": 1.00, "premium": 0.86}

    products = pd.DataFrame(
        {
            "product_id": [f"P{i:03d}" for i in range(1, N_PRODUCTS + 1)],
            "category": rng.choice(
                list(category_params),
                size=N_PRODUCTS,
                p=[0.24, 0.24, 0.18, 0.16, 0.18],
            ),
            "brand_tier": rng.choice(
                ["value", "mainstream", "premium"],
                size=N_PRODUCTS,
                p=[0.28, 0.52, 0.20],
            ),
        }
    )

    products["base_price"] = [
        category_params[row.category]["price"]
        * brand_factor[row.brand_tier]
        * rng.lognormal(mean=0, sigma=0.08)
        for row in products.itertuples()
    ]
    products["margin_rate"] = [
        np.clip(
            category_params[row.category]["margin"]
            + brand_margin[row.brand_tier]
            + rng.normal(0, 0.025),
            0.18,
            0.58,
        )
        for row in products.itertuples()
    ]
    products["price_elasticity"] = [
        category_params[row.category]["elasticity"] + rng.normal(0, 0.12)
        for row in products.itertuples()
    ]
    products["baseline_popularity"] = [
        category_params[row.category]["popularity"]
        * brand_popularity[row.brand_tier]
        * rng.lognormal(mean=0, sigma=0.18)
        for row in products.itertuples()
    ]

    products["base_price"] = products["base_price"].round(2)
    products["margin_rate"] = products["margin_rate"].round(3)
    products["price_elasticity"] = products["price_elasticity"].round(3)
    products["baseline_popularity"] = products["baseline_popularity"].round(3)

    return products


def build_time_table() -> pd.DataFrame:
    """Create week-level seasonality and holiday demand shocks."""
    weeks = pd.DataFrame({"week": np.arange(1, N_WEEKS + 1)})
    weeks["month"] = np.ceil(weeks["week"] / (N_WEEKS / 12)).clip(1, 12).astype(int)

    weeks["season"] = np.select(
        [
            weeks["month"].isin([12, 1, 2]),
            weeks["month"].isin([3, 4, 5]),
            weeks["month"].isin([6, 7, 8]),
        ],
        ["winter", "spring", "summer"],
        default="fall",
    )

    holiday_weeks = {1, 26, 27, 47, 48, 49, 50, 51, 52}
    weeks["holiday_flag"] = weeks["week"].isin(holiday_weeks).astype(int)

    season_base = weeks["season"].map({"winter": 1.05, "spring": 0.98, "summer": 1.07, "fall": 1.00})
    annual_cycle = 0.05 * np.sin(2 * np.pi * (weeks["week"] - 1) / N_WEEKS)
    weeks["seasonal_demand_index"] = (season_base + annual_cycle + 0.16 * weeks["holiday_flag"]).round(3)

    return weeks


def generate_synthetic_data(seed: int = SEED) -> pd.DataFrame:
    """Generate the full store x product x week panel."""
    rng = np.random.default_rng(seed)

    stores = build_store_table(rng)
    products = build_product_table(rng)
    weeks = build_time_table()

    data = stores.merge(products, how="cross").merge(weeks, how="cross")

    # Demand before any promotion effect. These same variables also influence
    # promotion assignment, so they are confounders by construction.
    income_fit = np.where(
        data["brand_tier"].eq("premium"),
        1 + (data["local_income_index"] - 100) / 450,
        1 - (data["local_income_index"] - 100) / 900,
    )
    competition_drag = 1 - 0.16 * data["competition_intensity"]
    base_price_drag = np.power(data["base_price"] / data["base_price"].median(), -0.12)

    expected_units_no_promo = (
        data["baseline_demand"]
        * data["baseline_popularity"]
        * data["seasonal_demand_index"]
        * income_fit
        * competition_drag
        * base_price_drag
    ).clip(lower=1.0)

    # Non-random promotion assignment. Managers favor rows that already have
    # stronger demand signals, plus strategic categories and holiday periods.
    strategic_category = data["category"].isin(["beverages", "snacks", "personal_care"]).astype(int)
    demand_z = (data["baseline_demand"] - data["baseline_demand"].mean()) / data["baseline_demand"].std()
    popularity_z = (
        data["baseline_popularity"] - data["baseline_popularity"].mean()
    ) / data["baseline_popularity"].std()
    seasonal_z = (
        data["seasonal_demand_index"] - data["seasonal_demand_index"].mean()
    ) / data["seasonal_demand_index"].std()

    assignment_score = (
        -2.05
        + 1.10 * demand_z
        + 1.30 * popularity_z
        + 0.65 * seasonal_z
        + 1.00 * data["holiday_flag"]
        + 0.80 * strategic_category
        + 0.20 * data["competition_intensity"]
    )
    data["treatment_probability"] = sigmoid(assignment_score).clip(0.03, 0.88)
    data["promotion_flag"] = rng.binomial(1, data["treatment_probability"]).astype(int)

    promoted = data["promotion_flag"].eq(1)
    promo_type_choices = np.array(["display", "coupon", "price_cut"])
    promo_type_probs = np.array([0.30, 0.34, 0.36])
    data["promo_type"] = "none"
    data.loc[promoted, "promo_type"] = rng.choice(
        promo_type_choices, size=promoted.sum(), p=promo_type_probs
    )

    discount = np.zeros(len(data))
    display = data["promo_type"].eq("display").to_numpy()
    coupon = data["promo_type"].eq("coupon").to_numpy()
    price_cut = data["promo_type"].eq("price_cut").to_numpy()
    discount[display] = rng.uniform(0.05, 0.12, size=display.sum())
    discount[coupon] = rng.uniform(0.08, 0.18, size=coupon.sum())
    discount[price_cut] = rng.uniform(0.12, 0.26, size=price_cut.sum())
    data["discount_depth"] = discount.round(3)

    # The true unit lift varies by elasticity, margin, discount, category, and
    # store demand. Some promotions lift volume but still destroy net profit.
    category_lift = data["category"].map(
        {
            "beverages": 0.10,
            "snacks": 0.09,
            "household": -0.02,
            "personal_care": 0.05,
            "frozen_food": 0.03,
        }
    )
    margin_lift = 0.25 * (data["margin_rate"] - data["margin_rate"].mean())
    demand_lift = 0.08 * demand_z
    elasticity_lift = data["price_elasticity"].abs() * data["discount_depth"] * 1.60

    true_lift = (
        0.050
        + elasticity_lift
        + category_lift
        + margin_lift
        + demand_lift
    ).clip(lower=-0.03, upper=0.75)
    data["treatment_effect_true"] = (true_lift * data["promotion_flag"]).round(4)
    data["incremental_units_true"] = (
        expected_units_no_promo * true_lift * data["promotion_flag"]
    ).round(2)

    observed_units_mean = expected_units_no_promo + data["incremental_units_true"]
    data["units_sold"] = rng.poisson(observed_units_mean).astype(int)

    effective_price = data["base_price"] * (1 - data["discount_depth"])
    unit_cost = data["base_price"] * (1 - data["margin_rate"])

    data["revenue"] = (data["units_sold"] * effective_price).round(2)
    data["gross_profit"] = (data["revenue"] - data["units_sold"] * unit_cost).round(2)

    promo_fixed_cost = data["promo_type"].map({"none": 0.0, "display": 7.0, "coupon": 4.0, "price_cut": 3.0})
    promo_variable_rate = data["promo_type"].map(
        {"none": 0.0, "display": 0.006, "coupon": 0.014, "price_cut": 0.006}
    )
    data["promo_cost"] = (
        data["promotion_flag"]
        * (promo_fixed_cost + data["units_sold"] * data["base_price"] * promo_variable_rate)
    ).round(2)
    data["net_profit"] = (data["gross_profit"] - data["promo_cost"]).round(2)

    control_profit_true = expected_units_no_promo * data["base_price"] * data["margin_rate"]
    promo_units_true = expected_units_no_promo + data["incremental_units_true"]
    promo_gross_profit_true = promo_units_true * (effective_price - unit_cost)
    promo_cost_true = data["promotion_flag"] * (
        promo_fixed_cost + promo_units_true * data["base_price"] * promo_variable_rate
    )
    data["incremental_profit_true"] = (
        data["promotion_flag"] * (promo_gross_profit_true - promo_cost_true - control_profit_true)
    ).round(2)

    data["treatment_probability"] = data["treatment_probability"].round(4)

    column_order = [
        "store_id",
        "product_id",
        "week",
        "region",
        "store_size",
        "urbanicity",
        "baseline_demand",
        "local_income_index",
        "competition_intensity",
        "category",
        "brand_tier",
        "base_price",
        "margin_rate",
        "price_elasticity",
        "baseline_popularity",
        "month",
        "season",
        "holiday_flag",
        "seasonal_demand_index",
        "promotion_flag",
        "discount_depth",
        "promo_type",
        "treatment_probability",
        "units_sold",
        "revenue",
        "gross_profit",
        "promo_cost",
        "net_profit",
        "treatment_effect_true",
        "incremental_units_true",
        "incremental_profit_true",
    ]

    return data[column_order]


def main() -> None:
    output_path = Path(__file__).resolve().parents[1] / "data" / "retail_promotions_synthetic.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = generate_synthetic_data()
    data.to_csv(output_path, index=False)

    print(f"Saved synthetic data to: {output_path}")
    print(f"Dataset shape: {data.shape}")
    print(f"Promotion rate: {data['promotion_flag'].mean():.3f}")
    print("\nAverage net_profit by promotion_flag:")
    print(data.groupby("promotion_flag")["net_profit"].mean().round(2))
    print("\nAverage true incremental_profit_true by promotion_flag:")
    print(data.groupby("promotion_flag")["incremental_profit_true"].mean().round(2))


if __name__ == "__main__":
    main()
