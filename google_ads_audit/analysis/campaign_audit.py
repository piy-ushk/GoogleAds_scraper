from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import (
    aggregate_performance,
    conversion_share,
    finding,
    money,
    pct,
    spend_share,
)
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_campaigns(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    campaign_df = aggregate_performance(df, ["campaign"])
    if campaign_df.empty:
        return findings, {}

    total_cost = float(campaign_df["cost"].sum())
    total_conversions = float(campaign_df["conversions"].sum())
    account_cpa = total_cost / total_conversions if total_conversions else 0
    metrics = {
        "campaign_count": int(campaign_df["campaign"].nunique()),
        "total_cost": total_cost,
        "total_conversions": total_conversions,
        "account_cpa": account_cpa,
        "top_campaigns": campaign_df.head(config.top_n_rows).to_dict("records"),
    }

    wasted = campaign_df[
        (campaign_df["cost"] >= config.zero_conversion_spend_min) & (campaign_df["conversions"] == 0)
    ]
    for _, row in wasted.head(5).iterrows():
        findings.append(
            finding(
                title=f"Campaign '{row['campaign']}' is spending without conversions",
                priority=Priority.HIGH,
                category="Campaign Audit",
                reason="The campaign has meaningful spend but has not produced conversions.",
                evidence=f"{money(row['cost'], config.currency)} spent with 0 conversions.",
                impact="Budget is being absorbed by traffic that is not generating measurable inquiries.",
                recommendation="Review search terms, match types, locations, bid strategy, and landing page alignment before allowing more spend.",
                metrics=row.to_dict(),
            )
        )

    inefficient = campaign_df[
        (campaign_df["conversions"] > 0)
        & (campaign_df["cost_per_conversion"] > account_cpa * config.high_cpa_multiplier)
    ]
    for _, row in inefficient.head(5).iterrows():
        findings.append(
            finding(
                title=f"Campaign '{row['campaign']}' has above-average CPA",
                priority=Priority.HIGH,
                category="Campaign Audit",
                reason="CPA is materially higher than the account average.",
                evidence=f"CPA is {money(row['cost_per_conversion'], config.currency)} vs account average {money(account_cpa, config.currency)}.",
                impact="Scaling this campaign without controls will raise blended CPA.",
                recommendation="Reduce budget or bids until search terms, locations, and conversion quality are cleaned up.",
                metrics=row.to_dict(),
            )
        )

    for _, row in campaign_df.head(5).iterrows():
        spend = spend_share(row, total_cost)
        conv = conversion_share(row, total_conversions)
        if spend >= 25 and conv <= spend * 0.5:
            findings.append(
                finding(
                    title=f"Budget concentration risk in '{row['campaign']}'",
                    priority=Priority.MEDIUM,
                    category="Campaign Audit",
                    reason="Spend share is much higher than conversion share.",
                    evidence=f"The campaign used {pct(spend)} of spend but produced only {pct(conv)} of conversions.",
                    impact="Budget allocation may be suppressing stronger campaigns.",
                    recommendation="Reallocate budget toward campaigns with lower CPA and stronger conversion share.",
                    metrics={**row.to_dict(), "spend_share": spend, "conversion_share": conv},
                )
            )

    if "campaign_status" in df.columns:
        inactive = df[df["campaign_status"].astype(str).str.lower().isin(["paused", "removed", "一時停止"])]
        if not inactive.empty:
            findings.append(
                finding(
                    title="Paused or inactive campaigns are present",
                    priority=Priority.LOW,
                    category="Campaign Audit",
                    reason="Paused/removed campaigns can hide historical context or interrupted tests.",
                    evidence=f"{inactive['campaign'].nunique()} inactive campaigns found.",
                    impact="Important learning may be excluded from current optimization decisions.",
                    recommendation="Review why these campaigns were paused and whether winning segments should be rebuilt.",
                    metrics={"inactive_campaigns": int(inactive["campaign"].nunique())},
                )
            )

    low_ctr = campaign_df[campaign_df["ctr"] < config.poor_ctr_threshold]
    for _, row in low_ctr.head(3).iterrows():
        findings.append(
            finding(
                title=f"Low CTR in campaign '{row['campaign']}'",
                priority=Priority.MEDIUM,
                category="Campaign Audit",
                reason="Low CTR suggests weak ad relevance, broad targeting, or poor auction positioning.",
                evidence=f"CTR is {pct(row['ctr'])}.",
                impact="Low CTR can reduce Quality Score and increase CPC.",
                recommendation="Tighten query intent, split ad groups by theme, and rewrite ads around emergency locksmith intent.",
                metrics=row.to_dict(),
            )
        )

    return findings, metrics
