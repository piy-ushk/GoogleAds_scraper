from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from google_ads_audit.columns import canonicalize_columns, detect_report_type
from google_ads_audit.models import ImportedReport, ReportType

logger = logging.getLogger(__name__)

NUMERIC_COLUMNS = {
    "impressions",
    "clicks",
    "cost",
    "ctr",
    "avg_cpc",
    "conversions",
    "conversion_rate",
    "cost_per_conversion",
    "conversion_value",
    "impression_share",
    "top_impression_rate",
    "absolute_top_impression_rate",
    "overlap_rate",
    "outranking_share",
    "lost_is_budget",
    "lost_is_rank",
    "quality_score",
}

PERCENT_COLUMNS = {
    "ctr",
    "conversion_rate",
    "impression_share",
    "top_impression_rate",
    "absolute_top_impression_rate",
    "overlap_rate",
    "outranking_share",
    "lost_is_budget",
    "lost_is_rank",
}

DATE_COLUMNS = {"date", "change_date"}


def read_google_ads_csv(path_or_buffer: Any, source_name: str | None = None) -> ImportedReport:
    if hasattr(path_or_buffer, "seek"):
        path_or_buffer.seek(0)
    try:
        dataframe = pd.read_csv(path_or_buffer, encoding="utf-8-sig", skip_blank_lines=True)
    except UnicodeDecodeError:
        if hasattr(path_or_buffer, "seek"):
            path_or_buffer.seek(0)
        dataframe = pd.read_csv(path_or_buffer, encoding="cp932", skip_blank_lines=True)
    original_columns = list(dataframe.columns)
    dataframe = clean_dataframe(dataframe)
    report_type = detect_report_type(original_columns)
    if report_type == ReportType.UNKNOWN:
        report_type = detect_report_type(dataframe.columns)
    return ImportedReport(
        report_type=report_type,
        source_name=source_name or getattr(path_or_buffer, "name", "uploaded_csv"),
        dataframe=dataframe,
        original_columns=original_columns,
    )


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    df = df.dropna(how="all")
    df.columns = [column.strip().replace("\ufeff", "") for column in df.columns]
    df = df.rename(columns=canonicalize_columns(df.columns))
    df = _remove_summary_rows(df)
    for column in df.columns:
        if column in NUMERIC_COLUMNS:
            df[column] = df[column].map(_parse_number)
        elif column in DATE_COLUMNS:
            parsed = pd.to_datetime(df[column], errors="coerce")
            if hasattr(parsed, "dt") and parsed.dt.tz is not None:
                parsed = parsed.dt.tz_convert(None)
            df[column] = parsed
        elif df[column].dtype == object:
            df[column] = df[column].astype(str).str.strip().replace({"nan": np.nan, "--": np.nan})
    df = df.drop_duplicates()
    df = _derive_metrics(df)
    return df


def _remove_summary_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    first_col = df.columns[0]
    mask = ~df[first_col].astype(str).str.lower().str.contains(
        r"^total|^合計|^総計|^account total", regex=True, na=False
    )
    return df.loc[mask].copy()


def _parse_number(value: Any) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip()
    if text in {"", "--", "nan", "None"}:
        return 0.0
    multiplier = 1.0
    if text.endswith("%"):
        multiplier = 1.0
    text = text.replace("%", "")
    text = re.sub(r"[¥￥$,，€£\s]", "", text)
    text = text.replace("−", "-")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text) * multiplier
    except ValueError:
        logger.debug("Unable to parse numeric value %r", value)
        return 0.0


def _derive_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if {"clicks", "impressions"}.issubset(df.columns):
        df["ctr"] = _safe_divide(df["clicks"], df["impressions"]) * 100
    if {"conversions", "clicks"}.issubset(df.columns):
        df["conversion_rate"] = _safe_divide(df["conversions"], df["clicks"]) * 100
    if {"cost", "conversions"}.issubset(df.columns):
        df["cost_per_conversion"] = _safe_divide(df["cost"], df["conversions"])
    if {"cost", "clicks"}.issubset(df.columns):
        df["avg_cpc"] = _safe_divide(df["cost"], df["clicks"])
    return df


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return (numerator / denominator).replace([np.inf, -np.inf], np.nan).fillna(0)


def merge_reports(imported_reports: list[ImportedReport]) -> dict[ReportType, pd.DataFrame]:
    grouped: dict[ReportType, list[pd.DataFrame]] = {}
    for report in imported_reports:
        grouped.setdefault(report.report_type, []).append(report.dataframe)
    return {
        report_type: pd.concat(frames, ignore_index=True).drop_duplicates()
        for report_type, frames in grouped.items()
    }
