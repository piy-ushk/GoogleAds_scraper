from __future__ import annotations

import re
from collections.abc import Iterable

from google_ads_audit.models import ReportType


CANONICAL_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "day", "日", "日付"),
    "campaign": ("campaign", "campaign name", "キャンペーン", "キャンペーン名"),
    "campaign_status": ("campaign status", "status", "キャンペーンのステータス"),
    "ad_group": ("ad group", "ad group name", "広告グループ", "広告グループ名"),
    "ad_group_status": ("ad group status", "広告グループのステータス"),
    "keyword": ("keyword", "keyword text", "キーワード"),
    "search_term": ("search term", "search terms", "検索語句", "検索語句テキスト"),
    "match_type": ("match type", "keyword match type", "マッチタイプ", "キーワードのマッチタイプ", "マッチ タイプ"),
    "quality_score": ("quality score", "品質スコア"),
    "ad": ("ad", "ad name", "広告"),
    "final_url": ("final url", "final urls", "landing page", "landing page url", "最終ページ url"),
    "device": ("device", "デバイス"),
    "location": ("location", "matched location", "region", "city", "地域", "都市"),
    "competitor": ("domain", "display url domain", "competitor", "競合", "表示 URL ドメイン", "表示urlドメイン"),
    "change_date": ("change date", "date/time", "日時", "変更日時"),
    "change_type": ("change type", "変更タイプ"),
    "changed_by": ("user", "changed by", "変更ユーザー"),
    "change_detail": ("change", "changes", "details", "変更内容", "詳細"),
    "conversion_action": ("conversion action", "コンバージョン アクション"),
    "impressions": ("impr.", "impressions", "表示回数", "インプレッション数"),
    "clicks": ("clicks", "クリック数", "クリック"),
    "cost": ("cost", "cost (converted currency)", "費用", "コスト", "ご利用金額", "金額"),
    "ctr": ("ctr", "クリック率"),
    "avg_cpc": ("avg. cpc", "average cpc", "平均クリック単価", "平均 cpc"),
    "conversions": ("conversions", "conv.", "コンバージョン", "コンバージョン数"),
    "conversion_rate": ("conv. rate", "conversion rate", "コンバージョン率"),
    "cost_per_conversion": ("cost / conv.", "cost per conversion", "コンバージョン単価", "費用 / コンバージョン"),
    "conversion_value": ("conversion value", "conv. value", "コンバージョン値"),
    "impression_share": ("search impr. share", "impr. share", "インプレッション シェア", "インプレッションシェア", "検索のインプレッション シェア"),
    "top_impression_rate": ("search top is", "top impr. rate", "ページ上部表示率"),
    "absolute_top_impression_rate": (
        "search abs. top is",
        "absolute top impr. rate",
        "ページ最上部表示率",
    ),
    "overlap_rate": ("overlap rate", "重複率"),
    "outranking_share": ("outranking share", "上位掲載率"),
    "lost_is_budget": ("search lost is (budget)", "予算による損失インプレッション シェア"),
    "lost_is_rank": ("search lost is (rank)", "ランクによる損失インプレッション シェア"),
    "hour": ("hour", "hour of day", "時間"),
    "day_of_week": ("day of week", "曜日"),
}


REPORT_SIGNATURES: dict[ReportType, set[str]] = {
    ReportType.SEARCH_TERMS: {"search_term", "campaign"},
    ReportType.KEYWORDS: {"keyword", "match_type"},
    ReportType.AUCTION_INSIGHTS: {"competitor", "impression_share", "overlap_rate"},
    ReportType.CHANGE_HISTORY: {"change_type", "change_detail"},
    ReportType.LANDING_PAGES: {"final_url"},
    ReportType.DEVICES: {"device"},
    ReportType.LOCATIONS: {"location"},
    ReportType.AD_GROUPS: {"ad_group", "campaign"},
    ReportType.ADS: {"ad", "campaign"},
    ReportType.CONVERSIONS: {"conversion_action"},
    ReportType.CAMPAIGNS: {"campaign"},
}


def normalize_column_name(name: str) -> str:
    cleaned = str(name).strip().replace("\ufeff", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.lower()


def canonicalize_columns(columns: Iterable[str]) -> dict[str, str]:
    normalized = {column: normalize_column_name(column) for column in columns}
    mapping: dict[str, str] = {}
    for original, normalized_name in normalized.items():
        for canonical, aliases in CANONICAL_COLUMN_ALIASES.items():
            if normalized_name == canonical or normalized_name in aliases:
                mapping[original] = canonical
                break
    return mapping


def detect_report_type(columns: Iterable[str]) -> ReportType:
    canonical_columns = set(canonicalize_columns(columns).values())
    for report_type, required_columns in REPORT_SIGNATURES.items():
        if required_columns.issubset(canonical_columns):
            return report_type
    if "campaign" in canonical_columns:
        return ReportType.CAMPAIGNS
    return ReportType.UNKNOWN
