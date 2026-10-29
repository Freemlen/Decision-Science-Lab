# Validation record

Validated on 2026-10-29 using Windows and Python 3.12.7.

- Created a separate empty `.repro-venv` without system site packages and installed only `requirements.txt`. `pip check` reported no broken requirements.
- Ran `python -m unittest discover -s tests -v`: **12 tests passed**, under one second of test runtime. These check invariants/formulas and leakage boundaries, not favorable synthetic recovery thresholds.
- Ran `python -m src.run_analysis --output-dir .repro-output`: exactly the five fixed seeds, 52,000 rows each; approximately four seconds for the local run, excluding environment installation.
- Ran `python scripts/check_reproduction.py .repro-output`: **all five numeric CSV reports matched** within the declared `rtol=1e-4`, `atol=1e-5`. Solver iteration counts, runtime and image bytes are excluded from cross-platform equality.
- Executed the current notebook from a fresh kernel using `scripts/execute_notebook.py` and the optional notebook dependencies. Every code cell completed; saved tables and figures are current. The kernel uses the command's Python interpreter and is closed afterwards.
- Visually inspected all four new figures for readable labels and legends. Original figures are unchanged.
- Independently reviewed the estimand, benchmark rounding, feature boundary and interpretation. The retained propensity specification fails balance and is explicitly unsuitable for a business point recommendation.

The original generator and input CSV are unchanged. Original notebook and memo contents are preserved in their archive paths. No corporate systems or data were accessed.

The GitHub Actions workflow repeats the numerical checks on Python 3.12/Linux. The PR's check status is the authority for that run; this record's completed clean-environment claim refers to the local Windows checks above. Scientific dependencies are pinned, but this is not a complete transitive platform lock or a bit-identical image guarantee.

Reproduction of this simulator does not validate identification in real data. There are no confidence intervals, power estimates, policy-value claims or production deployment checks.
