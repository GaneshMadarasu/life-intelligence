"""Hybrid retriever — fuses graph + vector results with timeline weighting."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.retrieval.graph_retriever import GraphRetriever
from src.retrieval.vector_retriever import VectorRetriever

logger = logging.getLogger(__name__)

GRAPH_WEIGHT = 0.6
VECTOR_WEIGHT = 0.4
RECENCY_BOOST_MAX = 0.15
RECENCY_DECAY_YEARS = 5


class HybridRetriever:
    def __init__(self, neo4j_client, vector_store) -> None:
        self.graph = GraphRetriever(neo4j_client)
        self.vector = VectorRetriever(vector_store)

    def retrieve(
        self,
        question: str,
        domains: list[str] | None = None,
        verticals: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        domains = domains or ["all"]
        verticals = verticals or ["all"]

        graph_results = self.graph.retrieve(
            question, domains, verticals, date_from, date_to, top_k * 2
        )
        vector_results = self.vector.retrieve(question, domains, verticals, top_k * 2)

        merged = self._fuse(graph_results, vector_results, top_k)

        total_context = "\n\n".join(
            r.get("text") or r.get("title") or str(r.get("name", ""))
            for r in merged
            if r.get("text") or r.get("title")
        )

        return {
            "graph_results": graph_results[:top_k],
            "vector_results": vector_results[:top_k],
            "merged_results": merged,
            "total_context": total_context,
        }

    def _fuse(
        self, graph_results: list[dict], vector_results: list[dict], top_k: int
    ) -> list[dict]:
        scored: dict[str, dict] = {}

        for i, r in enumerate(graph_results):
            key = self._result_key(r)
            graph_score = GRAPH_WEIGHT * (1.0 - i / max(len(graph_results), 1))
            recency = self._recency_boost(r)
            scored[key] = {
                **r,
                "graph_score": graph_score,
                "vector_score": 0.0,
                "combined_score": graph_score + recency,
            }

        for i, r in enumerate(vector_results):
            key = self._result_key(r)
            vector_score = VECTOR_WEIGHT * (1.0 - r.get("distance", 0.5))
            if key in scored:
                scored[key]["vector_score"] = vector_score
                scored[key]["combined_score"] += vector_score
            else:
                recency = self._recency_boost(r)
                scored[key] = {
                    **r,
                    "graph_score": 0.0,
                    "vector_score": vector_score,
                    "combined_score": vector_score + recency,
                }

        merged = sorted(scored.values(), key=lambda x: x["combined_score"], reverse=True)
        return merged[:top_k]

    def _result_key(self, r: dict) -> str:
        return str(r.get("id") or r.get("doc_id") or r.get("text", "")[:50])

    def _recency_boost(self, r: dict) -> float:
        date_str = r.get("date") or r.get("chunk_date") or ""
        if not date_str:
            return 0.0
        try:
            event_date = date.fromisoformat(str(date_str)[:10])
            years_ago = (date.today() - event_date).days / 365.25
            boost = RECENCY_BOOST_MAX * max(0, 1 - years_ago / RECENCY_DECAY_YEARS)
            return boost
        except ValueError:
            return 0.0
