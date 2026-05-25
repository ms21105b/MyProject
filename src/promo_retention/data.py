"""Data loading and normalization helpers."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .config import RAW_COLUMNS


def _snake_case(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def load_raw_csv(path: str | Path) -> pd.DataFrame:
    """Load the Kaggle CSV and normalize column names."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {csv_path}. See data/README.md for download instructions."
        )

    df = pd.read_csv(csv_path, sep=";")
    df = df.rename(columns={raw: key for key, raw in RAW_COLUMNS.items() if raw in df.columns})
    df = df.rename(columns={col: _snake_case(col) for col in df.columns})
    return df


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply reproducible cleaning and feature engineering."""
    cleaned = df.copy()

    if "purchase_date" in cleaned.columns:
        cleaned["purchase_date"] = pd.to_datetime(
            cleaned["purchase_date"], format="%d.%m.%Y", errors="coerce"
        )

    bool_columns = [
        "promo_code_used",
        "discount_applied",
        "churn",
        "subscription_status",
    ]
    for column in bool_columns:
        if column in cleaned.columns:
            cleaned[column] = (
                cleaned[column]
                .astype(str)
                .str.strip()
                .str.lower()
                .map({"yes": 1, "no": 0, "true": 1, "false": 0, "1": 1, "0": 0})
            )

    numeric_columns = ["purchase_amount", "previous_purchases", "review_rating", "age"]
    for column in numeric_columns:
        if column in cleaned.columns:
            cleaned[column] = _to_numeric(cleaned[column])

    if "customer_id" not in cleaned.columns:
        cleaned["customer_id"] = range(1, len(cleaned) + 1)

    cleaned = cleaned.dropna(subset=["customer_id", "purchase_date", "purchase_amount"])
    cleaned = cleaned[cleaned["purchase_amount"] > 0].copy()

    cleaned["order_id"] = range(1, len(cleaned) + 1)
    cleaned["purchase_month"] = cleaned["purchase_date"].dt.to_period("M").dt.to_timestamp()
    cleaned["purchase_quarter"] = cleaned["purchase_date"].dt.to_period("Q").astype(str)
    cleaned["promo_segment"] = cleaned["promo_code_used"].map({1: "Promo", 0: "No Promo"})

    first_purchase = cleaned.groupby("customer_id")["purchase_date"].transform("min")
    cleaned["first_observed_purchase_date"] = first_purchase
    cleaned["first_observed_purchase_month"] = first_purchase.dt.to_period("M").dt.to_timestamp()
    cleaned["first_purchase_date"] = cleaned["first_observed_purchase_date"]
    cleaned["first_purchase_month"] = cleaned["first_observed_purchase_month"]
    cleaned["cohort_index"] = (
        (cleaned["purchase_date"].dt.year - cleaned["first_observed_purchase_date"].dt.year) * 12
        + (cleaned["purchase_date"].dt.month - cleaned["first_observed_purchase_date"].dt.month)
    )

    return cleaned.reset_index(drop=True)


def _to_numeric(series: pd.Series) -> pd.Series:
    """Parse numeric fields from both dot and comma decimal CSV variants."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    normalized = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(normalized, errors="coerce")
