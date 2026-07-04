from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance, finding, money
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_landing_pages(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    page_df = aggregate_performance(df, ["final_url"])
    if page_df.empty:
        return findings, {}

    metrics = {"landing_pages": page_df.head(config.top_n_rows).to_dict("records")}
    invalid = page_df[~page_df["final_url"].astype(str).str.startswith(("http://", "https://"))]
    if not invalid.empty:
        findings.append(
            finding(
                title="Landing page URLs need validation",
                priority=Priority.HIGH,
                category="Landing Page Audit",
                reason="Some final URLs do not look like valid HTTP/HTTPS landing pages.",
                evidence=f"{len(invalid)} landing page rows have invalid-looking URLs.",
                impact="Broken or malformed URLs can destroy conversion rate and waste spend.",
                recommendation="Manually test all flagged final URLs and fix redirects, 404s, or tracking-template issues.",
                metrics={"invalid_urls": invalid.head(20).to_dict("records")},
            )
        )

    poor = page_df[(page_df["cost"] >= config.zero_conversion_spend_min) & (page_df["conversions"] == 0)]
    for _, row in poor.head(5).iterrows():
        findings.append(
            finding(
                title="Landing page spending without conversions",
                priority=Priority.HIGH,
                category="Landing Page Audit",
                reason="This landing page has cost but no recorded conversions.",
                evidence=f"{row['final_url']} spent {money(row['cost'], config.currency)} with 0 conversions.",
                impact="The page may be mismatched to query intent or have UX/tracking issues.",
                recommendation="Check page speed, mobile layout, phone CTA visibility, form tracking, and message match.",
                metrics=row.to_dict(),
            )
        )

    return findings, metrics
