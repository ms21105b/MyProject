"""Optional churn modeling for business interpretation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_inactivity_snapshot(
    df: pd.DataFrame,
    cutoff: str | pd.Timestamp,
    horizon_days: int = 180,
) -> pd.DataFrame:
    """Build cutoff-safe customer features and future inactivity labels."""
    cutoff_date = pd.Timestamp(cutoff)
    horizon_end = cutoff_date + pd.Timedelta(days=horizon_days)
    history = df[df["purchase_date"] <= cutoff_date].copy()
    future = df[(df["purchase_date"] > cutoff_date) & (df["purchase_date"] <= horizon_end)].copy()

    if history.empty:
        raise ValueError("Inactivity snapshot requires at least one historical transaction.")

    snapshot = build_customer_features(history, snapshot_date=cutoff_date + pd.Timedelta(days=1))
    future_active_customers = set(future["customer_id"].unique())
    snapshot["future_inactive_180d"] = (~snapshot["customer_id"].isin(future_active_customers)).astype(int)
    snapshot["cutoff_date"] = cutoff_date
    snapshot["horizon_days"] = horizon_days
    snapshot["horizon_end_date"] = horizon_end
    return snapshot


def train_inactivity_risk_model(
    df: pd.DataFrame,
    train_cutoff: str | pd.Timestamp = "2023-06-30",
    test_cutoff: str | pd.Timestamp = "2023-12-31",
    horizon_days: int = 180,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Train and evaluate a 180-day future inactivity risk model with time splits."""
    train_df = build_inactivity_snapshot(df, train_cutoff, horizon_days)
    test_df = build_inactivity_snapshot(df, test_cutoff, horizon_days)
    features = _model_features(train_df, test_df)

    x_train = train_df[features]
    y_train = train_df["future_inactive_180d"].astype(int)
    x_test = test_df[features]
    y_test = test_df["future_inactive_180d"].astype(int)

    if y_train.nunique() < 2 or y_test.nunique() < 2:
        raise ValueError("Inactivity model requires both active and inactive labels in train and test windows.")

    pipeline = _build_pipeline(x_train, features)
    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    y_score = pipeline.predict_proba(x_test)[:, 1]
    metrics = {
        "model_level": "customer_time_split",
        "target": f"future_inactive_{horizon_days}d",
        "train_cutoff": pd.Timestamp(train_cutoff).date().isoformat(),
        "test_cutoff": pd.Timestamp(test_cutoff).date().isoformat(),
        "horizon_days": horizon_days,
        "train_customers": int(len(train_df)),
        "test_customers": int(len(test_df)),
        "train_positive_rate": float(y_train.mean()),
        "test_positive_rate": float(y_test.mean()),
        "roc_auc": float(roc_auc_score(y_test, y_score)),
        "classification_report": classification_report(
            y_test,
            y_pred,
            output_dict=True,
            zero_division=0,
        ),
    }

    feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importances = pipeline.named_steps["model"].feature_importances_
    importance_df = (
        pd.DataFrame({"feature": feature_names, "importance": importances})
        .sort_values("importance", ascending=False)
        .head(20)
        .reset_index(drop=True)
    )
    return importance_df, metrics


def build_customer_features(
    df: pd.DataFrame,
    snapshot_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Aggregate order-level transactions into one row per customer for modeling."""
    if snapshot_date is None:
        snapshot_date = df["purchase_date"].max() + pd.Timedelta(days=1)

    aggregations: dict[str, tuple[str, object]] = {
        "frequency": ("order_id", "count"),
        "monetary": ("purchase_amount", "sum"),
        "avg_order_value": ("purchase_amount", "mean"),
        "recency": ("purchase_date", lambda x: (snapshot_date - x.max()).days),
        "max_feature_purchase_date": ("purchase_date", "max"),
        "promo_usage_rate": ("promo_code_used", "mean"),
        "promo_orders": ("promo_code_used", "sum"),
        "previous_purchases": ("previous_purchases", "max"),
        "subscription_status": ("subscription_status", "max"),
        "churn": ("churn", "max"),
    }
    if "age" in df.columns:
        aggregations["age"] = ("age", "max")
    if "review_rating" in df.columns:
        aggregations["avg_review_rating"] = ("review_rating", "mean")
    if "category" in df.columns:
        aggregations["distinct_categories"] = ("category", "nunique")
        aggregations["top_category"] = ("category", _mode_or_missing)
    if "season" in df.columns:
        aggregations["top_season"] = ("season", _mode_or_missing)
    if "payment_method" in df.columns:
        aggregations["top_payment_method"] = ("payment_method", _mode_or_missing)
    if "shipping_type" in df.columns:
        aggregations["top_shipping_type"] = ("shipping_type", _mode_or_missing)
    if "gender" in df.columns:
        aggregations["gender"] = ("gender", _mode_or_missing)
    if "location" in df.columns:
        aggregations["location"] = ("location", _mode_or_missing)

    customer_df = df.groupby("customer_id").agg(**aggregations).reset_index()
    customer_df["has_promo_order"] = (customer_df["promo_orders"] > 0).astype(int)
    active_months = (
        df.groupby("customer_id")["purchase_month"]
        .nunique()
        .reindex(customer_df["customer_id"])
        .to_numpy()
    )
    customer_df["active_months"] = active_months
    customer_df["orders_per_active_month"] = customer_df["frequency"] / np.maximum(active_months, 1)
    return customer_df


def _model_features(*frames: pd.DataFrame) -> list[str]:
    candidates = [
        "age",
        "frequency",
        "monetary",
        "avg_order_value",
        "recency",
        "promo_usage_rate",
        "promo_orders",
        "has_promo_order",
        "avg_review_rating",
        "previous_purchases",
        "subscription_status",
        "distinct_categories",
        "active_months",
        "orders_per_active_month",
        "gender",
        "location",
        "top_category",
        "top_season",
        "top_payment_method",
        "top_shipping_type",
    ]
    return [column for column in candidates if all(column in frame.columns for frame in frames)]


def _build_pipeline(x: pd.DataFrame, features: list[str]) -> Pipeline:
    numeric_features = [column for column in features if pd.api.types.is_numeric_dtype(x[column])]
    categorical_features = [column for column in features if column not in numeric_features]

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=10,
        random_state=42,
        class_weight="balanced",
    )
    return Pipeline(steps=[("preprocessor", preprocessor), ("model", classifier)])


def _mode_or_missing(series: pd.Series) -> str:
    mode = series.dropna().mode()
    if mode.empty:
        return "Unknown"
    return str(mode.iloc[0])
