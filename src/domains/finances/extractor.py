"""Finance entity extractor — uses Claude to pull structured data from financial documents."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a financial document analyzer. Extract all financial entities from the following text and return a JSON object with this exact structure:

{
  "accounts": [{"name": "", "type": "checking|savings|investment|credit|loan|mortgage", "institution": "", "account_number_last4": "", "balance": null, "currency": "USD", "opened_date": "", "status": "active|closed"}],
  "transactions": [{"description": "", "amount": null, "type": "debit|credit", "category": "", "date": "", "account": "", "merchant": ""}],
  "investments": [{"symbol": "", "name": "", "asset_type": "stock|etf|bond|crypto|real_estate|other", "quantity": null, "price_per_unit": null, "total_value": null, "purchase_date": "", "account": ""}],
  "insurance_plans": [{"plan_name": "", "insurer": "", "type": "health|life|auto|home|disability|other", "premium_monthly": null, "deductible": null, "coverage_limit": null, "start_date": "", "end_date": "", "policy_number": ""}],
  "tax_items": [{"year": "", "type": "W2|1099|deduction|credit|payment", "amount": null, "description": "", "issuer": ""}],
  "debts": [{"name": "", "type": "credit_card|student_loan|mortgage|auto|personal|other", "balance": null, "interest_rate": null, "minimum_payment": null, "due_date": ""}]
}

Return only valid JSON. Use empty arrays [] if no entities of a type are found. Use ISO 8601 date format (YYYY-MM-DD). Leave numeric fields as null if not mentioned. Leave string fields as "" if not mentioned.

Document text:
"""


class FinanceExtractor:
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
            logger.warning("Finance extraction failed: %s — using empty result", e)
            return self._empty_result()

    def _normalize(self, data: dict) -> dict:
        keys = ["accounts", "transactions", "investments", "insurance_plans", "tax_items", "debts"]
        return {k: data.get(k, []) for k in keys}

    def _empty_result(self) -> dict:
        return {
            "accounts": [], "transactions": [], "investments": [],
            "insurance_plans": [], "tax_items": [], "debts": [],
        }
