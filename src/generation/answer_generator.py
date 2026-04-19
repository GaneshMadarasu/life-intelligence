"""Answer generator — personal QA using Claude, cross-domain aware, safety-first.

Features:
- Anthropic prompt caching on system prompt (saves ~80% on repeated calls)
- In-memory TTL semantic cache keyed by question+domains hash
- Streaming support via generate_stream()
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Generator

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

# ── In-memory TTL cache ───────────────────────────────────────────────────────

_CACHE: dict[str, dict] = {}
_CACHE_TTL_SECONDS = int(os.getenv("ANSWER_CACHE_TTL", "300"))  # 5 minutes default


def _cache_key(question: str, domains: list[str]) -> str:
    raw = f"{question.strip().lower()}|{','.join(sorted(domains))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_get(key: str) -> dict | None:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SECONDS:
        return entry["value"]
    if entry:
        del _CACHE[key]
    return None


def _cache_set(key: str, value: dict) -> None:
    # Evict oldest entries if cache grows too large
    if len(_CACHE) > 200:
        oldest = min(_CACHE, key=lambda k: _CACHE[k]["ts"])
        del _CACHE[oldest]
    _CACHE[key] = {"ts": time.time(), "value": value}


# ─────────────────────────────────────────────────────────────────────────────


class AnswerGenerator:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return self._client

    def _build_messages(
        self,
        question: str,
        context: str,
        warnings: dict | None,
        cross_domain_insights: list[dict] | None,
        conversation_history: list[dict] | None,
    ) -> list[dict]:
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

        current_message = f"""Question: {question}

Personal data context (freshly retrieved):
{context[:6000]}
{warning_text}
{insights_text}

Please answer based on the provided personal data context."""

        messages: list[dict] = []
        for turn in (conversation_history or []):
            role = turn.get("role")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": current_message})
        return messages

    def generate(
        self,
        question: str,
        context: str,
        domains: list[str] | None = None,
        cross_domain_insights: list[dict] | None = None,
        warnings: dict | None = None,
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        if not context.strip():
            return {
                "answer": "I don't have enough data in your knowledge base to answer this question. Please ingest relevant documents first.",
                "key_facts": [],
                "cross_domain_insights": [],
                "warnings": [],
                "sources": [],
                "confidence": "low",
                "cached": False,
            }

        # Semantic cache check (skip when conversation history is active — context is dynamic)
        cache_key = _cache_key(question, domains or ["all"])
        if not conversation_history:
            cached = _cache_get(cache_key)
            if cached:
                logger.debug("Cache hit for question: %.60s", question)
                return {**cached, "cached": True}

        messages = self._build_messages(
            question, context, warnings, cross_domain_insights, conversation_history
        )

        try:
            client = self._get_client()
            # Use prompt caching on the system block — saves tokens on repeated calls
            response = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            )
            answer_text = response.content[0].text

            result = {
                "answer": answer_text,
                "key_facts": self._extract_bullet_points(answer_text),
                "cross_domain_insights": cross_domain_insights or [],
                "warnings": warnings.get("warnings", []) if warnings else [],
                "sources": self._extract_sources(context),
                "confidence": "high" if len(context) > 500 else "medium",
                "cached": False,
            }

            # Store in cache (only for single-turn queries)
            if not conversation_history:
                _cache_set(cache_key, result)

            return result

        except Exception as e:
            logger.error("Answer generation failed: %s", e)
            return {
                "answer": f"Error generating answer: {str(e)}",
                "key_facts": [],
                "cross_domain_insights": cross_domain_insights or [],
                "warnings": warnings.get("warnings", []) if warnings else [],
                "sources": [],
                "confidence": "low",
                "cached": False,
            }

    def generate_stream(
        self,
        question: str,
        context: str,
        domains: list[str] | None = None,
        cross_domain_insights: list[dict] | None = None,
        warnings: dict | None = None,
        conversation_history: list[dict] | None = None,
    ) -> Generator[str, None, None]:
        """Stream answer tokens as SSE data lines."""
        if not context.strip():
            yield "data: I don't have enough data in your knowledge base to answer this question.\n\n"
            yield "data: [DONE]\n\n"
            return

        messages = self._build_messages(
            question, context, warnings, cross_domain_insights, conversation_history
        )

        try:
            client = self._get_client()
            with client.messages.stream(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            ) as stream:
                for text in stream.text_stream:
                    # Escape newlines so each SSE data line is complete
                    escaped = text.replace("\n", "\\n")
                    yield f"data: {escaped}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("Streaming generation failed: %s", e)
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

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
