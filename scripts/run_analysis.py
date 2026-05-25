#!/usr/bin/env python3
"""Run the full promo-retention analysis pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.config import DEFAULT_RAW_FILE, FIGURE_DIR, OUTPUT_DIR
from promo_retention.data import clean_transactions, load_raw_csv
from promo_retention.metrics import (
    cohort_matrix,
    cohort_retention,
    monthly_kpis,
    promo_comparison,
    promo_sensitivity_summary,
    rfm_segments,
    segment_promo_matrix,
    segment_summary,
)
from promo_retention.modeling import build_inactivity_snapshot, train_inactivity_risk_model
from promo_retention.plotting import (
    save_cohort_heatmap,
    save_monthly_trend,
    save_promo_comparison,
    save_promo_sensitivity_summary,
    save_segment_matrix,
    save_scm_actual_vs_synthetic,
    save_scm_gap_path,
    save_scm_injected_lift_recovery,
    save_scm_placebo_mspe_ratio,
)
from promo_retention.synthetic_control import run_scm_workflow
from promo_retention.validation import summarize_cleaning, validate_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_RAW_FILE),
        help="Path to Kaggle CSV. Defaults to data/raw/EcommData_CSV.csv.",
    )
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Skip optional churn model training.",
    )
    parser.add_argument(
        "--include-scm",
        action="store_true",
        help="Run optional Synthetic Control quasi A/B extension.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw_csv(args.input)
    clean = clean_transactions(raw)

    validation_report = validate_dataset(clean)
    cleaning_report = summarize_cleaning(raw, clean)
    monthly = monthly_kpis(clean)
    promo = promo_comparison(clean)
    retention = cohort_retention(clean)
    retention_matrix = cohort_matrix(retention)
    rfm = rfm_segments(clean)
    latest_inactivity = build_inactivity_snapshot(clean, cutoff="2024-06-30", horizon_days=180)[
        ["customer_id", "future_inactive_180d"]
    ]
    rfm = rfm.merge(latest_inactivity, on="customer_id", how="left")
    segments = segment_summary(rfm)
    promo_sensitivity = promo_sensitivity_summary(rfm)
    segment_promo = segment_promo_matrix(rfm)

    validation_report.to_csv(OUTPUT_DIR / "validation_report.csv", index=False)
    cleaning_report.to_csv(OUTPUT_DIR / "cleaning_report.csv", index=False)
    monthly.to_csv(OUTPUT_DIR / "monthly_kpis.csv", index=False)
    promo.to_csv(OUTPUT_DIR / "promo_comparison.csv", index=False)
    retention.to_csv(OUTPUT_DIR / "cohort_retention.csv", index=False)
    retention_matrix.to_csv(OUTPUT_DIR / "cohort_retention_matrix.csv")
    rfm.to_csv(OUTPUT_DIR / "rfm_segments.csv", index=False)
    segments.to_csv(OUTPUT_DIR / "segment_summary.csv", index=False)
    promo_sensitivity.to_csv(OUTPUT_DIR / "promo_sensitivity_summary.csv", index=False)
    segment_promo.to_csv(OUTPUT_DIR / "segment_promo_matrix.csv", index=False)

    save_monthly_trend(monthly, FIGURE_DIR / "monthly_sales_promo_usage.png")
    save_cohort_heatmap(retention_matrix, FIGURE_DIR / "cohort_retention_heatmap.png")
    save_promo_comparison(promo, FIGURE_DIR / "promo_vs_no_promo.png")
    save_segment_matrix(segments, FIGURE_DIR / "segment_strategy_matrix.png")
    save_promo_sensitivity_summary(
        promo_sensitivity,
        FIGURE_DIR / "promo_sensitivity_summary.png",
    )

    if not args.skip_model:
        try:
            importance, model_metrics = train_inactivity_risk_model(clean)
            importance.to_csv(OUTPUT_DIR / "churn_time_split_feature_importance.csv", index=False)
            with (OUTPUT_DIR / "churn_time_split_metrics.json").open("w") as file:
                json.dump(model_metrics, file, indent=2)
        except Exception as exc:
            with (OUTPUT_DIR / "churn_time_split_metrics.json").open("w") as file:
                json.dump({"status": "skipped", "reason": str(exc)}, file, indent=2)
        for deprecated in ["churn_feature_importance.csv", "churn_model_metrics.json"]:
            deprecated_path = OUTPUT_DIR / deprecated
            if deprecated_path.exists():
                deprecated_path.unlink()

    if args.include_scm:
        scm = run_scm_workflow(clean)
        scm["panel"].to_csv(OUTPUT_DIR / "scm_panel.csv", index=False)
        scm["feasibility"].to_csv(OUTPUT_DIR / "scm_feasibility_summary.csv", index=False)
        scm["weights"].to_csv(OUTPUT_DIR / "scm_weights.csv", index=False)
        scm["gap_path"].to_csv(OUTPUT_DIR / "scm_gap_path.csv", index=False)
        scm["placebo_summary"].to_csv(OUTPUT_DIR / "scm_placebo_summary.csv", index=False)
        scm["lift_summary"].to_csv(OUTPUT_DIR / "scm_injected_lift_summary.csv", index=False)
        scm["summary"].to_csv(OUTPUT_DIR / "scm_summary.csv", index=False)
        with (OUTPUT_DIR / "scm_run_metadata.json").open("w") as file:
            json.dump(scm["metadata"], file, indent=2)
        save_scm_actual_vs_synthetic(scm["gap_path"], FIGURE_DIR / "scm_actual_vs_synthetic.png")
        save_scm_gap_path(scm["gap_path"], FIGURE_DIR / "scm_gap_path.png")
        save_scm_placebo_mspe_ratio(
            scm["placebo_summary"],
            FIGURE_DIR / "scm_placebo_mspe_ratio.png",
        )
        save_scm_injected_lift_recovery(
            scm["lift_summary"],
            FIGURE_DIR / "scm_injected_lift_recovery.png",
        )

    print(f"Analysis complete. Outputs: {OUTPUT_DIR}")
    print(f"Figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
