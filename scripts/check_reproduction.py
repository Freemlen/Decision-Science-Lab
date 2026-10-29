"""Check regenerated numeric reports against the committed reference results."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
actual = Path(sys.argv[1])
reference = ROOT / "reports" / "methodology_upgrade"
for filename in (
    "estimates_by_seed.csv", "robustness_summary.csv", "diagnostics_by_seed.csv",
    "balance_by_seed.csv", "oracle_segments_seed42.csv",
):
    left = pd.read_csv(reference / filename)
    right = pd.read_csv(actual / filename)
    # Solver iteration counts can differ across BLAS/OS without changing results.
    left = left.drop(columns=["propensity_iterations"], errors="ignore")
    right = right.drop(columns=["propensity_iterations"], errors="ignore")
    pd.testing.assert_frame_equal(left, right, check_exact=False, rtol=1e-4, atol=1e-5)
    print(f"PASS {filename}")
