"""Small regression tests for estimands, leakage guards, and the synthetic DGP.

Run from the repository root with ``python -m unittest discover -s tests -v``.
These tests check formulas and invariants, not proximity to a favorable seed's
ground truth or a causal guarantee for real observational data.
"""

import unittest

import numpy as np
import pandas as pd

from src.generate_synthetic_data import generate_synthetic_data
from src.estimation import (
    CATEGORICAL_COVARIATES,
    analyze_frame,
    att_weights,
    balance_table,
    effective_sample_size,
)
from src.run_analysis import summarize_errors, synthetic_att


ORACLE_AND_POST_TREATMENT = [
    "treatment_probability",
    "treatment_effect_true",
    "incremental_units_true",
    "incremental_profit_true",
    "discount_depth",
    "promo_type",
    "units_sold",
    "revenue",
    "gross_profit",
    "promo_cost",
    "estimated_propensity_score",
    "att_weight",
]


class GeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate_synthetic_data(seed=42)

    def test_seed_determinism_and_independence(self):
        pd.testing.assert_frame_equal(self.data, generate_synthetic_data(seed=42))
        other_seed = generate_synthetic_data(seed=43)
        self.assertFalse(self.data.equals(other_seed))
        self.assertFalse(
            np.array_equal(self.data["promotion_flag"], other_seed["promotion_flag"])
        )

    def test_panel_and_oracle_invariants(self):
        data = self.data
        self.assertEqual(len(data), 50 * 20 * 52)
        self.assertFalse(data.duplicated(["store_id", "product_id", "week"]).any())
        self.assertEqual(set(data["promotion_flag"].unique()), {0, 1})
        self.assertTrue(data["treatment_probability"].between(0.03, 0.88).all())
        controls = data["promotion_flag"].eq(0)
        for column in (
            "treatment_effect_true", "incremental_units_true", "incremental_profit_true"
        ):
            self.assertTrue(data.loc[controls, column].eq(0).all(), column)
        self.assertTrue(data.loc[controls, "discount_depth"].eq(0).all())
        self.assertTrue(data.loc[controls, "promo_type"].eq("none").all())

    def test_oracle_profit_matches_independent_mean_formula(self):
        """Reconstruct expected profit from primitives, including DGP rounding.

        The benchmark is a mean-outcome contrast for realized promotion versions
        among treated rows. It does not contain the sampled Poisson outcome noise.
        """
        data = self.data
        treated = data["promotion_flag"].to_numpy()
        demand_z = (
            (data["baseline_demand"] - data["baseline_demand"].mean())
            / data["baseline_demand"].std(ddof=1)
        )
        income_factor = np.where(
            data["brand_tier"].eq("premium"),
            1 + (data["local_income_index"] - 100) / 450,
            1 - (data["local_income_index"] - 100) / 900,
        )
        no_promo_mean = np.maximum(
            1,
            data["baseline_demand"]
            * data["baseline_popularity"]
            * data["seasonal_demand_index"]
            * income_factor
            * (1 - 0.16 * data["competition_intensity"])
            * (data["base_price"] / data["base_price"].median()) ** -0.12,
        )
        category_lift = data["category"].map({
            "beverages": 0.10,
            "snacks": 0.09,
            "household": -0.02,
            "personal_care": 0.05,
            "frozen_food": 0.03,
        })
        lift = np.clip(
            0.050
            + 1.60 * data["price_elasticity"].abs() * data["discount_depth"]
            + category_lift
            + 0.25 * (data["margin_rate"] - data["margin_rate"].mean())
            + 0.08 * demand_z,
            -0.03,
            0.75,
        )
        incremental_units = np.round(no_promo_mean * lift * treated, 2)
        np.testing.assert_allclose(data["incremental_units_true"], incremental_units)
        np.testing.assert_allclose(data["treatment_effect_true"], np.round(lift * treated, 4))

        promoted_units_mean = no_promo_mean + incremental_units
        fixed_cost = data["promo_type"].map({
            "none": 0.0, "display": 7.0, "coupon": 4.0, "price_cut": 3.0
        })
        variable_rate = data["promo_type"].map({
            "none": 0.0, "display": 0.006, "coupon": 0.014, "price_cut": 0.006
        })
        # Keep the generator's unrounded expected revenue and cost convention.
        promoted_profit_mean = (
            promoted_units_mean
            * (data["base_price"] * (1 - data["discount_depth"])
               - data["base_price"] * (1 - data["margin_rate"]))
            - treated * (fixed_cost + promoted_units_mean * data["base_price"] * variable_rate)
        )
        no_promo_profit_mean = no_promo_mean * data["base_price"] * data["margin_rate"]
        expected_oracle = np.round(treated * (promoted_profit_mean - no_promo_profit_mean), 2)
        np.testing.assert_allclose(data["incremental_profit_true"], expected_oracle, atol=1e-10)
        expected_att = expected_oracle[treated == 1].mean()
        self.assertAlmostEqual(synthetic_att(data), expected_att)
        self.assertAlmostEqual(
            data.loc[treated == 1, "incremental_profit_true"].mean(), expected_att
        )
        self.assertNotAlmostEqual(data["incremental_profit_true"].mean(), expected_att)

    def test_benchmark_uses_treated_rows_only(self):
        data = self.data.copy()
        expected = data.loc[data["promotion_flag"].eq(1), "incremental_profit_true"].mean()
        data.loc[data["promotion_flag"].eq(0), "incremental_profit_true"] = 1e9
        self.assertAlmostEqual(synthetic_att(data), expected)


def heterogeneous_fixture():
    """Two strata with common support, exact linear Y(0), and different effects.

    Treatment rates are 20% and 80%; the ATT is 0.2*1 + 0.8*9 = 7.4.
    The pooled additive OLS coefficient weights both strata equally and is 5.0.
    """
    x = np.repeat([0.0, 1.0], 100)
    treatment = np.concatenate([np.ones(20), np.zeros(80), np.ones(80), np.zeros(20)])
    data = pd.DataFrame({
        "baseline_demand": 10 + 10 * x,
        "local_income_index": 100.0,
        "competition_intensity": 0.5,
        "base_price": 4.0,
        "margin_rate": 0.4,
        "price_elasticity": -1.2,
        "baseline_popularity": 1.0,
        "holiday_flag": 0,
        "seasonal_demand_index": 1.0,
        "week": 1,
        "month": 1,
        "region": "West",
        "store_size": "medium",
        "urbanicity": "suburban",
        "category": "snacks",
        "brand_tier": "mainstream",
        "season": "winter",
        "store_id": "S001",
        "product_id": "P001",
        "promotion_flag": treatment.astype(int),
        "net_profit": 10 + 2 * x + treatment * (1 + 8 * x),
    })
    return data


class EstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = heterogeneous_fixture()
        cls.result = analyze_frame(cls.data)

    def test_att_standardization_is_not_pooled_treatment_coefficient(self):
        estimates = self.result["estimates"]
        self.assertAlmostEqual(estimates["regression_att"], 7.4, places=8)
        self.assertAlmostEqual(estimates["ols_coefficient"], 5.0, places=8)
        self.assertAlmostEqual(estimates["naive"], 8.6, places=8)

    def test_oracle_and_post_treatment_columns_cannot_change_estimates(self):
        contaminated = self.data.copy()
        rng = np.random.default_rng(2026)
        for column in ORACLE_AND_POST_TREATMENT:
            contaminated[column] = (
                "leakage_sentinel" if column == "promo_type"
                else rng.normal(size=len(contaminated)) * 1e10
            )
        result = analyze_frame(contaminated)
        self.assertEqual(result["estimates"], self.result["estimates"])
        np.testing.assert_array_equal(result["propensity_scores"], self.result["propensity_scores"])
        np.testing.assert_array_equal(result["weights"], self.result["weights"])
        pd.testing.assert_frame_equal(result["balance"], self.result["balance"])

    def test_att_odds_weights_and_normalized_estimate(self):
        treatment = np.array([1, 0, 1, 0])
        propensity = np.array([0.8, 0.2, 0.4, 0.75])
        np.testing.assert_allclose(att_weights(treatment, propensity), [1, 0.25, 1, 3])
        observed_treatment = self.data["promotion_flag"].to_numpy().astype(bool)
        outcome = self.data["net_profit"].to_numpy()
        expected = outcome[observed_treatment].mean() - np.average(
            outcome[~observed_treatment], weights=self.result["weights"][~observed_treatment]
        )
        self.assertAlmostEqual(self.result["estimates"]["propensity_att"], expected)

    def test_ess_is_scale_invariant_and_counts_equal_weights(self):
        weights = np.array([1.0, 2.0, 5.0, 8.0])
        expected = weights.sum() ** 2 / np.square(weights).sum()
        self.assertAlmostEqual(effective_sample_size(weights), expected)
        self.assertAlmostEqual(effective_sample_size(17 * weights), expected)
        self.assertAlmostEqual(effective_sample_size(np.ones(9)), 9.0)

    def test_smd_uses_fixed_unweighted_denominator(self):
        covariates = pd.DataFrame({"x": [0.0, 2.0, 6.0, 4.0, 6.0, 8.0]})
        treatment = np.array([0, 0, 0, 1, 1, 1])
        weights = np.array([1.0, 1.0, 8.0, 1.0, 1.0, 1.0])
        row = balance_table(covariates, treatment, weights).iloc[0]
        x0 = covariates.loc[treatment == 0, "x"].to_numpy()
        x1 = covariates.loc[treatment == 1, "x"].to_numpy()
        denominator = np.sqrt((x0.var(ddof=0) + x1.var(ddof=0)) / 2)
        self.assertAlmostEqual(row["unweighted_pooled_sd"], denominator)
        self.assertAlmostEqual(row["smd_before"], (x1.mean() - x0.mean()) / denominator)
        self.assertAlmostEqual(
            row["smd_after"],
            (x1.mean() - np.average(x0, weights=weights[treatment == 0])) / denominator,
        )

    def test_balance_includes_every_categorical_level(self):
        data = self.data.copy()
        for column in CATEGORICAL_COVARIATES:
            data[column] = np.repeat(["reference", "alternative"], len(data) // 2)
        balance_columns = set(analyze_frame(data)["balance"]["covariate"])
        expected = {
            f"{column}_{level}"
            for column in CATEGORICAL_COVARIATES
            for level in ("reference", "alternative")
        }
        self.assertTrue(expected.issubset(balance_columns), expected - balance_columns)

    def test_invalid_treatment_is_rejected(self):
        for treatment in (np.zeros(len(self.data)), np.ones(len(self.data)),
                          np.full(len(self.data), 2),
                          np.where(self.data["promotion_flag"].eq(1), 2, 0)):
            invalid = self.data.assign(promotion_flag=treatment)
            with self.subTest(treatment_values=np.unique(treatment)):
                with self.assertRaises(ValueError):
                    analyze_frame(invalid)

    def test_error_summary_reports_error_variability(self):
        results = pd.DataFrame({
            "method": ["fixture"] * 5,
            "estimate": [5.0, 5.0, 5.0, 5.0, 5.0],
            "error": [-2.0, -1.0, 0.0, 1.0, 2.0],
        })
        summary = summarize_errors(results).iloc[0]
        self.assertEqual(summary["n_seeds"], 5)
        self.assertEqual(summary["mean_error"], 0)
        self.assertAlmostEqual(summary["mae"], 1.2)
        self.assertAlmostEqual(summary["rmse"], np.sqrt(2.0))
        self.assertAlmostEqual(summary["error_sd"], np.sqrt(2.5))
        self.assertEqual(summary["estimate_sd"], 0)


if __name__ == "__main__":
    unittest.main()
