"""Bounded five-seed audit. Run from repository root: python -m src.run_analysis."""

import argparse
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
import scipy
import threadpoolctl
from threadpoolctl import threadpool_limits

from src.estimation import analyze_frame
from src.generate_synthetic_data import generate_synthetic_data


ROOT = Path(__file__).resolve().parents[1]
# Fixed before inspecting the new estimates. Each seed redraws stores, products,
# assignment, promotion versions and outcome noise; these are not five bootstraps.
SEEDS = (42, 101, 202, 303, 404)
METHOD_LABELS = {
    "naive": "Naive difference",
    "ols_coefficient": "Pooled OLS coefficient (not ATT)",
    "regression_att": "Control regression ATT",
    "propensity_att": "Propensity ATT (raw)",
    "propensity_att_clipped": "Propensity ATT (clipped sensitivity)",
}


def synthetic_att(data):
    """Oracle evaluation only: controls have placeholder zeros, not zero effects."""
    return float(data.loc[data.promotion_flag.eq(1), "incremental_profit_true"].mean())


def summarize_errors(results):
    """Descriptive five-replication errors, not coverage or sampling inference."""
    rows = []
    for method, group in results.groupby("method", sort=False):
        error = group["error"]
        rows.append({
            "method": method, "n_seeds": len(group),
            "mean_estimate": group["estimate"].mean(),
            "estimate_sd": group["estimate"].std(ddof=1),
            "mean_error": error.mean(), "mae": error.abs().mean(),
            "rmse": np.sqrt(np.mean(error ** 2)),
            "error_sd": error.std(ddof=1),
            "min_error": error.min(), "max_error": error.max(),
        })
    return pd.DataFrame(rows)


def oracle_segments(data):
    """Descriptive simulator audit only. Never return a policy or action label."""
    treated = data.loc[data.promotion_flag.eq(1)].copy()
    # Fixed value boundaries do not split equal-valued products by row order.
    treated["margin_band"] = pd.cut(
        treated.margin_rate, [-np.inf, .35, .45, np.inf],
        labels=["margin <= 0.35", "0.35 < margin <= 0.45", "margin > 0.45"],
    )
    treated["discount_band"] = pd.cut(
        treated.discount_depth, [-np.inf, .12, .18, np.inf],
        labels=["discount <= 0.12", "0.12 < discount <= 0.18", "discount > 0.18"],
    )
    return treated.groupby(["margin_band", "discount_band"], observed=True).agg(
        n_promoted=("promotion_flag", "size"),
        observed_mean_profit=("net_profit", "mean"),
        oracle_mean_expected_effect=("incremental_profit_true", "mean"),
    ).reset_index()


def save_figures(results, first, output):
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    seed42 = results[results.seed.eq(SEEDS[0])]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh([METHOD_LABELS[m] for m in seed42.method], seed42.estimate,
            color=["#64748b", "#94a3b8", "#2563eb", "#0d9488", "#d97706"])
    ax.axvline(seed42.true_att.iloc[0], color="#be123c", linestyle="--", label="Oracle expected ATT")
    ax.axvline(0, color="#334155", linewidth=.8)
    ax.invert_yaxis()
    ax.set(xlabel="Profit per promoted store-product-week (synthetic monetary units)",
           title="Seed 42: target-aligned estimates and historical comparisons")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(figures / "estimate_comparison.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = ["#64748b", "#94a3b8", "#2563eb", "#0d9488", "#d97706"]
    for color, (method, group) in zip(colors, results.groupby("method", sort=False)):
        ax.plot(range(len(SEEDS)), group.error, marker="o", color=color, label=METHOD_LABELS[method])
    ax.axhline(0, color="#334155", linewidth=.8)
    ax.set(xticks=range(len(SEEDS)), xticklabels=SEEDS, xlabel="Independent generator seed",
           ylabel="Estimate minus that seed's expected ATT", title="Five fixed replications: errors, not confidence intervals")
    ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(.5, -.16), ncol=2)
    fig.tight_layout()
    fig.savefig(figures / "robustness_errors.png", dpi=150)
    plt.close(fig)

    treatment = first["treatment"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for arm, label, color in [(0, "Controls", "#64748b"), (1, "Promoted", "#2563eb")]:
        axes[0].hist(first["propensity_scores"][treatment == arm], bins=np.linspace(0, 1, 31),
                     density=True, alpha=.55, label=label, color=color)
    axes[0].set(title="Seed 42: estimated propensity overlap", xlabel="Raw fitted propensity", ylabel="Density")
    axes[0].legend(frameon=False)
    weights = first["weights"][treatment == 0]
    axes[1].hist(weights, bins=np.geomspace(weights.min(), weights.max(), 35), color="#0d9488")
    axes[1].set_xscale("log")
    axes[1].set(title="Control weights: unmodified fitted odds", xlabel="ATT weight (log scale)", ylabel="Control rows")
    fig.tight_layout()
    fig.savefig(figures / "overlap_weights.png", dpi=150)
    plt.close(fig)

    balance = first["balance"].sort_values("smd_before")
    fig, ax = plt.subplots(figsize=(9, max(7, len(balance) * .24)))
    for col, label, color in [("smd_before", "Before", "#64748b"),
                              ("smd_after", "Raw ATT weights", "#0d9488"),
                              ("smd_after_clipped", "Clipped sensitivity", "#d97706")]:
        ax.scatter(balance[col].abs(), np.arange(len(balance)), label=label, color=color, s=22)
    ax.axvline(.1, color="#334155", linestyle="--", linewidth=.8)
    ax.set(yticks=np.arange(len(balance)), yticklabels=balance.covariate,
           xlabel="Absolute SMD (same unweighted pooled SD for every comparison)",
           title="Seed 42: balance on all baseline covariates and category levels")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(figures / "covariate_balance.png", dpi=150)
    plt.close(fig)


def run_study(output=ROOT / "reports" / "methodology_upgrade"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    start = perf_counter()
    estimates, diagnostics, balances = [], [], []
    first = None
    # Avoid machine-dependent oversubscription on a small linear-model audit.
    with threadpool_limits(limits=1):
        for seed in SEEDS:
            data = generate_synthetic_data(seed)
            # The estimator sees neither oracle columns nor promotion mechanics.
            observed = data.drop(columns=[
                "treatment_probability", "treatment_effect_true", "incremental_units_true",
                "incremental_profit_true", "promo_type", "discount_depth", "promo_cost",
                "units_sold", "revenue", "gross_profit",
            ])
            result = analyze_frame(observed)
            # Oracle evaluation happens only AFTER all estimation for this seed.
            truth = synthetic_att(data)
            for method, estimate in result["estimates"].items():
                estimates.append({"seed": seed, "method": method, "estimate": estimate,
                                  "true_att": truth, "error": estimate - truth,
                                  "absolute_error": abs(estimate - truth)})
            diagnostics.append({"seed": seed, **result["diagnostics"]})
            balances.append(result["balance"].assign(seed=seed))
            if seed == SEEDS[0]:
                first = {**result, "treatment": data.promotion_flag.to_numpy()}
                oracle_segments(data).to_csv(output / "oracle_segments_seed42.csv", index=False)
            print(f"Completed seed {seed}: {len(data):,} rows", flush=True)
    results = pd.DataFrame(estimates)
    results.to_csv(output / "estimates_by_seed.csv", index=False)
    summarize_errors(results).to_csv(output / "robustness_summary.csv", index=False)
    pd.DataFrame(diagnostics).to_csv(output / "diagnostics_by_seed.csv", index=False)
    pd.concat(balances, ignore_index=True).to_csv(output / "balance_by_seed.csv", index=False)
    save_figures(results, first, output)
    sources = ["src/generate_synthetic_data.py", "src/estimation.py", "src/run_analysis.py"]
    manifest = {
        "seeds": list(SEEDS), "rows_per_seed": 52000,
        "python": platform.python_version(), "numpy": np.__version__,
        "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
        "matplotlib": matplotlib.__version__,
        "scipy": scipy.__version__, "threadpoolctl": threadpoolctl.__version__,
        "source_hash_convention": "UTF-8 text with LF newlines on every platform",
        "source_sha256": {
            p: hashlib.sha256((ROOT / p).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            for p in sources
        },
        "specification": "Fixed main effects; no model or seed selection against oracle truth",
        "benchmark": "Mean expected profit effect before intermediate cashflow rounding, for realized promoted rows and versions; stored to cents",
        "elapsed_seconds": round(perf_counter() - start, 2),
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    display_path = output.relative_to(ROOT) if output.is_relative_to(ROOT) else output
    print(f"Saved audit to {display_path} in {manifest['elapsed_seconds']} seconds", flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "methodology_upgrade")
    args = parser.parse_args()
    run_study(args.output_dir)
