from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from google_ads_audit.models import AuditFinding, AuditResult


def export_json(result: AuditResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scores": result.scores.as_dict(),
        "findings": [finding.__dict__ for finding in result.findings],
        "metrics": result.metrics,
        "ai_summary": result.ai_summary,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return path


def export_excel(result: AuditResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame([result.scores.as_dict()]).to_excel(writer, sheet_name="Scores", index=False)
        _findings_dataframe(result.findings).to_excel(writer, sheet_name="Findings", index=False)
        for report_type, frame in result.reports.items():
            sheet = report_type.value[:31]
            frame.head(50_000).to_excel(writer, sheet_name=sheet, index=False)
    return path


def export_pdf(result: AuditResult, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story: list[Any] = []

    story.append(Paragraph("Google Ads Audit Report", styles["Title"]))
    story.append(Paragraph("Executive Summary", styles["Heading1"]))
    if result.ai_summary:
        story.append(Paragraph(_escape(result.ai_summary).replace("\n", "<br/>"), styles["BodyText"]))
    else:
        story.append(
            Paragraph(
                "This report was generated from uploaded Google Ads CSV exports. Findings are based on computed metrics, not raw AI interpretation.",
                styles["BodyText"],
            )
        )
    story.append(Spacer(1, 8))

    story.append(Paragraph("Account Health Score", styles["Heading1"]))
    score_rows = [["Area", "Score"]] + [[key, value] for key, value in result.scores.as_dict().items()]
    story.append(_table(score_rows, [115 * mm, 35 * mm]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Major Findings", styles["Heading1"]))
    for item in result.findings[:20]:
        story.append(Paragraph(f"{item.priority.value}: {_escape(item.title)}", styles["Heading2"]))
        story.append(Paragraph(f"<b>Reason:</b> {_escape(item.reason)}", styles["Small"]))
        story.append(Paragraph(f"<b>Evidence:</b> {_escape(item.evidence)}", styles["Small"]))
        story.append(Paragraph(f"<b>Impact:</b> {_escape(item.impact)}", styles["Small"]))
        story.append(Paragraph(f"<b>Recommendation:</b> {_escape(item.recommendation)}", styles["Small"]))
        story.append(Spacer(1, 5))

    story.append(Paragraph("Priority Action Plan", styles["Heading1"]))
    actions = [
        [item.priority.value, item.category, item.recommendation]
        for item in result.findings[:15]
    ]
    story.append(_table([["Priority", "Area", "Action"]] + actions, [22 * mm, 38 * mm, 90 * mm]))
    doc.build(story)
    return path


def _findings_dataframe(findings: list[AuditFinding]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Priority": item.priority.value,
                "Category": item.category,
                "Issue": item.title,
                "Reason": item.reason,
                "Evidence": item.evidence,
                "Impact": item.impact,
                "Recommendation": item.recommendation,
                "Metrics": json.dumps(item.metrics, ensure_ascii=False, default=str),
            }
            for item in findings
        ]
    )


def _table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )
    return table


def _escape(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
