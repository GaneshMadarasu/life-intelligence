"""Medical entity extractor — uses Claude to pull structured data from medical documents."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a medical document analyzer. Extract all medical entities from the following text and return a JSON object with this exact structure:

{
  "conditions": [{"name": "", "icd_code": "", "status": "active|resolved|chronic", "diagnosed_date": "", "severity": "mild|moderate|severe"}],
  "medications": [{"name": "", "dosage": "", "frequency": "", "prescribed_date": "", "prescriber": "", "indication": ""}],
  "symptoms": [{"name": "", "severity": "mild|moderate|severe", "onset_date": "", "resolved_date": ""}],
  "lab_results": [{"test_name": "", "value": "", "unit": "", "reference_range": "", "date": "", "is_abnormal": false}],
  "vitals": [{"type": "", "value": "", "unit": "", "date": ""}],
  "allergies": [{"allergen": "", "reaction": "", "severity": "mild|moderate|severe|anaphylaxis", "discovered_date": ""}],
  "procedures": [{"name": "", "date": "", "provider": "", "location": "", "notes": ""}],
  "vaccines": [{"name": "", "date": "", "lot_number": "", "provider": ""}],
  "hospitalizations": [{"reason": "", "admit_date": "", "discharge_date": "", "facility": "", "discharge_summary": ""}],
  "providers": [{"name": "", "specialty": "", "institution": "", "contact": ""}]
}

Return only valid JSON. Use empty arrays [] if no entities of a type are found. Use ISO 8601 date format (YYYY-MM-DD) where dates are mentioned. Leave fields empty string "" if not mentioned.

Document text:
"""


class MedicalExtractor:
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
            # Strip markdown code fences if present
            raw = re.sub(r"^```json\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            result = json.loads(raw)
            return self._normalize(result)
        except Exception as e:
            logger.warning("Claude extraction failed: %s — falling back to empty result", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        keys = ["conditions", "medications", "symptoms", "lab_results", "vitals",
                "allergies", "procedures", "vaccines", "hospitalizations", "providers"]
        return {k: data.get(k, []) for k in keys}

    def _empty_result(self) -> dict:
        return {
            "conditions": [], "medications": [], "symptoms": [],
            "lab_results": [], "vitals": [], "allergies": [],
            "procedures": [], "vaccines": [], "hospitalizations": [], "providers": [],
        }
