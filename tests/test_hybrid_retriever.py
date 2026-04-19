"""Tests for the hybrid retriever — mocked Neo4j and vector store."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.retrieval.hybrid_retriever import HybridRetriever


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_neo4j(graph_results: list | None = None):
    neo4j = MagicMock()
    neo4j.run_query.return_value = graph_results or []
    return neo4j


def _make_vector(vector_results: list | None = None):
    vector = MagicMock()
    vector.search.return_value = vector_results or []
    return vector


# ── Graph retriever mock helper ───────────────────────────────────────────────

def _patch_retrievers(graph_results, vector_results):
    """Return a HybridRetriever with mocked graph and vector sub-retrievers."""

    def make_hybrid(g, v):
        h = HybridRetriever(g, v)
        h.graph = MagicMock()
        h.graph.retrieve.return_value = graph_results
        h.vector = MagicMock()
        h.vector.retrieve.return_value = vector_results
        return h

    neo4j = _make_neo4j()
    vector = _make_vector()
    return make_hybrid(neo4j, vector)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHybridRetriever:

    def test_empty_results_returns_empty_context(self):
        h = _patch_retrievers([], [])
        result = h.retrieve("What are my medications?", domains=["healthcare"])
        assert result["total_context"] == ""
        assert result["graph_results"] == []
        assert result["vector_results"] == []

    def test_graph_only_results_included(self):
        graph_results = [
            {"id": "med1", "text": "Metformin 500mg twice daily", "result_type": "medication", "date": "2024-01-01"},
        ]
        h = _patch_retrievers(graph_results, [])
        result = h.retrieve("What are my medications?")
        assert "Metformin" in result["total_context"]

    def test_vector_only_results_included(self):
        vector_results = [
            {"doc_id": "doc1", "text": "Lab result: HbA1c 7.2%", "distance": 0.1},
        ]
        h = _patch_retrievers([], vector_results)
        result = h.retrieve("What is my HbA1c?")
        assert "HbA1c" in result["total_context"]

    def test_whoop_results_always_included_first(self):
        graph_results = [
            {"id": "w1", "text": "Recovery: 78%", "result_type": "whoop_recovery", "date": "2024-06-01"},
            {"id": "med1", "text": "Metformin 500mg", "result_type": "medication", "date": "2023-01-01"},
        ]
        h = _patch_retrievers(graph_results, [])
        result = h.retrieve("How is my recovery?")
        # Whoop section should appear before non-whoop
        whoop_pos = result["total_context"].find("Whoop Biometric")
        metformin_pos = result["total_context"].find("Metformin")
        assert whoop_pos != -1
        assert whoop_pos < metformin_pos

    def test_score_fusion_deduplicates_results(self):
        shared = {"id": "med1", "text": "Aspirin 81mg", "result_type": "medication"}
        graph_results = [{**shared, "date": "2024-01-01"}]
        vector_results = [{**shared, "distance": 0.2, "doc_id": "med1"}]
        h = _patch_retrievers(graph_results, vector_results)
        result = h.retrieve("aspirin")
        # Should not appear twice in merged results
        merged_ids = [r.get("id") or r.get("doc_id") for r in result["merged_results"]]
        assert merged_ids.count("med1") == 1

    def test_recency_boost_applied(self):
        from datetime import date, timedelta
        from src.retrieval.hybrid_retriever import HybridRetriever
        h = HybridRetriever(MagicMock(), MagicMock())
        today = date.today().isoformat()
        old = (date.today() - timedelta(days=365 * 4)).isoformat()
        boost_today = h._recency_boost({"date": today})
        boost_old = h._recency_boost({"date": old})
        assert boost_today > boost_old

    def test_recency_boost_zero_for_missing_date(self):
        from src.retrieval.hybrid_retriever import HybridRetriever
        h = HybridRetriever(MagicMock(), MagicMock())
        assert h._recency_boost({}) == 0.0

    def test_top_k_limits_merged_results(self):
        graph_results = [{"id": f"r{i}", "text": f"Result {i}", "result_type": "med", "date": "2024-01-01"} for i in range(20)]
        h = _patch_retrievers(graph_results, [])
        result = h.retrieve("test", top_k=3)
        assert len(result["graph_results"]) <= 3
