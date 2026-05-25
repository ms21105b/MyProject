from pathlib import Path
import sys
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.data import clean_transactions
from promo_retention.synthetic_control import (
    build_scm_panel,
    fit_synthetic_control,
    run_injected_lift_simulation,
    run_placebo_tests,
)


def _toy_panel() -> pd.DataFrame:
    months = pd.date_range("2023-01-01", periods=6, freq="MS")
    donor_a = [0.10, 0.12, 0.14, 0.16, 0.18, 0.20]
    donor_b = [0.20, 0.18, 0.16, 0.14, 0.12, 0.10]
    treated = [0.25 * a + 0.75 * b for a, b in zip(donor_a, donor_b)]
    rows = []
    for unit_id, location, values in [
        ("Potential Loyalist | Treated", "Treated", treated),
        ("Potential Loyalist | Donor A", "Donor A", donor_a),
        ("Potential Loyalist | Donor B", "Donor B", donor_b),
    ]:
        for month, value in zip(months, values):
            rows.append(
                {
                    "unit_id": unit_id,
                    "segment": "Potential Loyalist",
                    "location": location,
                    "purchase_month": month,
                    "active_customer_rate": value,
                    "orders_per_customer": value * 2,
                    "sales_per_customer": value * 100,
                    "promo_usage_rate": 0.1,
                }
            )
    return pd.DataFrame(rows)


def _transaction_fixture() -> pd.DataFrame:
    return clean_transactions(
        pd.DataFrame(
            [
                {
                    "customer_id": 1,
                    "purchase_date": "01.01.2023",
                    "purchase_amount": 100.0,
                    "promo_code_used": 0,
                    "subscription_status": 0,
                    "churn": 0,
                    "previous_purchases": 1,
                    "location": "Alabama",
                },
                {
                    "customer_id": 2,
                    "purchase_date": "01.02.2023",
                    "purchase_amount": 120.0,
                    "promo_code_used": 1,
                    "subscription_status": 0,
                    "churn": 0,
                    "previous_purchases": 2,
                    "location": "Alabama",
                },
                {
                    "customer_id": 99,
                    "purchase_date": "01.05.2023",
                    "purchase_amount": 9999.0,
                    "promo_code_used": 1,
                    "subscription_status": 0,
                    "churn": 0,
                    "previous_purchases": 99,
                    "location": "Alabama",
                },
            ]
        )
    )


class SyntheticControlTest(unittest.TestCase):
    def test_weights_are_convex_and_recover_toy_path(self) -> None:
        panel = _toy_panel()
        fit = fit_synthetic_control(
            panel,
            "Potential Loyalist | Treated",
            treatment_start="2023-04-01",
            outcome="active_customer_rate",
            donor_units=["Potential Loyalist | Donor A", "Potential Loyalist | Donor B"],
            predictor_columns=None,
        )

        self.assertAlmostEqual(float(fit.weights["weight"].sum()), 1.0, places=6)
        self.assertTrue((fit.weights["weight"] >= 0).all())
        self.assertLess(float(fit.summary.loc[0, "pre_rmse"]), 1e-8)
        self.assertLess(float(fit.summary.loc[0, "post_rmse"]), 1e-8)

    def test_cutoff_safe_panel_excludes_post_only_customers(self) -> None:
        clean = _transaction_fixture()
        panel, _ = build_scm_panel(clean, treatment_start="2023-04-01", min_unit_customers=1)

        self.assertEqual(int(panel[["unit_id", "unit_customers"]].drop_duplicates()["unit_customers"].sum()), 2)

    def test_placebo_summary_marks_treated_and_runs_for_donors(self) -> None:
        panel = _toy_panel()
        placebo = run_placebo_tests(
            panel,
            "Potential Loyalist | Treated",
            treatment_start="2023-04-01",
            outcome="active_customer_rate",
            donor_units=["Potential Loyalist | Donor A", "Potential Loyalist | Donor B"],
            predictor_columns=None,
        )

        self.assertEqual(len(placebo), 3)
        self.assertEqual(int(placebo["is_treated_unit"].sum()), 1)
        self.assertTrue(placebo["status"].eq("ok").all())

    def test_injected_lift_recovers_positive_direction(self) -> None:
        panel = _toy_panel()
        lift = run_injected_lift_simulation(
            panel,
            "Potential Loyalist | Treated",
            treatment_start="2023-04-01",
            outcome="active_customer_rate",
            lift_rates=(0.05, 0.10),
            donor_units=["Potential Loyalist | Donor A", "Potential Loyalist | Donor B"],
            predictor_columns=None,
        )

        self.assertTrue(lift["direction_recovered"].all())
        self.assertTrue((lift["recovered_absolute_lift"] > 0).all())


if __name__ == "__main__":
    unittest.main()
