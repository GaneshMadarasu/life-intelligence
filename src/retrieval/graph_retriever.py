"""Graph retriever — Cypher-based retrieval across all domains."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GraphRetriever:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def retrieve(
        self,
        query: str,
        domains: list[str] | None = None,
        verticals: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve graph context relevant to a natural-language query."""
        results: list[dict] = []
        results.extend(self._search_documents(query, domains, verticals, date_from, date_to, top_k))
        results.extend(self._search_entities(query, top_k))
        # Deduplicate by id
        seen: set[str] = set()
        unique = []
        for r in results:
            key = str(r.get("id") or r.get("text", ""))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:top_k]

    def _search_documents(
        self,
        query: str,
        domains: list[str] | None,
        verticals: list[str] | None,
        date_from: str | None,
        date_to: str | None,
        top_k: int,
    ) -> list[dict]:
        domain_filter = ""
        vertical_filter = ""
        params: dict = {
            "query": query.lower(),
            "date_from": date_from,
            "date_to": date_to,
            "limit": top_k,
        }
        if domains and "all" not in domains:
            domain_filter = "AND d.domain IN $domains"
            params["domains"] = domains
        if verticals and "all" not in verticals:
            vertical_filter = "AND d.vertical IN $verticals"
            params["verticals"] = verticals

        return self.neo4j.run_query(
            f"""
            MATCH (p:Person {{id: 'primary'}})-[:HAS_DOCUMENT]->(d:Document)
            WHERE ($date_from IS NULL OR d.date >= $date_from)
            AND ($date_to IS NULL OR d.date <= $date_to)
            {domain_filter}
            {vertical_filter}
            RETURN d.id AS id, d.title AS title, d.domain AS domain,
                   d.vertical AS vertical, d.date AS date,
                   'document' AS result_type
            ORDER BY d.date DESC
            LIMIT $limit
            """,
            params,
        )

    def _search_entities(self, query: str, top_k: int) -> list[dict]:
        """Search for named entities that match the query terms."""
        terms = [t.strip() for t in query.split() if len(t.strip()) > 3]
        results = []
        for term in terms[:5]:  # limit search terms
            for label in ["Condition", "Medication", "Supplement", "GeneticRisk", "Stressor"]:
                rows = self.neo4j.run_query(
                    f"""
                    MATCH (n:{label})
                    WHERE toLower(n.name) CONTAINS toLower($term)
                    OR toLower(coalesce(n.condition_name, '')) CONTAINS toLower($term)
                    OR toLower(coalesce(n.description, '')) CONTAINS toLower($term)
                    RETURN n.name AS name,
                           coalesce(n.condition_name, n.name, n.description) AS text,
                           '{label}' AS entity_type,
                           'entity' AS result_type
                    LIMIT 3
                    """,
                    {"term": term},
                )
                results.extend(rows)
        return results[:top_k]

    def retrieve_by_entity_type(self, entity_type: str, filters: dict | None = None) -> list[dict]:
        filter_str = ""
        params: dict = filters or {}
        if filters:
            clauses = [f"n.{k} = ${k}" for k in filters]
            filter_str = "WHERE " + " AND ".join(clauses)
        return self.neo4j.run_query(
            f"MATCH (n:{entity_type}) {filter_str} RETURN n LIMIT 50",
            params,
        )

    def get_entity_neighborhood(self, entity_id: str, depth: int = 2) -> list[dict]:
        return self.neo4j.run_query(
            """
            MATCH path = (n {id: $id})-[*1..$depth]-(m)
            RETURN [node in nodes(path) | {labels: labels(node), props: properties(node)}] AS nodes,
                   [rel in relationships(path) | type(rel)] AS relationships
            LIMIT 20
            """,
            {"id": entity_id, "depth": depth},
        )
