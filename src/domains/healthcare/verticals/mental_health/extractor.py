"""Mental health entity extractor — uses Claude to extract structured mental health data."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a mental health data analyzer. Extract all mental health entities from the following text and return a JSON object with this exact structure:

{
  "therapy_sessions": [{"date": "", "therapist": "", "type": "CBT|DBT|psychodynamic|other", "notes_summary": "", "mood_at_session": 0}],
  "mood_entries": [{"date": "", "score": 0, "notes": "", "triggers": "", "energy_level": 0, "anxiety_level": 0}],
  "mental_conditions": [{"name": "", "diagnosed_date": "", "status": "active|resolved|managed", "treating_provider": ""}],
  "stressors": [{"description": "", "category": "work|relationship|health|financial|other", "intensity": 0, "start_date": "", "resolved_date": ""}],
  "journal_entries": [{"date": "", "text_summary": "", "sentiment": "positive|neutral|negative", "key_themes": ""}],
  "meditation_sessions": [{"date": "", "duration_mins": 0, "type": "", "app_used": "", "notes": ""}]
}

Scores are 1-10 integers. Return only valid JSON. Use ISO dates (YYYY-MM-DD). Empty arrays [] if no entities found.

Document text:
"""


class MentalHealthExtractor:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._client

    def extract(self, text: str, metadata: dict | None = None) -> dict[str, Any]:
        if not text.strip():
            return self._empty_result()
        try:
            client = self._get_client()
            response = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                max_tokens=4096,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT + text[:8000]}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return self._normalize(json.loads(raw))
        except Exception as e:
            logger.warning("Claude mental health extraction failed: %s", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        keys = ["therapy_sessions", "mood_entries", "mental_conditions",
                "stressors", "journal_entries", "meditation_sessions"]
        return {k: data.get(k, []) for k in keys}

    def _empty_result(self) -> dict:
        return {k: [] for k in ["therapy_sessions", "mood_entries", "mental_conditions",
                                  "stressors", "journal_entries", "meditation_sessions"]}
