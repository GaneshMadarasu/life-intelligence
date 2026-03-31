"""Vector retriever — semantic search via ChromaDB across domains/verticals."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VectorRetriever:
    def __init__(self, vector_store) -> None:
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        domains: list[str] | None = None,
        verticals: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not domains or "all" in domains:
            return self.vector_store.search_across_domains(query, ["all"], top_k)

        results: list[dict] = []
        for domain in domains:
            if verticals and "all" not in verticals:
                for vertical in verticals:
                    hits = self.vector_store.search(query, domain, vertical, top_k)
                    for h in hits:
                        h["domain"] = domain
                        h["vertical"] = vertical
                    results.extend(hits)
            else:
                hits = self.vector_store.search_across_domains(query, [domain], top_k)
                results.extend(hits)

        results.sort(key=lambda x: x.get("distance", 1.0))
        return results[:top_k]

    def retrieve_with_filter(
        self, query: str, metadata_filter: dict, top_k: int = 5
    ) -> list[dict[str, Any]]:
        domain = metadata_filter.get("domain", "")
        vertical = metadata_filter.get("vertical", "")
        if domain and vertical:
            return self.vector_store.search(query, domain, vertical, top_k)
        return self.vector_store.search_across_domains(query, ["all"], top_k)
