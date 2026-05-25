#!/usr/bin/env python3
"""Generate a small schema-compatible sample dataset for smoke tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "customer_behavior_purchase.csv"


def main() -> None:
    rng = np.random.default_rng(42)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    customers = np.arange(1001, 1081)
    rows = []
    for customer_id in customers:
        purchases = int(rng.integers(1, 7))
        first_date = pd.Timestamp("2022-01-01") + pd.Timedelta(days=int(rng.integers(0, 720)))
        churn = int(rng.random() < 0.28)
        for purchase_number in range(purchases):
            purchase_date = first_date + pd.Timedelta(days=int(30 * purchase_number + rng.integers(0, 20)))
            if purchase_date > pd.Timestamp("2024-12-31"):
                continue
            promo = int(rng.random() < 0.42)
            rows.append(
                {
                    "Customer ID": customer_id,
                    "Age": int(rng.integers(18, 66)),
                    "Gender": rng.choice(["Male", "Female", "Other"]),
                    "Item Purchased": rng.choice(["Shirt", "Shoes", "Jacket", "Jeans", "Bag"]),
                    "Category": rng.choice(["Clothing", "Footwear", "Accessories"]),
                    "Purchase Amount (USD)": round(float(rng.normal(65 + promo * 8, 18)), 2),
                    "Location": rng.choice(["California", "New York", "Texas", "Florida"]),
                    "Size": rng.choice(["S", "M", "L", "XL"]),
                    "Color": rng.choice(["Black", "Blue", "White", "Green"]),
                    "Season": rng.choice(["Spring", "Summer", "Fall", "Winter"]),
                    "Review Rating": round(float(rng.uniform(2.5, 5.0)), 1),
                    "Subscription Status": rng.choice(["Yes", "No"], p=[0.35, 0.65]),
                    "Payment Method": rng.choice(["Credit Card", "PayPal", "Debit Card"]),
                    "Shipping Type": rng.choice(["Standard", "Express", "Free Shipping"]),
                    "Discount Applied": "Yes" if promo else "No",
                    "Promo Code Used": "Yes" if promo else "No",
                    "Previous Purchases": purchase_number,
                    "Preferred Payment Method": rng.choice(["Credit Card", "PayPal", "Debit Card"]),
                    "Frequency of Purchases": rng.choice(["Weekly", "Fortnightly", "Monthly", "Quarterly"]),
                    "Purchase Date": purchase_date.strftime("%d.%m.%Y"),
                    "Churn": "Yes" if churn and purchase_number == purchases - 1 else "No",
                }
            )

    pd.DataFrame(rows).to_csv(OUTPUT_FILE, sep=";", index=False)
    print(f"Sample data written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
