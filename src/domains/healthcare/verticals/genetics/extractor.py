"""Genetics entity extractor — uses Claude to extract structured genetic data."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a genetics report analyzer. Extract all genetic entities from the following text and return a JSON object with this exact structure:

{
  "genes": [{"name": "", "chromosome": "", "function": ""}],
  "genetic_variants": [{"rsid": "", "gene": "", "variant_type": "SNP|deletion|insertion", "genotype": "", "significance": "pathogenic|benign|uncertain|risk_factor"}],
  "genetic_risks": [{"condition_name": "", "risk_level": "high|moderate|low", "genes_involved": [""], "recommendations": ""}],
  "pharmacogenes": [{"gene": "", "drug_metabolism": "poor|intermediate|normal|ultra_rapid", "affected_drugs": [""]}],
  "ancestry_segments": [{"population": "", "percentage": 0, "confidence": "high|moderate|low"}],
  "genetic_report": {"provider": "", "report_date": "", "test_type": "WGS|WES|SNP_array|carrier_screening|other"}
}

Return only valid JSON. Empty arrays [] if not found. Use gene names exactly as written (e.g., BRCA2, APOE, CYP2D6).

Document text:
"""


class GeneticsExtractor:
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
            logger.warning("Claude genetics extraction failed: %s", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        return {
            "genes": data.get("genes", []),
            "genetic_variants": data.get("genetic_variants", []),
            "genetic_risks": data.get("genetic_risks", []),
            "pharmacogenes": data.get("pharmacogenes", []),
            "ancestry_segments": data.get("ancestry_segments", []),
            "genetic_report": data.get("genetic_report", {}),
        }

    def _empty_result(self) -> dict:
        return {
            "genes": [], "genetic_variants": [], "genetic_risks": [],
            "pharmacogenes": [], "ancestry_segments": [], "genetic_report": {},
        }
