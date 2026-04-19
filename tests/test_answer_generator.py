"""Tests for the answer generator — mocked Claude API responses."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.generation.answer_generator import AnswerGenerator, _cache_get, _cache_set, _cache_key, _CACHE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_claude_response(text: str):
    """Build a minimal mock Anthropic API response object."""
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def _make_generator_with_mock(answer_text: str = "Your HbA1c is 7.2%.") -> AnswerGenerator:
    gen = AnswerGenerator()
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_claude_response(answer_text)
    gen._client = mock_client
    return gen


# ── Cache tests ───────────────────────────────────────────────────────────────

class TestAnswerCache:

    def setup_method(self):
        _CACHE.clear()

    def test_cache_set_and_get(self):
        key = _cache_key("what is my hrv", ["healthcare"])
        _cache_set(key, {"answer": "42ms", "cached": False})
        result = _cache_get(key)
        assert result is not None
        assert result["answer"] == "42ms"

    def test_cache_miss_returns_none(self):
        key = _cache_key("unknown question xyz", ["all"])
        assert _cache_get(key) is None

    def test_cache_ttl_expiry(self):
        import src.generation.answer_generator as ag_mod
        key = _cache_key("expiring question", ["healthcare"])
        # Manually inject an old entry
        _CACHE[key] = {"ts": time.time() - 9999, "value": {"answer": "stale"}}
        result = _cache_get(key)
        assert result is None
        assert key not in _CACHE

    def test_cache_key_is_deterministic(self):
        k1 = _cache_key("test question", ["healthcare", "all"])
        k2 = _cache_key("test question", ["all", "healthcare"])
        assert k1 == k2  # Sorted domains

    def test_cache_hit_sets_cached_flag(self):
        gen = _make_generator_with_mock("Cached answer")
        context = "HbA1c was 7.2% in January 2024."
        # First call — should miss cache and call Claude
        result1 = gen.generate("What is my HbA1c?", context, domains=["healthcare"])
        assert result1["cached"] is False
        # Second call — should hit cache
        result2 = gen.generate("What is my HbA1c?", context, domains=["healthcare"])
        assert result2["cached"] is True
        # Claude should only have been called once
        assert gen._client.messages.create.call_count == 1


# ── Generation tests ──────────────────────────────────────────────────────────

class TestAnswerGenerator:

    def setup_method(self):
        _CACHE.clear()

    def test_empty_context_returns_low_confidence(self):
        gen = AnswerGenerator()
        result = gen.generate("What is my HbA1c?", context="")
        assert result["confidence"] == "low"
        assert "don't have enough data" in result["answer"].lower()

    def test_successful_generation_returns_answer(self):
        gen = _make_generator_with_mock("Your HbA1c is 7.2%.")
        result = gen.generate("What is my HbA1c?", "HbA1c was 7.2% on 2024-01-15.", domains=["healthcare"])
        assert result["answer"] == "Your HbA1c is 7.2%."
        assert result["confidence"] in ("high", "medium")

    def test_cross_domain_insights_passed_through(self):
        gen = _make_generator_with_mock("Answer with insights.")
        insights = [{"from_type": "InsurancePlan", "from_name": "BCBS", "relationship": "COVERS", "to_type": "Condition", "to_name": "Diabetes"}]
        result = gen.generate("Insurance?", "context", cross_domain_insights=insights)
        assert result["cross_domain_insights"] == insights

    def test_warnings_passed_through(self):
        gen = _make_generator_with_mock("Safe answer.")
        warnings = {"warnings": [{"message": "Drug interaction", "domain": "healthcare"}], "high": []}
        result = gen.generate("Medications?", "context", warnings=warnings)
        assert len(result["warnings"]) == 1

    def test_conversation_history_skips_cache(self):
        gen = _make_generator_with_mock("Turn 2 answer")
        context = "Some health context."
        history = [{"role": "user", "content": "What is my HRV?"}, {"role": "assistant", "content": "42ms"}]
        gen.generate("And what about recovery?", context, conversation_history=history)
        gen.generate("And what about recovery?", context, conversation_history=history)
        # Both calls should hit Claude because conversation history disables cache
        assert gen._client.messages.create.call_count == 2

    def test_claude_api_error_returns_error_response(self):
        gen = AnswerGenerator()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API quota exceeded")
        gen._client = mock_client
        result = gen.generate("What is my HbA1c?", "context text here", domains=["healthcare"])
        assert result["confidence"] == "low"
        assert "Error" in result["answer"]

    def test_bullet_point_extraction(self):
        gen = AnswerGenerator()
        text = "Answer\n\n- Point one\n- Point two\n• Point three\n\nEnd."
        bullets = gen._extract_bullet_points(text)
        assert len(bullets) == 3
        assert "Point one" in bullets

    def test_source_extraction_from_context(self):
        gen = AnswerGenerator()
        context = "source_file: /data/uploads/healthcare/lab_results_2024.pdf\nHbA1c: 7.2%"
        sources = gen._extract_sources(context)
        assert any(".pdf" in s or "source_file" in s for s in sources)

    def test_streaming_yields_done_sentinel(self):
        gen = AnswerGenerator()
        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Hello", " world"])

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream
        gen._client = mock_client

        chunks = list(gen.generate_stream("question", "context"))
        assert any("[DONE]" in c for c in chunks)
        assert any("Hello" in c for c in chunks)

    def test_streaming_empty_context_yields_done(self):
        gen = AnswerGenerator()
        chunks = list(gen.generate_stream("question", ""))
        assert any("[DONE]" in c for c in chunks)
