"""Fitness entity extractor — uses Claude to extract structured fitness data."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a fitness and nutrition data analyzer. Extract all fitness entities from the following text and return a JSON object with this exact structure:

{
  "workouts": [{"type": "", "date": "", "duration_mins": 0, "calories_burned": 0, "intensity": "low|moderate|high", "notes": ""}],
  "exercises": [{"name": "", "sets": 0, "reps": 0, "weight": "", "duration_mins": 0, "workout_date": ""}],
  "meals": [{"name": "", "date": "", "calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "meal_type": "breakfast|lunch|dinner|snack"}],
  "body_metrics": [{"type": "weight|bmi|body_fat|muscle_mass", "value": "", "unit": "", "date": ""}],
  "supplements": [{"name": "", "dosage": "", "frequency": "", "brand": "", "purpose": ""}],
  "fitness_goals": [{"description": "", "target_date": "", "target_value": "", "metric": "", "status": "active|achieved|abandoned"}],
  "sleep_records": [{"date": "", "duration_hours": 0, "quality": 0, "deep_sleep_hours": 0, "notes": ""}]
}

Return only valid JSON. Use empty arrays [] if no entities found. Use ISO dates (YYYY-MM-DD).

Document text:
"""


class FitnessExtractor:
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
            logger.warning("Claude fitness extraction failed: %s", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        keys = ["workouts", "exercises", "meals", "body_metrics",
                "supplements", "fitness_goals", "sleep_records"]
        return {k: data.get(k, []) for k in keys}

    def _empty_result(self) -> dict:
        return {k: [] for k in ["workouts", "exercises", "meals", "body_metrics",
                                 "supplements", "fitness_goals", "sleep_records"]}
