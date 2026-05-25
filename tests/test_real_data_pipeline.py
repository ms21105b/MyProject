from pathlib import Path
import sys
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.data import clean_transactions, load_raw_csv
from promo_retention.modeling import build_inactivity_snapshot


REAL_DATA = PROJECT_ROOT / "data" / "raw" / "EcommData_CSV.csv"


class RealDataPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not REAL_DATA.exists():
            raise unittest.SkipTest("Real Kaggle CSV is not available locally.")
        cls.raw = load_raw_csv(REAL_DATA)
        cls.clean = clean_transactions(cls.raw)

    def test_real_csv_cleaning_preserves_orders_and_parses_types(self) -> None:
        self.assertEqual(len(self.clean), len(self.raw))
        self.assertEqual(self.clean["customer_id"].nunique(), 3900)
        self.assertTrue(pd.api.types.is_numeric_dtype(self.clean["purchase_amount"]))
        self.assertEqual(self.clean["purchase_date"].min().date().isoformat(), "2022-01-01")
        self.assertEqual(self.clean["purchase_date"].max().date().isoformat(), "2024-12-31")
        self.assertEqual(int(self.clean["purchase_amount"].isna().sum()), 0)
        self.assertLessEqual(set(self.clean["promo_code_used"].dropna().unique()), {0, 1})
        self.assertLessEqual(set(self.clean["churn"].dropna().unique()), {0, 1})

    def test_inactivity_snapshot_features_are_customer_level(self) -> None:
        customer_features = build_inactivity_snapshot(self.clean, cutoff="2023-06-30", horizon_days=180)

        self.assertLessEqual(len(customer_features), self.clean["customer_id"].nunique())
        self.assertEqual(customer_features["customer_id"].nunique(), len(customer_features))
        self.assertLessEqual(set(customer_features["future_inactive_180d"].unique()), {0, 1})
        self.assertTrue(
            {
                "frequency",
                "monetary",
                "recency",
                "promo_usage_rate",
                "avg_order_value",
                "avg_review_rating",
                "subscription_status",
                "future_inactive_180d",
            }.issubset(customer_features.columns)
        )


if __name__ == "__main__":
    unittest.main()
