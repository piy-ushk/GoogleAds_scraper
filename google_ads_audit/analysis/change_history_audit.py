from __future__ import annotations

import re

import pandas as pd

from google_ads_audit.analysis.helpers import finding
from google_ads_audit.config import AuditConfig
from google_ads_audit.models import AuditFinding, Priority

IMPORTANT_CHANGE_PATTERNS = {
    "Budget changes": r"budget|予算",
    "Bid strategy changes": r"bid strateg|bidding|入札|目標コンバージョン単価|maximize",
    "Keyword additions": r"keyword.*add|added keyword|キーワード.*追加",
    "Keyword removals": r"keyword.*remove|removed keyword|キーワード.*削除",
    "Campaign edits": r"campaign|キャンペーン",
    "Conversion edits": r"conversion|コンバージョン",
}


def audit_change_history(df: pd.DataFrame, performance_df: pd.DataFrame, config: AuditConfig) -> tuple[list[AuditFinding], dict]:
    findings: list[AuditFinding] = []
    if df.empty:
        return findings, {}

    text_columns = [column for column in ["change_type", "change_detail"] if column in df.columns]
    combined = df[text_columns].astype(str).agg(" ".join, axis=1) if text_columns else pd.Series("", index=df.index)
    metrics = {"major_changes": []}

    for label, pattern in IMPORTANT_CHANGE_PATTERNS.items():
        matches = df[combined.str.lower().str.contains(pattern, regex=True, na=False)]
        if not matches.empty:
            examples = matches.head(5).to_dict("records")
            metrics["major_changes"].append({"type": label, "count": int(len(matches)), "examples": examples})
            priority = Priority.HIGH if re.search("Bid|Budget|Conversion", label) else Priority.MEDIUM
            findings.append(
                finding(
                    title=label + " detected in change history",
                    priority=priority,
                    category="Change History Audit",
                    reason="Major account changes can explain sudden CPA/CVR movement.",
                    evidence=f"{len(matches)} matching change-history rows found.",
                    impact="Performance should be compared immediately before and after these changes.",
                    recommendation="Open these changes in Google Ads and verify whether performance shifted after the edit dates.",
                    metrics={"examples": examples, "count": int(len(matches))},
                )
            )

    if "change_date" in df.columns and "date" in performance_df.columns and not performance_df.empty:
        dated_changes = df.dropna(subset=["change_date"]).sort_values("change_date")
        comparisons = []
        daily = performance_df.groupby("date", dropna=False)[["cost", "clicks", "impressions", "conversions"]].sum()
        daily = daily.reset_index()
        for _, change in dated_changes.head(20).iterrows():
            change_date = change["change_date"]
            before = daily[(daily["date"] >= change_date - pd.Timedelta(days=14)) & (daily["date"] < change_date)]
            after = daily[(daily["date"] > change_date) & (daily["date"] <= change_date + pd.Timedelta(days=14))]
            if before.empty or after.empty:
                continue
            before_cpa = before["cost"].sum() / before["conversions"].sum() if before["conversions"].sum() else 0
            after_cpa = after["cost"].sum() / after["conversions"].sum() if after["conversions"].sum() else 0
            if before_cpa and after_cpa > before_cpa * 1.25:
                comparisons.append(
                    {
                        "change_date": str(change_date.date()),
                        "before_cpa": before_cpa,
                        "after_cpa": after_cpa,
                        "change": change.to_dict(),
                    }
                )
        metrics["before_after_change_checks"] = comparisons
        if comparisons:
            first = comparisons[0]
            findings.append(
                finding(
                    title="Performance worsened after a recorded account change",
                    priority=Priority.HIGH,
                    category="Change History Audit",
                    reason="A before/after window around change history shows CPA deterioration.",
                    evidence=f"After {first['change_date']}, 14-day CPA rose from {first['before_cpa']:.0f} to {first['after_cpa']:.0f}.",
                    impact="This is a strong candidate driver of the decline and should be manually validated.",
                    recommendation="Inspect the exact change, affected campaign, and whether reverting or segmenting is appropriate.",
                    metrics=first,
                )
            )

    return findings, metrics
