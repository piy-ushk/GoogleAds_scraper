from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def money(value: float, currency: str = "JPY") -> str:
    symbol = "¥" if currency.upper() == "JPY" else f"{currency} "
    return f"{symbol}{value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def metric_sum(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def weighted_average(df: pd.DataFrame, value: str, weight: str) -> float:
    if value not in df.columns or weight not in df.columns:
        return 0.0
    values = pd.to_numeric(df[value], errors="coerce").fillna(0)
    weights = pd.to_numeric(df[weight], errors="coerce").fillna(0)
    total_weight = weights.sum()
    if total_weight == 0:
        return float(values.mean() if len(values) else 0)
    return float((values * weights).sum() / total_weight)


def aggregate_performance(df: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    available_dimensions = [dimension for dimension in dimensions if dimension in df.columns]
    metrics = [column for column in ["cost", "clicks", "impressions", "conversions"] if column in df.columns]
    if not available_dimensions or not metrics:
        return pd.DataFrame()
    grouped = df.groupby(available_dimensions, dropna=False)[metrics].sum().reset_index()
    for col in ["cost", "clicks", "impressions", "conversions"]:
        if col not in grouped.columns:
            grouped[col] = 0.0
    grouped = add_rate_metrics(grouped)
    return grouped.sort_values("cost", ascending=False) if "cost" in grouped.columns else grouped


def add_rate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if {"clicks", "impressions"}.issubset(result.columns):
        result["ctr"] = safe_divide(result["clicks"], result["impressions"]) * 100
    if {"conversions", "clicks"}.issubset(result.columns):
        result["conversion_rate"] = safe_divide(result["conversions"], result["clicks"]) * 100
    if {"cost", "conversions"}.issubset(result.columns):
        result["cost_per_conversion"] = safe_divide(result["cost"], result["conversions"])
    if {"cost", "clicks"}.issubset(result.columns):
        result["avg_cpc"] = safe_divide(result["cost"], result["clicks"])
    return result


def safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> Any:
    if isinstance(denominator, pd.Series):
        return (numerator / denominator.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0)
    if denominator == 0:
        return 0
    return numerator / denominator


def performance_snapshot(df: pd.DataFrame) -> dict[str, float]:
    cost = metric_sum(df, "cost")
    clicks = metric_sum(df, "clicks")
    impressions = metric_sum(df, "impressions")
    conversions = metric_sum(df, "conversions")
    return {
        "cost": cost,
        "clicks": clicks,
        "impressions": impressions,
        "conversions": conversions,
        "ctr": float(safe_divide(clicks, impressions) * 100),
        "conversion_rate": float(safe_divide(conversions, clicks) * 100),
        "cpa": float(safe_divide(cost, conversions)),
        "avg_cpc": float(safe_divide(cost, clicks)),
    }


def finding(
    *,
    title: str,
    priority: Priority,
    category: str,
    reason: str,
    evidence: str,
    impact: str,
    recommendation: str,
    metrics: dict[str, Any] | None = None,
) -> AuditFinding:
    return AuditFinding(
        title=title,
        priority=priority,
        category=category,
        reason=reason,
        evidence=evidence,
        impact=impact,
        recommendation=recommendation,
        metrics=metrics or {},
    )


def spend_share(row: pd.Series, total_cost: float) -> float:
    return float(safe_divide(float(row.get("cost", 0)), total_cost) * 100)


def conversion_share(row: pd.Series, total_conversions: float) -> float:
    return float(safe_divide(float(row.get("conversions", 0)), total_conversions) * 100)


def priority_from_cost(cost: float, config: AuditConfig) -> Priority:
    if cost >= config.zero_conversion_spend_min * 3:
        return Priority.HIGH
    if cost >= config.zero_conversion_spend_min:
        return Priority.MEDIUM
    return Priority.LOW
