from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def generate_ai_summary(metrics: dict[str, Any], api_key: str | None = None, model: str = "gpt-4.1-mini") -> str | None:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        payload = json.dumps(metrics, ensure_ascii=False, default=str)[:80_000]
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior Google Ads consultant. Explain only the computed metrics "
                        "provided by Python. Do not invent data. Every claim must reference a metric "
                        "or finding from the JSON. Keep the report concise, practical, and prioritized."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Write an executive audit narrative from this structured metrics JSON. "
                        "Include the likely drivers, risks, and priority actions.\n\n" + payload
                    ),
                },
            ],
        )
        return response.output_text
    except Exception as exc:  # pragma: no cover - optional external service
        logger.warning("AI summary generation failed: %s", exc)
        return None
