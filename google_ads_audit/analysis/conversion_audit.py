from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance, finding, money, performance_snapshot, pct
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_conversions(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    metrics = performance_snapshot(df)
    metrics["trend"] = []
    if df.empty or "conversions" not in df.columns:
        findings.append(
            finding(
                title="Conversion data is missing",
                priority=Priority.HIGH,
                category="Conversion Audit",
                reason="The uploaded files do not include conversion metrics.",
                evidence="No conversions column was detected in the imported data.",
                impact="CPA, CVR, and bid strategy health cannot be trusted without conversion data.",
                recommendation="Export campaign/keyword/search term reports with conversion columns and verify conversion actions.",
                metrics={},
            )
        )
        return findings, metrics

    if metrics["conversions"] == 0 and metrics["cost"] > 0:
        findings.append(
            finding(
                title="No conversions recorded despite spend",
                priority=Priority.HIGH,
                category="Conversion Audit",
                reason="The account has cost but no tracked conversions in the uploaded period.",
                evidence=f"{money(metrics['cost'], config.currency)} spent with 0 conversions.",
                impact="This may indicate tracking failure or severe lead-generation issues.",
                recommendation="Immediately verify primary conversion actions, call tracking, forms, and imported conversions.",
                metrics=metrics,
            )
        )

    if "date" in df.columns:
        trend = aggregate_performance(df, ["date"]).sort_values("date")
        metrics["trend"] = trend.to_dict("records")
        if len(trend) >= 14:
            midpoint = len(trend) // 2
            before = performance_snapshot(trend.iloc[:midpoint])
            after = performance_snapshot(trend.iloc[midpoint:])
            metrics["period_comparison"] = {"before": before, "after": after}
            if before["cpa"] and after["cpa"] > before["cpa"] * 1.25:
                change = ((after["cpa"] - before["cpa"]) / before["cpa"]) * 100
                findings.append(
                    finding(
                        title="CPA worsened in the later period",
                        priority=Priority.HIGH,
                        category="Conversion Audit",
                        reason="Cost per conversion rose materially when comparing the first half to the second half of uploaded data.",
                        evidence=f"CPA increased from {money(before['cpa'], config.currency)} to {money(after['cpa'], config.currency)} ({pct(change)} increase).",
                        impact="The account is paying more for each inquiry than it was earlier in the period.",
                        recommendation="Cross-reference this date range against change history, search terms, auction insights, and landing page changes.",
                        metrics={"before": before, "after": after, "change_pct": change},
                    )
                )
            if before["conversions"] and after["conversions"] < before["conversions"] * 0.8:
                change = ((after["conversions"] - before["conversions"]) / before["conversions"]) * 100
                findings.append(
                    finding(
                        title="Conversion volume declined in the later period",
                        priority=Priority.HIGH,
                        category="Conversion Audit",
                        reason="The later period produced materially fewer conversions.",
                        evidence=f"Conversions changed from {before['conversions']:.0f} to {after['conversions']:.0f} ({pct(change)}).",
                        impact="Lead volume loss is likely visible to the business, not only in ad metrics.",
                        recommendation="Check whether impression share, CPC, conversion tracking, call handling, or landing page behavior changed at the same time.",
                        metrics={"before": before, "after": after, "change_pct": change},
                    )
                )

    if "campaign" in df.columns:
        campaign = aggregate_performance(df, ["campaign"])
        metrics["best_converting_campaigns"] = campaign.sort_values(
            ["conversions", "cost_per_conversion"], ascending=[False, True]
        ).head(config.top_n_rows).to_dict("records")
        metrics["worst_converting_campaigns"] = campaign.sort_values(
            ["cost_per_conversion", "cost"], ascending=[False, False]
        ).head(config.top_n_rows).to_dict("records")

    return findings, metrics
