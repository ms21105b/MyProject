"""Plot generation for portfolio-ready figures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_CACHE_DIR = Path(tempfile.gettempdir()) / "promo_retention_cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_DIR))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def set_theme() -> None:
    sns.set_theme(style="whitegrid", palette="Set2")
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.bbox"] = "tight"


def save_monthly_trend(monthly: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(monthly["purchase_month"], monthly["sales"], marker="o", label="Sales")
    ax1.set_title("Monthly Sales and Promo Usage")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Sales")

    ax2 = ax1.twinx()
    ax2.plot(
        monthly["purchase_month"],
        monthly["promo_usage_rate"],
        color="#d95f02",
        marker="s",
        label="Promo usage rate",
    )
    ax2.set_ylabel("Promo usage rate")
    fig.autofmt_xdate()
    fig.savefig(output_path)
    plt.close(fig)


def save_cohort_heatmap(matrix: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, ax = plt.subplots(figsize=(11, 7))
    sns.heatmap(matrix, cmap="YlGnBu", annot=False, fmt=".0%", ax=ax)
    ax.set_title("First Observed Purchase Cohort Retention")
    ax.set_xlabel("Months Since First Purchase")
    ax.set_ylabel("First Observed Purchase Month")
    fig.savefig(output_path)
    plt.close(fig)


def save_cohort_heatmap_by_promo(
    promo_first_matrix: pd.DataFrame,
    no_promo_first_matrix: pd.DataFrame,
    output_path: str | Path,
) -> None:
    set_theme()
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    for ax, matrix, title in [
        (axes[0], promo_first_matrix, "Promo First Observed Cohort"),
        (axes[1], no_promo_first_matrix, "No Promo First Observed Cohort"),
    ]:
        sns.heatmap(matrix, cmap="YlGnBu", annot=False, fmt=".0%", ax=ax)
        ax.set_title(title)
        ax.set_xlabel("Months Since First Purchase")
        ax.set_ylabel("First Observed Purchase Month")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def save_promo_comparison(comparison: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    sns.barplot(data=comparison, x="promo_segment", y="avg_order_value", ax=axes[0])
    axes[0].set_title("Average Order Value")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("USD")

    sns.barplot(data=comparison, x="promo_segment", y="churn_rate", ax=axes[1])
    axes[1].set_title("Churn Rate")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Rate")
    fig.savefig(output_path)
    plt.close(fig)


def save_segment_matrix(segment_summary: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, ax = plt.subplots(figsize=(9, 5))
    plot_data = segment_summary.copy()
    sns.scatterplot(
        data=plot_data,
        x="promo_usage_rate",
        y="churn_rate",
        size="customers",
        hue="segment",
        sizes=(80, 900),
        ax=ax,
        legend="brief",
    )
    ax.set_title("Segment Strategy Matrix")
    ax.set_xlabel("Promo Usage Rate")
    ax.set_ylabel("Churn Rate")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)
    fig.savefig(output_path)
    plt.close(fig)


def save_promo_sensitivity_summary(summary: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    order = ["No Promo", "Moderate Promo", "High Promo"]
    plot_data = summary.copy()
    sns.barplot(data=plot_data, x="promo_sensitivity", y="customers", order=order, ax=axes[0])
    axes[0].set_title("Customers by Promo Sensitivity")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Customers")
    axes[0].tick_params(axis="x", rotation=20)

    y_column = "future_inactive_180d_rate" if "future_inactive_180d_rate" in plot_data.columns else "churn_rate"
    sns.barplot(data=plot_data, x="promo_sensitivity", y=y_column, order=order, ax=axes[1])
    axes[1].set_title("Future Inactivity Risk")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Rate")
    axes[1].tick_params(axis="x", rotation=20)
    fig.savefig(output_path)
    plt.close(fig)


def save_scm_actual_vs_synthetic(path: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(path["purchase_month"], path["actual"], marker="o", label="Actual")
    ax.plot(path["purchase_month"], path["synthetic"], marker="s", label="Synthetic")
    _mark_scm_treatment_start(path, ax)
    ax.set_title("SCM Actual vs Synthetic")
    ax.set_xlabel("Month")
    ax.set_ylabel(str(path["outcome"].iloc[0]))
    ax.legend()
    fig.autofmt_xdate()
    fig.savefig(output_path)
    plt.close(fig)


def save_scm_gap_path(path: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axhline(0, color="#555555", linewidth=1)
    ax.plot(path["purchase_month"], path["gap"], marker="o", color="#1b9e77")
    _mark_scm_treatment_start(path, ax)
    ax.set_title("SCM Gap Path")
    ax.set_xlabel("Month")
    ax.set_ylabel("Actual - Synthetic")
    fig.autofmt_xdate()
    fig.savefig(output_path)
    plt.close(fig)


def save_scm_placebo_mspe_ratio(placebo: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    plot_data = placebo[placebo["status"].eq("ok")].copy()
    plot_data = plot_data.sort_values("mspe_ratio", ascending=False)
    plot_data["label"] = plot_data["unit_id"].where(plot_data["is_treated_unit"], "Placebo")
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.barplot(data=plot_data, x="unit_id", y="mspe_ratio", hue="is_treated_unit", dodge=False, ax=ax)
    ax.set_title("SCM Placebo MSPE Ratio")
    ax.set_xlabel("")
    ax.set_ylabel("Post / Pre MSPE")
    ax.tick_params(axis="x", rotation=75)
    ax.legend(title="Pseudo-treated")
    fig.savefig(output_path)
    plt.close(fig)


def save_scm_injected_lift_recovery(lift: pd.DataFrame, output_path: str | Path) -> None:
    set_theme()
    plot_data = lift.copy()
    plot_data["lift_rate_pct"] = plot_data["lift_rate"] * 100
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axhline(1, color="#555555", linewidth=1, linestyle="--")
    sns.barplot(data=plot_data, x="lift_rate_pct", y="recovery_ratio", color="#7570b3", ax=ax)
    ax.set_title("SCM Injected Lift Recovery")
    ax.set_xlabel("Injected lift (%)")
    ax.set_ylabel("Recovered / Expected Lift")
    fig.savefig(output_path)
    plt.close(fig)


def _mark_scm_treatment_start(path: pd.DataFrame, ax: plt.Axes) -> None:
    post_months = path.loc[path["period"] == "post", "purchase_month"]
    if post_months.empty:
        return
    treatment_start = post_months.min()
    ax.axvline(treatment_start, color="#d95f02", linestyle="--", linewidth=1)
