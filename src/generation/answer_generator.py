"""Answer generator — personal QA using Claude, cross-domain aware, safety-first."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a personal life intelligence assistant with access to the user's health, financial, legal, and career data stored in a private local knowledge graph.

Your role:
- Answer questions using the provided context from the user's personal records
- Be precise and cite specific data (dates, values, names) when available
- Flag SAFETY WARNINGS prominently — drug interactions, insurance gaps, overdue screenings
- Highlight cross-domain insights when you detect connections across domains
- Be concise but complete. Never hallucinate data not in the context.
- Always respect privacy — this is the user's own private data

Format your response as:
1. Direct answer to the question
2. Key facts supporting the answer (bulleted)
3. Cross-domain insights (if any)
4. Safety warnings (if any) — lead with HIGH severity

If context is insufficient, say so clearly rather than guessing."""


class AnswerGenerator:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._client

    def generate(
        self,
        question: str,
        context: str,
        domains: list[str] | None = None,
        cross_domain_insights: list[dict] | None = None,
        warnings: dict | None = None,
    ) -> dict[str, Any]:
        if not context.strip():
            return {
                "answer": "I don't have enough data in your knowledge base to answer this question. Please ingest relevant documents first.",
                "key_facts": [],
                "cross_domain_insights": [],
                "warnings": [],
                "sources": [],
                "confidence": "low",
            }

        warning_text = ""
        if warnings and warnings.get("high"):
            warning_text = "\n\nSAFETY WARNINGS (HIGH SEVERITY):\n" + "\n".join(
                f"- {w['message']}" for w in warnings["high"]
            )

        insights_text = ""
        if cross_domain_insights:
            insights_text = "\n\nCROSS-DOMAIN CONNECTIONS DETECTED:\n" + "\n".join(
                f"- {i.get('from_type', '')} '{i.get('from_name', '')}' "
                f"→ {i.get('relationship', '')} → "
                f"{i.get('to_type', '')} '{i.get('to_name', '')}'"
                for i in cross_domain_insights[:5]
            )

        user_message = f"""Question: {question}

Personal data context:
{context[:6000]}
{warning_text}
{insights_text}

Please answer based on the provided personal data context."""

        try:
            client = self._get_client()
            response = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            answer_text = response.content[0].text

            return {
                "answer": answer_text,
                "key_facts": self._extract_bullet_points(answer_text),
                "cross_domain_insights": cross_domain_insights or [],
                "warnings": warnings.get("warnings", []) if warnings else [],
                "sources": self._extract_sources(context),
                "confidence": "high" if len(context) > 500 else "medium",
            }
        except Exception as e:
            logger.error("Answer generation failed: %s", e)
            return {
                "answer": f"Error generating answer: {str(e)}",
                "key_facts": [],
                "cross_domain_insights": cross_domain_insights or [],
                "warnings": warnings.get("warnings", []) if warnings else [],
                "sources": [],
                "confidence": "low",
            }

    def _extract_bullet_points(self, text: str) -> list[str]:
        lines = text.split("\n")
        bullets = [
            line.lstrip("•-* ").strip()
            for line in lines
            if line.strip().startswith(("•", "-", "*", "- "))
        ]
        return bullets[:10]

    def _extract_sources(self, context: str) -> list[str]:
        sources = []
        for line in context.split("\n"):
            if "source_file" in line.lower() or ".pdf" in line.lower() or ".json" in line.lower():
                sources.append(line.strip()[:100])
        return list(set(sources))[:5]
