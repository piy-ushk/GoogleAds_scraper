from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from google_ads_audit.analysis.auction_audit import audit_auction
from google_ads_audit.analysis.campaign_audit import audit_campaigns
from google_ads_audit.analysis.change_history_audit import audit_change_history
from google_ads_audit.analysis.conversion_audit import audit_conversions
from google_ads_audit.analysis.keyword_audit import audit_keywords
from google_ads_audit.analysis.landing_page_audit import audit_landing_pages
from google_ads_audit.analysis.search_term_audit import audit_search_terms
from google_ads_audit.analysis.helpers import add_rate_metrics
from google_ads_audit.analysis.segment_audits import audit_segment
from google_ads_audit.cleaning import merge_reports
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditResult, ImportedReport, ReportType
from google_ads_audit.scoring import compute_scores
from google_ads_audit.visualization import build_charts

logger = logging.getLogger(__name__)


def run_audit(imported_reports: list[ImportedReport], config: AuditConfig) -> AuditResult:
    reports = merge_reports(imported_reports)
    findings = []
    metrics: dict[str, Any] = {"reports_loaded": {key.value: len(value) for key, value in reports.items()}}

    campaign_df = _report_or_performance(reports, ReportType.CAMPAIGNS)
    keyword_df = _report_or_performance(reports, ReportType.KEYWORDS)
    search_df = reports.get(ReportType.SEARCH_TERMS, pd.DataFrame())
    device_df = _report_or_performance(reports, ReportType.DEVICES, required_dimension="device")
    location_df = _report_or_performance(reports, ReportType.LOCATIONS, required_dimension="location")
    landing_df = _report_or_performance(reports, ReportType.LANDING_PAGES, required_dimension="final_url")
    performance_df = _best_performance(reports)

    module_outputs = [
        ("campaign_audit", audit_campaigns(campaign_df, config)),
        ("keyword_audit", audit_keywords(keyword_df, config)),
        ("search_term_audit", audit_search_terms(search_df, config)),
        ("conversion_audit", audit_conversions(performance_df, config)),
        ("device_audit", audit_segment(device_df, "device", "Device Audit", config)),
        ("location_audit", audit_segment(location_df, "location", "Location Audit", config)),
        ("time_day_audit", audit_segment(performance_df, "day_of_week", "Time Audit", config)),
        ("time_hour_audit", audit_segment(performance_df, "hour", "Time Audit", config)),
        ("auction_audit", audit_auction(reports.get(ReportType.AUCTION_INSIGHTS, pd.DataFrame()), config)),
        (
            "change_history_audit",
            audit_change_history(reports.get(ReportType.CHANGE_HISTORY, pd.DataFrame()), performance_df, config),
        ),
        ("landing_page_audit", audit_landing_pages(landing_df, config)),
    ]

    for name, (module_findings, module_metrics) in module_outputs:
        findings.extend(module_findings)
        metrics[name] = module_metrics

    findings.sort(key=lambda item: {"High": 0, "Medium": 1, "Low": 2}[item.priority.value])
    scores = compute_scores(findings, reports)
    charts = build_charts(reports)
    metrics["score_breakdown"] = scores.as_dict()
    metrics["top_findings"] = [finding.metrics | {"title": finding.title} for finding in findings[:10]]
    return AuditResult(reports=reports, findings=findings, scores=scores, metrics=metrics, charts=charts)


def _report_or_performance(
    reports: dict[ReportType, pd.DataFrame],
    report_type: ReportType,
    required_dimension: str | None = None,
) -> pd.DataFrame:
    report = reports.get(report_type)
    if report is not None and not report.empty:
        report = report.copy()
        for col in ["cost", "clicks", "impressions", "conversions"]:
            if col not in report.columns:
                report[col] = 0.0
        report = add_rate_metrics(report)
        return report
    return _best_performance(reports, required_dimension=required_dimension)


def _best_performance(
    reports: dict[ReportType, pd.DataFrame],
    required_dimension: str | None = None,
) -> pd.DataFrame:
    candidates = []
    for frame in reports.values():
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        if required_dimension and required_dimension not in frame.columns:
            continue
        if {"cost", "clicks", "impressions"}.issubset(frame.columns):
            candidates.append(frame)
    if not candidates:
        return pd.DataFrame()
    best = max(candidates, key=lambda frame: len(frame.columns)).copy()
    for col in ["cost", "clicks", "impressions", "conversions"]:
        if col not in best.columns:
            best[col] = 0.0
    best = add_rate_metrics(best)
    return best
