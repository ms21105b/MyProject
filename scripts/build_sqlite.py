#!/usr/bin/env python3
"""Load the cleaned CSV into SQLite for SQL practice."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from promo_retention.config import DEFAULT_RAW_FILE
from promo_retention.data import clean_transactions, load_raw_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_RAW_FILE),
        help="Path to Kaggle CSV. Defaults to data/raw/EcommData_CSV.csv.",
    )
    parser.add_argument("--output", default="data/processed/ecommerce.sqlite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    raw = load_raw_csv(args.input)
    clean = clean_transactions(raw)
    sqlite_df = clean.copy()
    for column in [
        "purchase_date",
        "purchase_month",
        "first_observed_purchase_date",
        "first_observed_purchase_month",
        "first_purchase_date",
        "first_purchase_month",
    ]:
        if column in sqlite_df.columns:
            sqlite_df[column] = sqlite_df[column].dt.strftime("%Y-%m-%d")

    with sqlite3.connect(output) as connection:
        sqlite_df.to_sql("transactions_clean", connection, if_exists="replace", index=False)

    print(f"SQLite database written to {output}")


if __name__ == "__main__":
    main()
