"""Synthetic-control utilities for quasi-experimental promo analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .metrics import rfm_segments


DEFAULT_OUTCOME = "active_customer_rate"
DEFAULT_PREDICTORS = ("orders_per_customer", "sales_per_customer", "promo_usage_rate")
OUTCOME_COLUMNS = (
    "active_customer_rate",
    "orders_per_customer",
    "sales_per_customer",
    "promo_usage_rate",
)


@dataclass(frozen=True)
class SCMFitResult:
    """Container for one synthetic-control fit."""

    weights: pd.DataFrame
    path: pd.DataFrame
    summary: pd.DataFrame
    donor_units: list[str]


def build_scm_panel(
    df: pd.DataFrame,
    treatment_start: str | pd.Timestamp,
    min_unit_customers: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build a cutoff-safe segment-location-month panel for SCM.

    Customer segment labels are built only from transactions before
    ``treatment_start``. Customers first observed after that date are excluded
    from the SCM panel because they cannot be assigned without post-treatment
    information.
    """
    treatment_month = _month_start(treatment_start)
    pre_df = df[df["purchase_date"] < treatment_month].copy()
    if pre_df.empty:
        raise ValueError("SCM panel requires transactions before treatment_start.")

    labels = rfm_segments(pre_df)[["customer_id", "segment", "promo_sensitivity"]]
    customer_locations = (
        pre_df.groupby("customer_id")["location"].agg(_mode_or_missing).rename("location")
    )
    labels = labels.join(customer_locations, on="customer_id")

    labeled = df.merge(labels, on="customer_id", how="inner", suffixes=("", "_assigned"))
    labeled["assigned_location"] = labeled["location_assigned"].fillna(labeled["location"])

    units = (
        labels.groupby(["segment", "location"])["customer_id"]
        .nunique()
        .rename("unit_customers")
        .reset_index()
    )
    units["unit_id"] = _make_unit_id(units["segment"], units["location"])

    months = pd.date_range(
        df["purchase_month"].min(),
        df["purchase_month"].max(),
        freq="MS",
    )
    skeleton = (
        units[["segment", "location", "unit_id", "unit_customers"]]
        .merge(pd.DataFrame({"purchase_month": months}), how="cross")
        .sort_values(["unit_id", "purchase_month"])
    )

    activity = (
        labeled.groupby(["segment", "assigned_location", "purchase_month"])
        .agg(
            active_customers=("customer_id", "nunique"),
            orders=("order_id", "count"),
            sales=("purchase_amount", "sum"),
            promo_orders=("promo_code_used", "sum"),
        )
        .reset_index()
        .rename(columns={"assigned_location": "location"})
    )

    panel = skeleton.merge(activity, on=["segment", "location", "purchase_month"], how="left")
    for column in ["active_customers", "orders", "sales", "promo_orders"]:
        panel[column] = panel[column].fillna(0.0)

    panel["active_customer_rate"] = panel["active_customers"] / panel["unit_customers"]
    panel["orders_per_customer"] = panel["orders"] / panel["unit_customers"]
    panel["sales_per_customer"] = panel["sales"] / panel["unit_customers"]
    panel["promo_usage_rate"] = np.where(
        panel["orders"] > 0,
        panel["promo_orders"] / panel["orders"],
        0.0,
    )
    panel["treatment_start"] = treatment_month
    panel["period"] = np.where(panel["purchase_month"] < treatment_month, "pre", "post")

    feasibility = summarize_panel_feasibility(panel, treatment_month, min_unit_customers)
    return panel.reset_index(drop=True), feasibility


def summarize_panel_feasibility(
    panel: pd.DataFrame,
    treatment_start: str | pd.Timestamp,
    min_unit_customers: int = 20,
) -> pd.DataFrame:
    """Summarize whether each segment-location unit is viable for SCM."""
    treatment_month = _month_start(treatment_start)
    pre = panel[panel["purchase_month"] < treatment_month]
    post = panel[panel["purchase_month"] >= treatment_month]

    pre_summary = (
        pre.groupby(["unit_id", "segment", "location"])
        .agg(
            unit_customers=("unit_customers", "max"),
            pre_months=("purchase_month", "nunique"),
            pre_active_months=("active_customers", lambda x: int((x > 0).sum())),
            pre_mean_active_customer_rate=("active_customer_rate", "mean"),
            pre_mean_orders_per_customer=("orders_per_customer", "mean"),
            pre_mean_sales_per_customer=("sales_per_customer", "mean"),
        )
        .reset_index()
    )
    post_summary = (
        post.groupby("unit_id")
        .agg(
            post_months=("purchase_month", "nunique"),
            post_active_months=("active_customers", lambda x: int((x > 0).sum())),
            post_mean_active_customer_rate=("active_customer_rate", "mean"),
        )
        .reset_index()
    )
    feasibility = pre_summary.merge(post_summary, on="unit_id", how="left")
    feasibility["post_months"] = feasibility["post_months"].fillna(0).astype(int)
    feasibility["post_active_months"] = feasibility["post_active_months"].fillna(0).astype(int)
    feasibility["eligible_for_scm"] = (
        (feasibility["unit_customers"] >= min_unit_customers)
        & (feasibility["pre_months"] >= 12)
        & (feasibility["post_months"] >= 6)
        & (feasibility["pre_active_months"] >= 6)
    )
    return feasibility.sort_values(
        ["eligible_for_scm", "unit_customers", "pre_active_months"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def choose_treated_candidate(
    feasibility: pd.DataFrame,
    preferred_segments: Iterable[str] | None = None,
) -> str:
    """Choose a pseudo-treated unit for the default SCM demonstration."""
    candidates = feasibility[feasibility["eligible_for_scm"]].copy()
    if preferred_segments:
        preferred = candidates[candidates["segment"].isin(list(preferred_segments))]
        if not preferred.empty:
            candidates = preferred
    if candidates.empty:
        raise ValueError("No eligible segment-location unit is available for SCM.")
    candidates = candidates.sort_values(
        ["unit_customers", "pre_active_months", "pre_mean_active_customer_rate"],
        ascending=[False, False, False],
    )
    return str(candidates.iloc[0]["unit_id"])


def fit_synthetic_control(
    panel: pd.DataFrame,
    treated_unit: str,
    treatment_start: str | pd.Timestamp,
    outcome: str = DEFAULT_OUTCOME,
    donor_units: Iterable[str] | None = None,
    predictor_columns: Iterable[str] | None = DEFAULT_PREDICTORS,
    donor_scope: str = "same_segment",
) -> SCMFitResult:
    """Fit one synthetic-control model with convex donor weights."""
    _validate_outcome(panel, outcome)
    treatment_month = _month_start(treatment_start)
    donors = _resolve_donor_units(panel, treated_unit, donor_units, donor_scope)
    if not donors:
        raise ValueError(f"No donor units available for treated unit: {treated_unit}")

    treated_features, donor_features = _build_feature_matrices(
        panel,
        treated_unit,
        donors,
        treatment_month,
        outcome,
        predictor_columns,
    )
    weights = _solve_weights(treated_features, donor_features)

    path = _build_gap_path(panel, treated_unit, donors, weights, treatment_month, outcome)
    summary = _summarize_fit(path, treated_unit, outcome, treatment_month)
    weight_df = (
        pd.DataFrame({"unit_id": donors, "weight": weights})
        .query("weight > 1e-8")
        .sort_values("weight", ascending=False)
        .reset_index(drop=True)
    )
    weight_df[["segment", "location"]] = weight_df["unit_id"].str.split(
        " | ",
        n=1,
        expand=True,
        regex=False,
    )
    return SCMFitResult(
        weights=weight_df,
        path=path,
        summary=summary,
        donor_units=list(donors),
    )


def run_placebo_tests(
    panel: pd.DataFrame,
    treated_unit: str,
    treatment_start: str | pd.Timestamp,
    outcome: str = DEFAULT_OUTCOME,
    donor_units: Iterable[str] | None = None,
    predictor_columns: Iterable[str] | None = DEFAULT_PREDICTORS,
    donor_scope: str = "same_segment",
) -> pd.DataFrame:
    """Run SCM placebo fits for the treated unit and comparable donor units."""
    treatment_month = _month_start(treatment_start)
    base_units = [treated_unit] + _resolve_donor_units(panel, treated_unit, donor_units, donor_scope)
    rows: list[dict[str, object]] = []
    for placebo_unit in base_units:
        try:
            placebo_donors = [unit for unit in base_units if unit != placebo_unit]
            fit = fit_synthetic_control(
                panel,
                placebo_unit,
                treatment_month,
                outcome=outcome,
                donor_units=placebo_donors,
                predictor_columns=predictor_columns,
                donor_scope="explicit",
            )
            row = fit.summary.iloc[0].to_dict()
            row["is_treated_unit"] = placebo_unit == treated_unit
            row["status"] = "ok"
        except Exception as exc:  # pragma: no cover - exercised by real-data edge cases
            row = {
                "unit_id": placebo_unit,
                "outcome": outcome,
                "is_treated_unit": placebo_unit == treated_unit,
                "status": "failed",
                "failure_reason": str(exc),
                "pre_rmse": np.nan,
                "post_rmse": np.nan,
                "mspe_ratio": np.nan,
            }
        rows.append(row)

    summary = pd.DataFrame(rows)
    ok = summary["status"].eq("ok") & summary["mspe_ratio"].notna()
    summary.loc[ok, "mspe_ratio_rank"] = summary.loc[ok, "mspe_ratio"].rank(
        method="min",
        ascending=False,
    )
    denominator = int(ok.sum())
    summary.loc[ok, "permutation_style_p_value"] = summary.loc[ok, "mspe_ratio_rank"] / max(
        denominator,
        1,
    )
    summary["status_ok"] = summary["status"].eq("ok")
    return (
        summary.sort_values(["status_ok", "mspe_ratio"], ascending=[False, False])
        .drop(columns=["status_ok"])
        .reset_index(drop=True)
    )


def run_injected_lift_simulation(
    panel: pd.DataFrame,
    treated_unit: str,
    treatment_start: str | pd.Timestamp,
    outcome: str = DEFAULT_OUTCOME,
    lift_rates: Iterable[float] = (0.03, 0.05, 0.10),
    donor_units: Iterable[str] | None = None,
    predictor_columns: Iterable[str] | None = DEFAULT_PREDICTORS,
    donor_scope: str = "same_segment",
) -> pd.DataFrame:
    """Inject post-period uplift and check whether SCM recovers its direction."""
    treatment_month = _month_start(treatment_start)
    baseline = fit_synthetic_control(
        panel,
        treated_unit,
        treatment_month,
        outcome=outcome,
        donor_units=donor_units,
        predictor_columns=predictor_columns,
        donor_scope=donor_scope,
    )
    baseline_post_gap = baseline.path.loc[baseline.path["period"] == "post", "gap"].mean()
    treated_post = (
        panel["unit_id"].eq(treated_unit) & (panel["purchase_month"] >= treatment_month)
    )
    original_post_mean = panel.loc[treated_post, outcome].mean()

    rows = []
    for lift_rate in lift_rates:
        lifted_panel = panel.copy()
        lifted_panel.loc[treated_post, outcome] = lifted_panel.loc[treated_post, outcome] * (
            1 + lift_rate
        )
        lifted = fit_synthetic_control(
            lifted_panel,
            treated_unit,
            treatment_month,
            outcome=outcome,
            donor_units=donor_units,
            predictor_columns=predictor_columns,
            donor_scope=donor_scope,
        )
        lifted_post_gap = lifted.path.loc[lifted.path["period"] == "post", "gap"].mean()
        expected_absolute_lift = original_post_mean * lift_rate
        recovered_absolute_lift = lifted_post_gap - baseline_post_gap
        rows.append(
            {
                "unit_id": treated_unit,
                "outcome": outcome,
                "lift_rate": lift_rate,
                "expected_absolute_lift": expected_absolute_lift,
                "recovered_absolute_lift": recovered_absolute_lift,
                "recovery_ratio": _safe_divide(recovered_absolute_lift, expected_absolute_lift),
                "direction_recovered": recovered_absolute_lift > 0,
                "baseline_post_gap": baseline_post_gap,
                "lifted_post_gap": lifted_post_gap,
            }
        )
    return pd.DataFrame(rows)


def summarize_scm_results(
    fit_summary: pd.DataFrame,
    placebo_summary: pd.DataFrame,
    lift_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Create a report-ready one-row SCM interpretation summary."""
    row = fit_summary.iloc[0].to_dict()
    treated_placebo = placebo_summary[placebo_summary["is_treated_unit"]]
    if not treated_placebo.empty:
        row["placebo_rank"] = treated_placebo.iloc[0].get("mspe_ratio_rank")
        row["placebo_p_value"] = treated_placebo.iloc[0].get("permutation_style_p_value")
        row["placebo_units"] = int(placebo_summary["status"].eq("ok").sum())
    row["mean_recovery_ratio"] = float(lift_summary["recovery_ratio"].mean())
    row["all_lift_directions_recovered"] = bool(lift_summary["direction_recovered"].all())
    row["interpretation_label"] = _interpretation_label(row)
    row["analysis_scope"] = "quasi_ab_simulation"
    return pd.DataFrame([row])


def run_scm_workflow(
    df: pd.DataFrame,
    treatment_start: str | pd.Timestamp = "2024-01-01",
    outcome: str = DEFAULT_OUTCOME,
    treatment_segment: str | None = None,
    treatment_location: str | None = None,
    min_unit_customers: int = 20,
    donor_scope: str = "same_segment",
) -> dict[str, object]:
    """Run the default SCM workflow and return all report artifacts."""
    panel, feasibility = build_scm_panel(
        df,
        treatment_start=treatment_start,
        min_unit_customers=min_unit_customers,
    )
    if treatment_segment and treatment_location:
        treated_unit = f"{treatment_segment} | {treatment_location}"
    else:
        treated_unit = choose_treated_candidate(feasibility)

    fit = fit_synthetic_control(
        panel,
        treated_unit,
        treatment_start,
        outcome=outcome,
        donor_scope=donor_scope,
    )
    placebo = run_placebo_tests(
        panel,
        treated_unit,
        treatment_start,
        outcome=outcome,
        donor_units=fit.donor_units,
        donor_scope="explicit",
    )
    lift = run_injected_lift_simulation(
        panel,
        treated_unit,
        treatment_start,
        outcome=outcome,
        donor_units=fit.donor_units,
        donor_scope="explicit",
    )
    summary = summarize_scm_results(fit.summary, placebo, lift)
    metadata = {
        "analysis_type": "pseudo_treatment_quasi_ab_simulation",
        "treatment_start": _month_start(treatment_start).date().isoformat(),
        "treated_unit": treated_unit,
        "outcome": outcome,
        "donor_scope": donor_scope,
        "donor_units": fit.donor_units,
        "causal_claim": "simulation_only_no_randomized_treatment",
    }
    return {
        "panel": panel,
        "feasibility": feasibility,
        "weights": fit.weights,
        "gap_path": fit.path,
        "fit_summary": fit.summary,
        "placebo_summary": placebo,
        "lift_summary": lift,
        "summary": summary,
        "metadata": metadata,
    }


def _build_feature_matrices(
    panel: pd.DataFrame,
    treated_unit: str,
    donor_units: list[str],
    treatment_start: pd.Timestamp,
    outcome: str,
    predictor_columns: Iterable[str] | None,
) -> tuple[np.ndarray, np.ndarray]:
    pre = panel[panel["purchase_month"] < treatment_start]
    units = [treated_unit] + donor_units
    outcome_wide = (
        pre.pivot(index="purchase_month", columns="unit_id", values=outcome)
        .reindex(columns=units)
        .sort_index()
    )
    feature_frame = outcome_wide.copy()

    extra_predictors = [col for col in (predictor_columns or []) if col in panel.columns and col != outcome]
    for column in extra_predictors:
        means = pre.groupby("unit_id")[column].mean().reindex(units)
        feature_frame.loc[f"pre_mean_{column}", :] = means.to_numpy()

    feature_frame = feature_frame.astype(float).fillna(0.0)
    standardized = feature_frame.copy()
    for idx in standardized.index:
        values = standardized.loc[idx, :]
        std = float(values.std(ddof=0))
        if std > 0:
            standardized.loc[idx, :] = (values - float(values.mean())) / std

    treated_features = standardized[treated_unit].to_numpy(dtype=float)
    donor_features = standardized[donor_units].to_numpy(dtype=float)
    return treated_features, donor_features


def _solve_weights(treated_features: np.ndarray, donor_features: np.ndarray) -> np.ndarray:
    donor_count = donor_features.shape[1]

    def objective(weights: np.ndarray) -> float:
        residual = treated_features - donor_features @ weights
        return float(residual @ residual)

    initial_weights = [np.repeat(1.0 / donor_count, donor_count)]
    initial_weights.extend(np.eye(donor_count))
    candidates = [weights.copy() for weights in initial_weights]

    for initial in initial_weights:
        result = minimize(
            objective,
            initial,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * donor_count,
            constraints=({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},),
            options={"maxiter": 1000, "ftol": 1e-12},
        )
        if np.all(np.isfinite(result.x)):
            weights = _normalize_simplex(result.x)
            if weights is not None:
                candidates.append(weights)
        if result.success:
            break

    feasible = [weights for weights in candidates if weights is not None]
    if not feasible:
        raise ValueError("Synthetic-control optimization failed: no feasible weights.")
    return min(feasible, key=objective)


def _build_gap_path(
    panel: pd.DataFrame,
    treated_unit: str,
    donor_units: list[str],
    weights: np.ndarray,
    treatment_start: pd.Timestamp,
    outcome: str,
) -> pd.DataFrame:
    outcome_wide = (
        panel.pivot(index="purchase_month", columns="unit_id", values=outcome)
        .reindex(columns=[treated_unit] + donor_units)
        .sort_index()
        .fillna(0.0)
    )
    synthetic = outcome_wide[donor_units].to_numpy(dtype=float) @ weights
    path = pd.DataFrame(
        {
            "purchase_month": outcome_wide.index,
            "unit_id": treated_unit,
            "outcome": outcome,
            "actual": outcome_wide[treated_unit].to_numpy(dtype=float),
            "synthetic": synthetic,
        }
    )
    path["gap"] = path["actual"] - path["synthetic"]
    path["period"] = np.where(path["purchase_month"] < treatment_start, "pre", "post")
    return path


def _summarize_fit(
    path: pd.DataFrame,
    treated_unit: str,
    outcome: str,
    treatment_start: pd.Timestamp,
) -> pd.DataFrame:
    pre_gap = path.loc[path["period"] == "pre", "gap"]
    post_gap = path.loc[path["period"] == "post", "gap"]
    pre_actual = path.loc[path["period"] == "pre", "actual"]
    post_actual = path.loc[path["period"] == "post", "actual"]
    pre_mspe = float(np.mean(np.square(pre_gap)))
    post_mspe = float(np.mean(np.square(post_gap)))
    row = {
        "unit_id": treated_unit,
        "outcome": outcome,
        "treatment_start": treatment_start.date().isoformat(),
        "pre_months": int((path["period"] == "pre").sum()),
        "post_months": int((path["period"] == "post").sum()),
        "pre_mean_actual": float(pre_actual.mean()),
        "post_mean_actual": float(post_actual.mean()),
        "pre_mean_gap": float(pre_gap.mean()),
        "post_mean_gap": float(post_gap.mean()),
        "pre_rmse": float(np.sqrt(pre_mspe)),
        "post_rmse": float(np.sqrt(post_mspe)),
        "pre_mspe": pre_mspe,
        "post_mspe": post_mspe,
        "mspe_ratio": _safe_divide(post_mspe, pre_mspe),
    }
    row["pre_fit_label"] = "GOOD_PRE_FIT" if row["pre_rmse"] <= max(0.02, row["pre_mean_actual"] * 0.25) else "POOR_PRE_FIT"
    return pd.DataFrame([row])


def _resolve_donor_units(
    panel: pd.DataFrame,
    treated_unit: str,
    donor_units: Iterable[str] | None,
    donor_scope: str,
) -> list[str]:
    if donor_units is not None:
        return [str(unit) for unit in donor_units if str(unit) != treated_unit]

    unit_info = panel[["unit_id", "segment"]].drop_duplicates()
    if treated_unit not in set(unit_info["unit_id"]):
        raise ValueError(f"Treated unit not found in SCM panel: {treated_unit}")
    if donor_scope == "same_segment":
        segment = unit_info.loc[unit_info["unit_id"] == treated_unit, "segment"].iloc[0]
        donors = unit_info.loc[
            (unit_info["segment"] == segment) & (unit_info["unit_id"] != treated_unit),
            "unit_id",
        ]
    elif donor_scope in {"all", "explicit"}:
        donors = unit_info.loc[unit_info["unit_id"] != treated_unit, "unit_id"]
    else:
        raise ValueError("donor_scope must be one of: same_segment, all, explicit")
    return sorted(donors.astype(str).tolist())


def _validate_outcome(panel: pd.DataFrame, outcome: str) -> None:
    if outcome not in panel.columns:
        raise ValueError(f"Outcome column not found in SCM panel: {outcome}")
    if outcome not in OUTCOME_COLUMNS:
        raise ValueError(f"Unsupported SCM outcome: {outcome}")


def _interpretation_label(row: dict[str, object]) -> str:
    if row.get("pre_fit_label") != "GOOD_PRE_FIT":
        return "SIMULATION_ONLY_POOR_PRE_FIT"
    if not row.get("all_lift_directions_recovered", False):
        return "SIMULATION_ONLY_WEAK_LIFT_RECOVERY"
    return "SIMULATION_ONLY_GOOD_PRE_FIT"


def _make_unit_id(segment: pd.Series, location: pd.Series) -> pd.Series:
    return segment.astype(str) + " | " + location.astype(str)


def _mode_or_missing(series: pd.Series) -> str:
    mode = series.dropna().mode()
    if mode.empty:
        return "Unknown"
    return str(mode.iloc[0])


def _month_start(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp()


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return float(numerator / denominator)


def _normalize_simplex(weights: np.ndarray) -> np.ndarray | None:
    clipped = np.clip(weights.astype(float), 0.0, 1.0)
    total = clipped.sum()
    if total <= 0 or not np.isfinite(total):
        return None
    return clipped / total
