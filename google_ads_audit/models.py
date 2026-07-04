from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd


class ReportType(StrEnum):
    CAMPAIGNS = "campaigns"
    AD_GROUPS = "ad_groups"
    KEYWORDS = "keywords"
    SEARCH_TERMS = "search_terms"
    ADS = "ads"
    DEVICES = "devices"
    LOCATIONS = "locations"
    AUCTION_INSIGHTS = "auction_insights"
    CHANGE_HISTORY = "change_history"
    CONVERSIONS = "conversions"
    LANDING_PAGES = "landing_pages"
    UNKNOWN = "unknown"


class Priority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass(frozen=True)
class ImportedReport:
    report_type: ReportType
    source_name: str
    dataframe: pd.DataFrame
    original_columns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AuditFinding:
    title: str
    priority: Priority
    category: str
    reason: str
    evidence: str
    impact: str
    recommendation: str
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreBreakdown:
    campaign_structure: float
    keyword_quality: float
    budget_efficiency: float
    conversion_tracking: float
    ctr: float
    cpa: float
    search_terms: float
    landing_pages: float
    competition: float

    @property
    def overall(self) -> float:
        values = [
            self.campaign_structure,
            self.keyword_quality,
            self.budget_efficiency,
            self.conversion_tracking,
            self.ctr,
            self.cpa,
            self.search_terms,
            self.landing_pages,
            self.competition,
        ]
        return round(sum(values) / len(values), 1)

    def as_dict(self) -> dict[str, float]:
        return {
            "Campaign Structure": round(self.campaign_structure, 1),
            "Keyword Quality": round(self.keyword_quality, 1),
            "Budget Efficiency": round(self.budget_efficiency, 1),
            "Conversion Tracking": round(self.conversion_tracking, 1),
            "CTR": round(self.ctr, 1),
            "CPA": round(self.cpa, 1),
            "Search Terms": round(self.search_terms, 1),
            "Landing Pages": round(self.landing_pages, 1),
            "Competition": round(self.competition, 1),
            "Overall": self.overall,
        }


@dataclass
class AuditResult:
    reports: dict[ReportType, pd.DataFrame]
    findings: list[AuditFinding]
    scores: ScoreBreakdown
    metrics: dict[str, Any]
    charts: dict[str, Any]
    ai_summary: str | None = None


PathLike = str | Path
