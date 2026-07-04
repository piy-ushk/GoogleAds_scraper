from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance, finding, money, pct
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_keywords(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    keyword_df = aggregate_performance(df, ["keyword", "match_type"])
    if keyword_df.empty:
        return findings, {}

    metrics = {
        "keyword_count": int(keyword_df["keyword"].nunique()),
        "top_keywords": keyword_df.head(config.top_n_rows).to_dict("records"),
    }

    wasted = keyword_df[
        (keyword_df["cost"] >= config.zero_conversion_spend_min) & (keyword_df["conversions"] == 0)
    ]
    for _, row in wasted.head(10).iterrows():
        findings.append(
            finding(
                title=f"Keyword '{row['keyword']}' spent without conversions",
                priority=Priority.HIGH,
                category="Keyword Audit",
                reason="A keyword consumed budget but did not generate conversions.",
                evidence=f"{money(row['cost'], config.currency)} spent, 0 conversions, {int(row['clicks'])} clicks.",
                impact="This is direct wasted spend unless it assists conversions outside current tracking.",
                recommendation="Pause, lower bids, or move to a tighter match type after reviewing matching search terms.",
                metrics=row.to_dict(),
            )
        )

    account_cpa = keyword_df["cost"].sum() / keyword_df["conversions"].sum() if keyword_df["conversions"].sum() else 0
    high_cpa = keyword_df[
        (keyword_df["conversions"] > 0)
        & (keyword_df["cost_per_conversion"] > account_cpa * config.high_cpa_multiplier)
    ]
    for _, row in high_cpa.head(5).iterrows():
        findings.append(
            finding(
                title=f"Keyword '{row['keyword']}' has high CPA",
                priority=Priority.MEDIUM,
                category="Keyword Audit",
                reason="Keyword CPA is materially above the account average.",
                evidence=f"CPA is {money(row['cost_per_conversion'], config.currency)} vs keyword average {money(account_cpa, config.currency)}.",
                impact="High CPA keywords reduce account efficiency even when they convert.",
                recommendation="Segment by device/location, reduce bid pressure, and isolate high-intent variants.",
                metrics=row.to_dict(),
            )
        )

    if "quality_score" in df.columns:
        low_qs = df[pd.to_numeric(df["quality_score"], errors="coerce") <= config.low_quality_score_threshold]
        if not low_qs.empty:
            findings.append(
                finding(
                    title="Low Quality Score keywords need cleanup",
                    priority=Priority.MEDIUM,
                    category="Keyword Audit",
                    reason="Low Quality Score usually indicates weak ad relevance, landing page relevance, or expected CTR.",
                    evidence=f"{low_qs['keyword'].nunique()} keywords have Quality Score <= {config.low_quality_score_threshold}.",
                    impact="Low Quality Score can inflate CPC and reduce impression share.",
                    recommendation="Split weak keywords into tighter ad groups, improve ad copy relevance, and align landing pages.",
                    metrics={"low_quality_keyword_count": int(low_qs["keyword"].nunique())},
                )
            )

    if "match_type" in df.columns:
        match_spend = keyword_df.groupby("match_type")["cost"].sum()
        broad_cost = float(match_spend[match_spend.index.astype(str).str.lower().str.contains("broad|部分一致")].sum())
        total_cost = float(match_spend.sum())
        broad_share = broad_cost / total_cost if total_cost else 0
        metrics["broad_match_spend_share"] = broad_share
        if broad_share >= config.broad_match_share_warning:
            findings.append(
                finding(
                    title="Broad match appears to control a large share of spend",
                    priority=Priority.HIGH,
                    category="Keyword Audit",
                    reason="Broad match can expand into weaker intent queries when negatives and bidding signals are insufficient.",
                    evidence=f"Broad match spend share is {pct(broad_share * 100)}.",
                    impact="Query quality can deteriorate quickly, especially in urgent local services.",
                    recommendation="Review broad-match search terms, add negatives, and promote proven queries into exact/phrase match.",
                    metrics={"broad_cost": broad_cost, "total_cost": total_cost, "broad_share": broad_share},
                )
            )

    duplicate_dims = ["keyword", "match_type"]
    if set(duplicate_dims).issubset(df.columns):
        duplicates = df.groupby(duplicate_dims)["campaign"].nunique().reset_index(name="campaign_count")
        duplicates = duplicates[duplicates["campaign_count"] > 1]
        if not duplicates.empty:
            findings.append(
                finding(
                    title="Duplicate keywords found across campaigns",
                    priority=Priority.LOW,
                    category="Keyword Audit",
                    reason="Duplicate keywords can split learning and create internal auction overlap.",
                    evidence=f"{len(duplicates)} keyword/match-type combinations appear in multiple campaigns.",
                    impact="Budget and bidding signals may be fragmented.",
                    recommendation="Consolidate duplicates or separate them by clear geography/service intent.",
                    metrics={"duplicate_keyword_count": int(len(duplicates))},
                )
            )

    return findings, metrics
