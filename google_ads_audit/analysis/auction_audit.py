from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import finding, pct
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_auction(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    if df.empty:
        return findings, {}

    metrics = {"competitors": df.head(config.top_n_rows).to_dict("records")}
    if "competitor" not in df.columns:
        return findings, metrics

    for column in ["impression_share", "overlap_rate", "top_impression_rate", "outranking_share"]:
        if column not in df.columns:
            df[column] = 0

    competitors = df.sort_values(["impression_share", "overlap_rate"], ascending=False).head(5)
    if not competitors.empty:
        leader = competitors.iloc[0]
        findings.append(
            finding(
                title=f"Competitor '{leader['competitor']}' is prominent in auctions",
                priority=Priority.MEDIUM,
                category="Auction Audit",
                reason="Auction insights show a competitor with strong visibility or overlap.",
                evidence=f"Impression share {pct(leader['impression_share'])}, overlap rate {pct(leader['overlap_rate'])}, top-of-page rate {pct(leader['top_impression_rate'])}.",
                impact="Competitive pressure can raise CPC and reduce absolute top visibility.",
                recommendation="Compare ad copy, emergency response claims, service areas, and bid pressure for the affected campaigns.",
                metrics=leader.to_dict(),
            )
        )

    return findings, metrics
