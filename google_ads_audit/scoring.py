from __future__ import annotations

import pandas as pd

from google_ads_audit.models import AuditFinding, Priority, ScoreBreakdown


def compute_scores(findings: list[AuditFinding], reports: dict) -> ScoreBreakdown:
    penalties = {
        "Campaign Audit": _category_penalty(findings, "Campaign Audit"),
        "Keyword Audit": _category_penalty(findings, "Keyword Audit"),
        "Search Term Audit": _category_penalty(findings, "Search Term Audit"),
        "Conversion Audit": _category_penalty(findings, "Conversion Audit"),
        "Landing Page Audit": _category_penalty(findings, "Landing Page Audit"),
        "Auction Audit": _category_penalty(findings, "Auction Audit"),
    }

    return ScoreBreakdown(
        campaign_structure=_score(100 - penalties["Campaign Audit"]),
        keyword_quality=_score(100 - penalties["Keyword Audit"]),
        budget_efficiency=_score(100 - penalties["Campaign Audit"] * 0.6 - penalties["Search Term Audit"] * 0.6),
        conversion_tracking=_score(100 - penalties["Conversion Audit"]),
        ctr=_score(_metric_score(reports, "ctr")),
        cpa=_score(100 - penalties["Conversion Audit"] * 0.5 - penalties["Campaign Audit"] * 0.4),
        search_terms=_score(100 - penalties["Search Term Audit"]),
        landing_pages=_score(100 - penalties["Landing Page Audit"]),
        competition=_score(100 - penalties["Auction Audit"]),
    )


def _category_penalty(findings: list[AuditFinding], category: str) -> float:
    penalty = 0.0
    for item in findings:
        if item.category != category:
            continue
        if item.priority == Priority.HIGH:
            penalty += 24
        elif item.priority == Priority.MEDIUM:
            penalty += 12
        else:
            penalty += 5
    return min(penalty, 75)


def _score(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def _metric_score(reports: dict, metric: str) -> float:
    frames = [frame for frame in reports.values() if isinstance(frame, pd.DataFrame) and metric in frame.columns]
    if not frames:
        return 70.0
    combined = pd.concat(frames, ignore_index=True)
    if metric == "ctr":
        if {"clicks", "impressions"}.issubset(combined.columns):
            ctr = combined["clicks"].sum() / combined["impressions"].replace(0, pd.NA).sum() * 100
        else:
            ctr = combined[metric].mean()
        if ctr >= 8:
            return 95
        if ctr >= 5:
            return 85
        if ctr >= 3:
            return 70
        if ctr >= 1.5:
            return 50
        return 30
    return 70.0
