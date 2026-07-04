from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance


def build_charts(reports: dict) -> dict[str, object]:
    try:
        import plotly.express as px
    except ModuleNotFoundError:
        return {}

    charts: dict[str, object] = {}
    performance = _best_performance_frame(reports)
    if performance is not None and not performance.empty:
        if "date" in performance.columns:
            trend = aggregate_performance(performance, ["date"]).sort_values("date")
            charts["Spend Trend"] = px.line(trend, x="date", y="cost", title="Spend Trend")
            charts["CPA Trend"] = px.line(trend, x="date", y="cost_per_conversion", title="CPA Trend")
            charts["Conversion Trend"] = px.line(trend, x="date", y="conversions", title="Conversion Trend")
            charts["CTR Trend"] = px.line(trend, x="date", y="ctr", title="CTR Trend")
        if "campaign" in performance.columns:
            campaign = aggregate_performance(performance, ["campaign"]).head(15)
            charts["Campaign Comparison"] = px.bar(
                campaign,
                x="campaign",
                y=["cost", "conversions"],
                title="Campaign Cost and Conversions",
                barmode="group",
            )
            charts["Budget Allocation"] = px.pie(
                campaign,
                names="campaign",
                values="cost",
                title="Budget Allocation by Campaign",
            )
        if "keyword" in performance.columns:
            keyword = aggregate_performance(performance, ["keyword"]).head(15)
            charts["Keyword Comparison"] = px.bar(
                keyword, x="keyword", y="cost_per_conversion", title="Top Keyword CPA"
            )
        if "device" in performance.columns:
            device = aggregate_performance(performance, ["device"])
            charts["Device Comparison"] = px.bar(
                device, x="device", y=["cost", "conversions"], barmode="group", title="Device Performance"
            )
        if "location" in performance.columns:
            location = aggregate_performance(performance, ["location"]).head(15)
            charts["Location Comparison"] = px.bar(
                location, x="location", y="cost_per_conversion", title="Location CPA"
            )
        if "cost" in performance.columns:
            top_spenders = performance.sort_values("cost", ascending=False).head(15)
            label = _first_available(top_spenders, ["campaign", "keyword", "search_term", "final_url"])
            if label:
                charts["Top Spenders"] = px.bar(top_spenders, x=label, y="cost", title="Top Spenders")
        if "conversions" in performance.columns:
            top_converters = performance.sort_values("conversions", ascending=False).head(15)
            label = _first_available(top_converters, ["campaign", "keyword", "search_term", "final_url"])
            if label:
                charts["Top Converters"] = px.bar(
                    top_converters, x=label, y="conversions", title="Top Converters"
                )
    return charts


def _best_performance_frame(reports: dict) -> pd.DataFrame | None:
    candidates = [
        frame
        for frame in reports.values()
        if isinstance(frame, pd.DataFrame) and {"cost", "clicks", "impressions"}.issubset(frame.columns)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda frame: len(frame.columns))


def _first_available(df: pd.DataFrame, columns: list[str]) -> str | None:
    for column in columns:
        if column in df.columns:
            return column
    return None
