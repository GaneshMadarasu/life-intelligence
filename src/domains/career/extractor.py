"""Career entity extractor — uses Claude to pull structured data from career documents."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a career document analyzer. Extract all career entities from the following text and return a JSON object with this exact structure:

{
  "jobs": [{"title": "", "company": "", "location": "", "start_date": "", "end_date": "", "description": "", "employment_type": "full-time|part-time|contract|internship|freelance", "is_current": false, "salary": null, "currency": "USD"}],
  "skills": [{"name": "", "category": "technical|soft|language|tool|framework|certification", "proficiency": "beginner|intermediate|advanced|expert", "years_experience": null, "last_used_date": ""}],
  "education": [{"institution": "", "degree": "", "field_of_study": "", "start_date": "", "end_date": "", "gpa": null, "honors": "", "is_complete": true}],
  "certifications": [{"name": "", "issuer": "", "issued_date": "", "expiry_date": "", "credential_id": ""}],
  "achievements": [{"title": "", "description": "", "date": "", "context": ""}],
  "projects": [{"name": "", "description": "", "role": "", "start_date": "", "end_date": "", "technologies": [], "url": ""}]
}

Return only valid JSON. Use empty arrays [] if no entities found. ISO 8601 dates. Leave numerics as null if not mentioned.

Document text:
"""


class CareerExtractor:
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
            result = json.loads(raw)
            return self._normalize(result)
        except Exception as e:
            logger.warning("Career extraction failed: %s — using empty result", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        keys = ["jobs", "skills", "education", "certifications", "achievements", "projects"]
        return {k: data.get(k, []) for k in keys}

    def _empty_result(self) -> dict:
        return {
            "jobs": [], "skills": [], "education": [],
            "certifications": [], "achievements": [], "projects": [],
        }
