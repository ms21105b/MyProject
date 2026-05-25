#!/usr/bin/env python3
"""Run the synthetic-control quasi A/B analysis extension."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.config import DEFAULT_RAW_FILE, FIGURE_DIR, OUTPUT_DIR
from promo_retention.data import clean_transactions, load_raw_csv
from promo_retention.plotting import (
    save_scm_actual_vs_synthetic,
    save_scm_gap_path,
    save_scm_injected_lift_recovery,
    save_scm_placebo_mspe_ratio,
)
from promo_retention.synthetic_control import DEFAULT_OUTCOME, OUTCOME_COLUMNS, run_scm_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SCM quasi A/B extension.")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_RAW_FILE),
        help="Path to Kaggle CSV. Defaults to data/raw/EcommData_CSV.csv.",
    )
    parser.add_argument(
        "--treatment-start",
        default="2024-01-01",
        help="Pseudo-treatment start month, e.g. 2024-01-01.",
    )
    parser.add_argument(
        "--outcome",
        default=DEFAULT_OUTCOME,
        choices=OUTCOME_COLUMNS,
        help="SCM outcome to model.",
    )
    parser.add_argument(
        "--treatment-segment",
        default=None,
        help="Optional explicit treatment segment, e.g. 'Potential Loyalist'.",
    )
    parser.add_argument(
        "--treatment-location",
        default=None,
        help="Optional explicit treatment location, e.g. 'Alabama'.",
    )
    parser.add_argument(
        "--min-unit-customers",
        type=int,
        default=20,
        help="Minimum pre-period customers for SCM eligibility diagnostics.",
    )
    parser.add_argument(
        "--donor-scope",
        choices=["same_segment", "all"],
        default="same_segment",
        help="Use donors from the same segment or all segment-location units.",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="Write CSV/JSON outputs without generating figures.",
    )
    return parser.parse_args()


def write_scm_outputs(artifacts: dict[str, object], skip_plots: bool = False) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    artifacts["panel"].to_csv(OUTPUT_DIR / "scm_panel.csv", index=False)
    artifacts["feasibility"].to_csv(OUTPUT_DIR / "scm_feasibility_summary.csv", index=False)
    artifacts["weights"].to_csv(OUTPUT_DIR / "scm_weights.csv", index=False)
    artifacts["gap_path"].to_csv(OUTPUT_DIR / "scm_gap_path.csv", index=False)
    artifacts["placebo_summary"].to_csv(OUTPUT_DIR / "scm_placebo_summary.csv", index=False)
    artifacts["lift_summary"].to_csv(OUTPUT_DIR / "scm_injected_lift_summary.csv", index=False)
    artifacts["summary"].to_csv(OUTPUT_DIR / "scm_summary.csv", index=False)
    with (OUTPUT_DIR / "scm_run_metadata.json").open("w") as file:
        json.dump(artifacts["metadata"], file, indent=2)

    if skip_plots:
        return
    save_scm_actual_vs_synthetic(
        artifacts["gap_path"],
        FIGURE_DIR / "scm_actual_vs_synthetic.png",
    )
    save_scm_gap_path(artifacts["gap_path"], FIGURE_DIR / "scm_gap_path.png")
    save_scm_placebo_mspe_ratio(
        artifacts["placebo_summary"],
        FIGURE_DIR / "scm_placebo_mspe_ratio.png",
    )
    save_scm_injected_lift_recovery(
        artifacts["lift_summary"],
        FIGURE_DIR / "scm_injected_lift_recovery.png",
    )


def main() -> None:
    args = parse_args()
    raw = load_raw_csv(args.input)
    clean = clean_transactions(raw)
    artifacts = run_scm_workflow(
        clean,
        treatment_start=args.treatment_start,
        outcome=args.outcome,
        treatment_segment=args.treatment_segment,
        treatment_location=args.treatment_location,
        min_unit_customers=args.min_unit_customers,
        donor_scope=args.donor_scope,
    )
    write_scm_outputs(artifacts, skip_plots=args.skip_plots)
    print("SCM quasi A/B analysis complete.")
    print(f"Treated unit: {artifacts['metadata']['treated_unit']}")
    print(f"Outputs: {OUTPUT_DIR}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
