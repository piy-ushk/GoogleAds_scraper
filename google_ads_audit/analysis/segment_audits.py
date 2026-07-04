from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance, finding, money, pct
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_segment(
    df: pd.DataFrame,
    dimension: str,
    category: str,
    config: AuditConfig,
) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    segment_df = aggregate_performance(df, [dimension])
    if segment_df.empty:
        return findings, {}

    total_conversions = float(segment_df["conversions"].sum())
    account_cpa = float(segment_df["cost"].sum() / total_conversions) if total_conversions else 0
    metrics = {
        f"{dimension}_comparison": segment_df.head(config.top_n_rows).to_dict("records"),
        "best": segment_df.sort_values(["conversions", "cost_per_conversion"], ascending=[False, True])
        .head(5)
        .to_dict("records"),
        "worst": segment_df.sort_values(["cost_per_conversion", "cost"], ascending=[False, False])
        .head(5)
        .to_dict("records"),
    }

    high_cpa = segment_df[
        (segment_df["conversions"] > 0)
        & (segment_df["cost_per_conversion"] > account_cpa * config.high_cpa_multiplier)
    ]
    for _, row in high_cpa.head(3).iterrows():
        name = row[dimension]
        findings.append(
            finding(
                title=f"High CPA in {dimension} segment '{name}'",
                priority=Priority.MEDIUM,
                category=category,
                reason=f"The {dimension} segment is converting at a materially weaker CPA than the account.",
                evidence=f"CPA is {money(row['cost_per_conversion'], config.currency)} vs account CPA {money(account_cpa, config.currency)}.",
                impact="This segment may be lowering overall efficiency.",
                recommendation=f"Reduce bids, restrict targeting, or split '{name}' into its own campaign/ad group for tighter control.",
                metrics=row.to_dict(),
            )
        )

    no_conversion = segment_df[
        (segment_df["cost"] >= config.zero_conversion_spend_min) & (segment_df["conversions"] == 0)
    ]
    for _, row in no_conversion.head(3).iterrows():
        findings.append(
            finding(
                title=f"{dimension.title()} segment '{row[dimension]}' spent without conversions",
                priority=Priority.HIGH,
                category=category,
                reason="Spend is present but no conversions were recorded.",
                evidence=f"{money(row['cost'], config.currency)} spent with 0 conversions.",
                impact="This segment may be wasting budget.",
                recommendation=f"Exclude, bid down, or isolate this {dimension} segment after checking lead quality.",
                metrics=row.to_dict(),
            )
        )

    if dimension == "device" and len(segment_df) >= 2:
        best_cpa = segment_df[segment_df["cost_per_conversion"] > 0]["cost_per_conversion"].min()
        worst = segment_df.sort_values("cost_per_conversion", ascending=False).iloc[0]
        if best_cpa and worst["cost_per_conversion"] > best_cpa * 1.4:
            gap = ((worst["cost_per_conversion"] - best_cpa) / best_cpa) * 100
            findings.append(
                finding(
                    title=f"{worst['device']} CPA is materially worse than the best device",
                    priority=Priority.MEDIUM,
                    category=category,
                    reason="Device performance is uneven.",
                    evidence=f"{worst['device']} CPA is {money(worst['cost_per_conversion'], config.currency)}, {pct(gap)} above the best device CPA.",
                    impact="Device bid adjustments or landing page issues may be affecting lead volume.",
                    recommendation="Review mobile call tracking, page speed, and device bid adjustments.",
                    metrics=worst.to_dict(),
                )
            )

    return findings, metrics
