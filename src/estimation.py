"""Observed-data estimators with an explicit pre-treatment feature boundary.

The ATT outcome regression fits m0(X) on controls and averages Y - m0(X)
over treated rows. Pooled OLS is retained as a historical comparison: its
treatment coefficient does not generally target ATT with heterogeneous effects.
Neither estimator is guaranteed unbiased when its nuisance model is misspecified.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ALLOWED_COVARIATES = (
    "region", "store_size", "urbanicity", "baseline_demand",
    "local_income_index", "competition_intensity", "category", "brand_tier",
    "base_price", "margin_rate", "price_elasticity", "baseline_popularity",
    "week", "month", "season", "holiday_flag", "seasonal_demand_index",
)
CATEGORICAL_COVARIATES = (
    "region", "store_size", "urbanicity", "category", "brand_tier", "season",
)
NUMERIC_COVARIATES = tuple(
    name for name in ALLOWED_COVARIATES if name not in CATEGORICAL_COVARIATES
)
BLOCKED_FEATURE_COLS = frozenset({
    "units_sold", "revenue", "gross_profit", "promo_cost", "net_profit",
    "discount_depth", "promo_type", "treatment_effect_true",
    "incremental_units_true", "incremental_profit_true", "treatment_probability",
    "estimated_propensity_score", "att_weight",
})


def _treatment_array(treatment):
    values = np.asarray(treatment, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("Treatment must be a finite one-dimensional array.")
    if not np.isin(values, [0, 1]).all() or set(values) != {0.0, 1.0}:
        raise ValueError("Treatment must be binary with both arms present.")
    return values.astype(bool)


def _weight_array(weights, size=None):
    values = np.asarray(weights, dtype=float)
    if (values.ndim != 1 or (size is not None and len(values) != size)
            or not np.isfinite(values).all() or (values < 0).any()
            or values.sum() <= 0):
        raise ValueError("Weights must be finite, nonnegative, and have positive sum.")
    return values


def effective_sample_size(weights):
    """Kish ESS for a vector of nonnegative weights; invariant to rescaling."""
    values = _weight_array(weights)
    # Rescale first to avoid squaring large, but finite, weights.
    scaled = values / values.max()
    return float(scaled.sum() ** 2 / np.square(scaled).sum())


def att_weights(treatment, propensity):
    """ATT weights: one for treated rows, e(X)/(1-e(X)) for controls.

    No trimming, stabilization or clipping is performed by this function.
    Endpoint scores are rejected instead of silently changing the estimand.
    """
    treated = _treatment_array(treatment)
    scores = np.asarray(propensity, dtype=float)
    if (scores.ndim != 1 or len(scores) != len(treated)
            or not np.isfinite(scores).all()
            or ((scores <= 0) | (scores >= 1)).any()):
        raise ValueError("Propensity scores must be finite and strictly between 0 and 1.")
    weights = np.ones(len(treated), dtype=float)
    weights[~treated] = scores[~treated] / (1 - scores[~treated])
    return weights


def balance_table(covariates, treatment, weights, clipped_weights=None):
    """Balance of numeric/one-hot covariates with a fixed unweighted scale.

    The denominator is sqrt((Var(X|T=1) + Var(X|T=0))/2), using ddof=0.
    It stays fixed before and after weighting. All dummy levels are suitable
    here, even though regression uses a reference level to reduce redundancy.
    """
    treated = _treatment_array(treatment)
    values = covariates.to_numpy(dtype=float)
    if values.ndim != 2 or len(values) != len(treated) or not np.isfinite(values).all():
        raise ValueError("Balance covariates must be a finite numeric DataFrame.")
    weights = _weight_array(weights, len(treated))
    _weight_array(weights[~treated])
    treated_mean = values[treated].mean(axis=0)
    control_mean = values[~treated].mean(axis=0)
    denominator = np.sqrt(
        (values[treated].var(axis=0, ddof=0)
         + values[~treated].var(axis=0, ddof=0)) / 2
    )

    def standardized_difference(control_average):
        difference = treated_mean - control_average
        result = np.zeros_like(difference)
        np.divide(difference, denominator, out=result, where=denominator != 0)
        # Constant in both arms: identical values mean perfect balance; distinct
        # constants reveal no support and cannot be assigned an arbitrary SMD.
        no_scale_difference = (denominator == 0) & (difference != 0)
        result[no_scale_difference] = np.sign(difference[no_scale_difference]) * np.inf
        # Floating mean/variance roundoff must not imply imbalance in a column
        # whose value is exactly the same for every observation.
        result[np.ptp(values, axis=0) == 0] = 0.0
        return result

    result = pd.DataFrame({
        "covariate": covariates.columns,
        "unweighted_pooled_sd": denominator,
        "smd_before": standardized_difference(control_mean),
        "smd_after": standardized_difference(
            np.average(values[~treated], axis=0, weights=weights[~treated])
        ),
    })
    result["abs_smd_before"] = result["smd_before"].abs()
    result["abs_smd_after"] = result["smd_after"].abs()
    if clipped_weights is not None:
        clipped = _weight_array(clipped_weights, len(treated))
        _weight_array(clipped[~treated])
        result["smd_after_clipped"] = standardized_difference(
            np.average(values[~treated], axis=0, weights=clipped[~treated])
        )
        result["abs_smd_after_clipped"] = result["smd_after_clipped"].abs()
    return result


def _weight_diagnostics(weights, prefix):
    values = np.asarray(weights)
    top_count = max(1, int(np.ceil(0.01 * len(values))))
    results = {
        f"{prefix}_p{quantile}": float(np.quantile(values, quantile / 100))
        for quantile in (50, 90, 95, 99)
    }
    results.update({
        f"{prefix}_max": float(values.max()),
        f"{prefix}_top1pct_share": float(
            np.sort(values)[-top_count:].sum() / values.sum()
        ),
        f"{prefix}_count_gt10": int((values > 10).sum()),
        f"{prefix}_count_gt50": int((values > 50).sum()),
    })
    return results


def analyze_frame(data):
    """Fit the frozen estimator specification using only permitted covariates.

    Inputs may contain simulation benchmark columns; they are never selected
    or read. The only observed response used is net_profit. Returned estimates
    are point estimates, and diagnostics are not confidence intervals.

    Raw logistic ATT weighting is primary. The historical [0.02, 0.98] score
    clipping is a separately labelled bias/variance sensitivity, not a repair
    that guarantees the original ATT target. The logistic model may be wrong.
    """
    if set(ALLOWED_COVARIATES) & BLOCKED_FEATURE_COLS:
        raise RuntimeError("Feature whitelist contains blocked variables.")
    required = list(ALLOWED_COVARIATES) + ["promotion_flag", "net_profit"]
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    observed = data.loc[:, required]
    if observed.isna().any().any():
        raise ValueError("Observed inputs contain missing values.")
    treated = _treatment_array(observed["promotion_flag"])
    y = observed["net_profit"].to_numpy(dtype=float)
    numeric = observed.loc[:, NUMERIC_COVARIATES].to_numpy(dtype=float)
    if not np.isfinite(y).all() or not np.isfinite(numeric).all():
        raise ValueError("Observed outcomes and numeric covariates must be finite.")

    X = pd.get_dummies(
        observed.loc[:, ALLOWED_COVARIATES],
        columns=list(CATEGORICAL_COVARIATES), drop_first=True, dtype=float,
    )
    X_balance = pd.get_dummies(
        observed.loc[:, ALLOWED_COVARIATES],
        columns=list(CATEGORICAL_COVARIATES), drop_first=False, dtype=float,
    )
    control_regression = LinearRegression().fit(X.loc[~treated], y[~treated])
    regression_att = float(
        (y[treated] - control_regression.predict(X.loc[treated])).mean()
    )
    # Original common-slope pooled regression, retained without calling it ATT.
    X_pooled = X.copy()
    X_pooled.insert(0, "promotion_flag", treated.astype(float))
    pooled_regression = LinearRegression().fit(X_pooled, y)

    propensity_model = make_pipeline(
        StandardScaler(),
        LogisticRegression(C=1.0, max_iter=2000, tol=1e-7, solver="lbfgs"),
    )
    propensity_model.fit(X, treated.astype(int))
    if propensity_model[-1].n_iter_.max() >= propensity_model[-1].max_iter:
        raise RuntimeError("Propensity logistic regression did not converge.")
    scores = propensity_model.predict_proba(X)[:, 1]
    weights = att_weights(treated, scores)
    clipped_scores = np.clip(scores, 0.02, 0.98)
    clipped_weights = att_weights(treated, clipped_scores)
    treated_mean = y[treated].mean()
    estimates = {
        "naive": float(treated_mean - y[~treated].mean()),
        "ols_coefficient": float(pooled_regression.coef_[0]),
        "regression_att": regression_att,
        "propensity_att": float(
            treated_mean - np.average(y[~treated], weights=weights[~treated])
        ),
        "propensity_att_clipped": float(
            treated_mean - np.average(y[~treated], weights=clipped_weights[~treated])
        ),
    }
    balance = balance_table(X_balance, treated, weights, clipped_weights)
    n_controls = int((~treated).sum())
    ess = effective_sample_size(weights[~treated])
    clipped_ess = effective_sample_size(clipped_weights[~treated])
    diagnostics = {
        "n_rows": len(data),
        "n_treated": int(treated.sum()),
        "n_controls": n_controls,
        "control_ess": ess,
        "control_ess_share": ess / n_controls,
        "clipped_control_ess": clipped_ess,
        "clipped_control_ess_share": clipped_ess / n_controls,
        "propensity_min": float(scores.min()),
        "propensity_max": float(scores.max()),
        "propensity_clipped_count": int((scores != clipped_scores).sum()),
        "propensity_clipped_share": float((scores != clipped_scores).mean()),
        "treated_outside_control_range_share": float(
            ((scores[treated] < scores[~treated].min())
             | (scores[treated] > scores[~treated].max())).mean()
        ),
        "max_abs_smd_before": float(balance["abs_smd_before"].max()),
        "max_abs_smd_after": float(balance["abs_smd_after"].max()),
        "max_abs_smd_clipped": float(balance["abs_smd_after_clipped"].max()),
        "propensity_iterations": int(propensity_model[-1].n_iter_.max()),
    }
    for arm, mask in (("treated", treated), ("control", ~treated)):
        diagnostics[f"propensity_{arm}_min"] = float(scores[mask].min())
        diagnostics[f"propensity_{arm}_max"] = float(scores[mask].max())
        for quantile in (1, 5, 50, 95, 99):
            diagnostics[f"propensity_{arm}_p{quantile:02d}"] = float(
                np.quantile(scores[mask], quantile / 100)
            )
    diagnostics.update(_weight_diagnostics(weights[~treated], "control_weight"))
    diagnostics.update(
        _weight_diagnostics(clipped_weights[~treated], "clipped_control_weight")
    )
    return {
        "estimates": estimates,
        "propensity_scores": scores,
        "weights": weights,
        "clipped_propensity_scores": clipped_scores,
        "clipped_weights": clipped_weights,
        "balance": balance,
        "diagnostics": diagnostics,
    }
