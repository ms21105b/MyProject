"""Dataset validation checks used by scripts and notebooks."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "customer_id",
    "purchase_date",
    "purchase_amount",
    "promo_code_used",
    "previous_purchases",
    "churn",
]


def validate_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Return a compact validation report as a DataFrame."""
    rows: list[dict[str, object]] = []
    rows.append(
        {
            "check": "row_count",
            "status": "PASS" if len(df) > 0 else "FAIL",
            "value": len(df),
            "missing_rate": 0.0,
        }
    )
    if "customer_id" in df.columns:
        rows.append(
            {
                "check": "customer_count",
                "status": "PASS" if df["customer_id"].nunique() > 0 else "FAIL",
                "value": int(df["customer_id"].nunique()),
                "missing_rate": float(df["customer_id"].isna().mean()),
            }
        )

    for column in REQUIRED_COLUMNS:
        exists = column in df.columns
        missing_rate = float(df[column].isna().mean()) if exists else None
        rows.append(
            {
                "check": f"required_column:{column}",
                "status": "PASS" if exists else "FAIL",
                "value": "" if exists else "missing",
                "missing_rate": missing_rate,
            }
        )

    if "purchase_date" in df.columns:
        min_date = df["purchase_date"].min()
        max_date = df["purchase_date"].max()
        rows.append(
            {
                "check": "date_range",
                "status": "PASS" if pd.notna(min_date) and pd.notna(max_date) else "FAIL",
                "value": f"{min_date.date()} to {max_date.date()}",
                "missing_rate": float(df["purchase_date"].isna().mean()),
            }
        )

    if "purchase_amount" in df.columns:
        rows.append(
            {
                "check": "positive_purchase_amount",
                "status": "PASS" if (df["purchase_amount"] > 0).all() else "WARN",
                "value": int((df["purchase_amount"] <= 0).sum()),
                "missing_rate": float(df["purchase_amount"].isna().mean()),
            }
        )

    for column in ["promo_code_used", "churn", "subscription_status"]:
        if column in df.columns:
            values = sorted(df[column].dropna().unique().tolist())
            rows.append(
                {
                    "check": f"binary_values:{column}",
                    "status": "PASS" if set(values).issubset({0, 1}) else "WARN",
                    "value": "|".join(str(int(value)) for value in values),
                    "missing_rate": float(df[column].isna().mean()),
                }
            )
            rows.append(
                {
                    "check": f"rate:{column}",
                    "status": "PASS",
                    "value": float(df[column].mean()),
                    "missing_rate": float(df[column].isna().mean()),
                }
            )

    return pd.DataFrame(rows)


def summarize_cleaning(raw: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    """Compare key counts before and after cleaning."""
    def _binary_mean(series: pd.Series) -> float | None:
        mapped = (
            series.astype(str)
            .str.strip()
            .str.lower()
            .map({"yes": 1, "no": 0, "true": 1, "false": 0, "1": 1, "0": 0})
        )
        if mapped.notna().any():
            return float(mapped.mean())
        numeric = pd.to_numeric(series, errors="coerce")
        return float(numeric.mean()) if numeric.notna().any() else None

    def _metrics(frame: pd.DataFrame, label: str) -> dict[str, object]:
        return {
            "stage": label,
            "rows": len(frame),
            "customers": frame["customer_id"].nunique() if "customer_id" in frame else None,
            "sales": _numeric(frame["purchase_amount"]).sum() if "purchase_amount" in frame else None,
            "promo_usage_rate": _binary_mean(frame["promo_code_used"])
            if "promo_code_used" in frame
            else None,
        }

    return pd.DataFrame([_metrics(raw, "raw"), _metrics(clean, "clean")])


def _numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    normalized = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(normalized, errors="coerce")
