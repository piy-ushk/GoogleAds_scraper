from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AuditConfig:
    currency: str = "JPY"
    high_spend_min: float = 50_000
    zero_conversion_spend_min: float = 30_000
    poor_ctr_threshold: float = 2.0
    poor_cvr_threshold: float = 2.0
    high_cpa_multiplier: float = 1.5
    low_quality_score_threshold: float = 5
    broad_match_share_warning: float = 0.5
    top_n_rows: int = 15
    before_period_label: str = "Before decline"
    after_period_label: str = "After decline"
    irrelevant_search_terms: list[str] = field(default_factory=list)


def load_config(path: str | Path = "config/audit_config.yml") -> AuditConfig:
    config_path = Path(path)
    if not config_path.exists():
        return AuditConfig()
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    valid_keys = AuditConfig.__dataclass_fields__.keys()
    return AuditConfig(**{key: value for key, value in raw.items() if key in valid_keys})
