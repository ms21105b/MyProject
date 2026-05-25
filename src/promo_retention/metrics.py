"""Business metric, retention, and RFM calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def monthly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly sales and customer KPIs."""
    monthly = (
        df.groupby("purchase_month")
        .agg(
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
            sales=("purchase_amount", "sum"),
            avg_order_value=("purchase_amount", "mean"),
            promo_usage_rate=("promo_code_used", "mean"),
        )
        .reset_index()
    )
    monthly_churn = (
        df.groupby(["purchase_month", "customer_id"])["churn"]
        .max()
        .groupby("purchase_month")
        .mean()
        .rename("churn_rate")
        .reset_index()
    )
    monthly = monthly.merge(monthly_churn, on="purchase_month", how="left")
    return monthly


def promo_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare behavior between promo-code and non-promo transactions."""
    return (
        df.groupby("promo_segment")
        .agg(
            orders=("order_id", "count"),
            customers=("customer_id", "nunique"),
            sales=("purchase_amount", "sum"),
            avg_order_value=("purchase_amount", "mean"),
            previous_purchases_avg=("previous_purchases", "mean"),
            churn_rate=("churn", "mean"),
        )
        .reset_index()
        .sort_values("orders", ascending=False)
    )


def cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """Build customer cohort retention by first observed purchase month."""
    customer_cohorts = (
        df.groupby(["first_observed_purchase_month", "cohort_index"])["customer_id"]
        .nunique()
        .reset_index(name="customers")
    )
    cohort_sizes = (
        customer_cohorts[customer_cohorts["cohort_index"] == 0]
        .set_index("first_observed_purchase_month")["customers"]
        .rename("cohort_size")
    )
    customer_cohorts = customer_cohorts.join(cohort_sizes, on="first_observed_purchase_month")
    customer_cohorts["retention_rate"] = (
        customer_cohorts["customers"] / customer_cohorts["cohort_size"]
    )
    return customer_cohorts


def cohort_matrix(retention: pd.DataFrame) -> pd.DataFrame:
    """Pivot retention rows into a heatmap-ready matrix."""
    matrix = retention.pivot_table(
        index="first_observed_purchase_month",
        columns="cohort_index",
        values="retention_rate",
        aggfunc="mean",
    )
    matrix.index = matrix.index.strftime("%Y-%m")
    return matrix


def rfm_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Create customer-level RFM scores and segment labels."""
    snapshot_date = df["purchase_date"].max() + pd.Timedelta(days=1)
    rfm = (
        df.groupby("customer_id")
        .agg(
            recency=("purchase_date", lambda x: (snapshot_date - x.max()).days),
            frequency=("order_id", "count"),
            monetary=("purchase_amount", "sum"),
            avg_order_value=("purchase_amount", "mean"),
            promo_usage_rate=("promo_code_used", "mean"),
            previous_purchases=("previous_purchases", "max"),
            churn=("churn", "max"),
        )
        .reset_index()
    )

    rfm["r_score"] = _quantile_score(rfm["recency"], reverse=True)
    rfm["f_score"] = _quantile_score(rfm["frequency"])
    rfm["m_score"] = _quantile_score(rfm["monetary"])
    rfm["rfm_score"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]
    rfm["promo_sensitivity"] = _promo_sensitivity(rfm["promo_usage_rate"])
    rfm["segment"] = np.select(
        [
            (rfm["r_score"] >= 4) & (rfm["f_score"] >= 4) & (rfm["m_score"] >= 4),
            (rfm["r_score"] >= 3) & (rfm["f_score"] >= 3),
            (rfm["r_score"] <= 2) & (rfm["m_score"] >= 4),
            (rfm["r_score"] <= 2) & (rfm["f_score"] <= 2),
        ],
        [
            "High Value",
            "Potential Loyalist",
            "At Risk High Spender",
            "Dormant / Churn Risk",
        ],
        default="Regular",
    )
    return rfm


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Summarize customer segments for business recommendations."""
    aggregations = _summary_aggregations(rfm)
    return rfm.groupby("segment").agg(**aggregations).reset_index().sort_values("customers", ascending=False)


def promo_sensitivity_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """Summarize customer behavior by promo sensitivity tier."""
    aggregations = _summary_aggregations(rfm)
    return (
        rfm.groupby("promo_sensitivity")
        .agg(**aggregations)
        .reset_index()
        .sort_values("customers", ascending=False)
    )


def segment_promo_matrix(rfm: pd.DataFrame) -> pd.DataFrame:
    """Summarize the cross-tab of RFM segment and promo sensitivity."""
    aggregations = _summary_aggregations(rfm)
    return (
        rfm.groupby(["segment", "promo_sensitivity"])
        .agg(**aggregations)
        .reset_index()
        .sort_values(["segment", "customers"], ascending=[True, False])
    )


def _summary_aggregations(rfm: pd.DataFrame) -> dict[str, tuple[str, str]]:
    aggregations: dict[str, tuple[str, str]] = {
        "customers": ("customer_id", "count"),
        "avg_recency": ("recency", "mean"),
        "avg_frequency": ("frequency", "mean"),
        "avg_monetary": ("monetary", "mean"),
        "avg_order_value": ("avg_order_value", "mean"),
        "promo_usage_rate": ("promo_usage_rate", "mean"),
        "churn_rate": ("churn", "mean"),
    }
    if "future_inactive_180d" in rfm.columns:
        aggregations["future_inactive_180d_rate"] = ("future_inactive_180d", "mean")
    return aggregations


def _promo_sensitivity(promo_usage_rate: pd.Series) -> pd.Series:
    promo_users = promo_usage_rate[promo_usage_rate > 0]
    if promo_users.empty:
        return pd.Series("No Promo", index=promo_usage_rate.index)

    high_threshold = promo_users.quantile(0.75)
    return pd.Series(
        np.select(
            [
                promo_usage_rate <= 0,
                promo_usage_rate >= high_threshold,
            ],
            [
                "No Promo",
                "High Promo",
            ],
            default="Moderate Promo",
        ),
        index=promo_usage_rate.index,
    )


def _quantile_score(series: pd.Series, reverse: bool = False) -> pd.Series:
    """Return 1-5 quantile scores with duplicate-safe fallback."""
    ranked = series.rank(method="first")
    labels = [5, 4, 3, 2, 1] if reverse else [1, 2, 3, 4, 5]
    try:
        return pd.qcut(ranked, 5, labels=labels).astype(int)
    except ValueError:
        return pd.Series(np.repeat(3, len(series)), index=series.index)
