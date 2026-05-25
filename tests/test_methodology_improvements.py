from pathlib import Path
import sys
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.data import clean_transactions
from promo_retention.metrics import (
    cohort_retention,
    promo_sensitivity_summary,
    rfm_segments,
)
from promo_retention.modeling import build_inactivity_snapshot


def _fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "customer_id": 1,
                "purchase_date": "01.01.2023",
                "purchase_amount": "10,5",
                "promo_code_used": "Yes",
                "subscription_status": "No",
                "churn": "No",
                "previous_purchases": 4,
                "review_rating": 4.0,
                "category": "Clothing",
                "season": "Winter",
                "payment_method": "Credit Card",
                "shipping_type": "Standard",
            },
            {
                "customer_id": 1,
                "purchase_date": "01.08.2023",
                "purchase_amount": "20,0",
                "promo_code_used": "No",
                "subscription_status": "No",
                "churn": "No",
                "previous_purchases": 5,
                "review_rating": 4.0,
                "category": "Clothing",
                "season": "Summer",
                "payment_method": "Credit Card",
                "shipping_type": "Standard",
            },
            {
                "customer_id": 2,
                "purchase_date": "01.02.2023",
                "purchase_amount": 30.0,
                "promo_code_used": 0,
                "subscription_status": 1,
                "churn": 1,
                "previous_purchases": 2,
                "review_rating": 3.5,
                "category": "Accessories",
                "season": "Spring",
                "payment_method": "PayPal",
                "shipping_type": "Express",
            },
            {
                "customer_id": 3,
                "purchase_date": "01.03.2023",
                "purchase_amount": 40.0,
                "promo_code_used": 1,
                "subscription_status": 0,
                "churn": 0,
                "previous_purchases": 7,
                "review_rating": 5.0,
                "category": "Footwear",
                "season": "Spring",
                "payment_method": "Debit Card",
                "shipping_type": "Free Shipping",
            },
            {
                "customer_id": 3,
                "purchase_date": "01.04.2023",
                "purchase_amount": 50.0,
                "promo_code_used": 1,
                "subscription_status": 0,
                "churn": 0,
                "previous_purchases": 8,
                "review_rating": 5.0,
                "category": "Footwear",
                "season": "Spring",
                "payment_method": "Debit Card",
                "shipping_type": "Free Shipping",
            },
        ]
    )


class MethodologyImprovementsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clean = clean_transactions(_fixture())

    def test_first_observed_cohort_fields_are_public_facing(self) -> None:
        self.assertIn("first_observed_purchase_month", self.clean.columns)
        retention = cohort_retention(self.clean)

        self.assertIn("first_observed_purchase_month", retention.columns)
        self.assertNotIn("first_purchase_month", retention.columns)
        self.assertTrue(retention["retention_rate"].between(0, 1).all())

    def test_promo_sensitivity_is_separate_from_rfm_segment(self) -> None:
        rfm = rfm_segments(self.clean)

        self.assertIn("promo_sensitivity", rfm.columns)
        self.assertNotIn("Promo Sensitive", set(rfm["segment"]))
        self.assertEqual(set(rfm["promo_sensitivity"]), {"No Promo", "Moderate Promo", "High Promo"})

        summary = promo_sensitivity_summary(rfm)
        self.assertEqual(int(summary["customers"].sum()), 3)
        self.assertEqual(set(summary["promo_sensitivity"]), {"No Promo", "Moderate Promo", "High Promo"})

    def test_inactivity_snapshot_uses_cutoff_features_and_future_label(self) -> None:
        snapshot = build_inactivity_snapshot(
            self.clean,
            cutoff="2023-06-30",
            horizon_days=180,
        ).set_index("customer_id")

        self.assertEqual(set(snapshot.index), {1, 2, 3})
        self.assertEqual(snapshot.loc[1, "frequency"], 1)
        self.assertEqual(snapshot.loc[1, "future_inactive_180d"], 0)
        self.assertEqual(snapshot.loc[2, "future_inactive_180d"], 1)
        self.assertLessEqual(snapshot["max_feature_purchase_date"].max(), pd.Timestamp("2023-06-30"))


if __name__ == "__main__":
    unittest.main()
