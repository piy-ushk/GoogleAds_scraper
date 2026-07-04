from __future__ import annotations

import pandas as pd

from google_ads_audit.analysis.helpers import aggregate_performance, finding, money
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority


def audit_search_terms(df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    term_df = aggregate_performance(df, ["search_term"])
    if term_df.empty:
        return findings, {}

    metrics = {
        "search_term_count": int(term_df["search_term"].nunique()),
        "top_search_terms": term_df.head(config.top_n_rows).to_dict("records"),
        "negative_keyword_suggestions": [],
        "exact_match_opportunities": [],
    }

    wasted = term_df[
        (term_df["cost"] >= config.zero_conversion_spend_min) & (term_df["conversions"] == 0)
    ]
    for _, row in wasted.head(10).iterrows():
        metrics["negative_keyword_suggestions"].append(str(row["search_term"]))
        findings.append(
            finding(
                title=f"Search term '{row['search_term']}' spent without conversions",
                priority=Priority.HIGH,
                category="Search Term Audit",
                reason="The query has consumed spend but generated no tracked conversions.",
                evidence=f"{money(row['cost'], config.currency)} spent across {int(row['clicks'])} clicks with 0 conversions.",
                impact="This is one of the clearest negative-keyword or targeting cleanup opportunities.",
                recommendation="Add as a negative keyword if irrelevant, or isolate into a dedicated exact/phrase ad group if strategically important.",
                metrics=row.to_dict(),
            )
        )

    if config.irrelevant_search_terms:
        pattern = "|".join([rf"\b{term}\b" for term in config.irrelevant_search_terms])
        irrelevant = term_df[
            term_df["search_term"].astype(str).str.lower().str.contains(pattern, regex=True, na=False)
        ]
        if not irrelevant.empty:
            metrics["negative_keyword_suggestions"].extend(
                irrelevant.sort_values("cost", ascending=False)["search_term"].astype(str).head(25).tolist()
            )
            findings.append(
                finding(
                    title="Irrelevant search intent detected",
                    priority=Priority.HIGH,
                    category="Search Term Audit",
                    reason="Search terms include informational, employment, free, or DIY intent patterns.",
                    evidence=f"{len(irrelevant)} search terms matched the configured irrelevant-intent list.",
                    impact="These searches can drain budget from urgent locksmith inquiries.",
                    recommendation="Review the suggested terms and add negatives at campaign/account level.",
                    metrics={"examples": irrelevant.head(10).to_dict("records")},
                )
            )

    opportunities = term_df[
        (term_df["conversions"] >= 2)
        & (term_df["cost_per_conversion"] > 0)
        & (term_df["cost_per_conversion"] <= term_df["cost_per_conversion"].replace(0, pd.NA).median())
    ].sort_values(["conversions", "cost_per_conversion"], ascending=[False, True])
    metrics["exact_match_opportunities"] = opportunities["search_term"].astype(str).head(20).tolist()
    if not opportunities.empty:
        best = opportunities.iloc[0]
        findings.append(
            finding(
                title="High-performing search terms should be promoted",
                priority=Priority.MEDIUM,
                category="Search Term Audit",
                reason="Some queries have proven conversion volume and efficient CPA.",
                evidence=f"'{best['search_term']}' generated {best['conversions']:.0f} conversions at {money(best['cost_per_conversion'], config.currency)} CPA.",
                impact="Keeping proven queries hidden inside broader matching limits control over bids and ad copy.",
                recommendation="Add top converting queries as exact match keywords with dedicated ad copy and location/device controls.",
                metrics={"opportunities": opportunities.head(10).to_dict("records")},
            )
        )

    metrics["negative_keyword_suggestions"] = sorted(set(metrics["negative_keyword_suggestions"]))
    return findings, metrics
