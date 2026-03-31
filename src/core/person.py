"""Single Person node manager — all domains share the same Person."""

from __future__ import annotations

import os
import logging
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_manager_instance: "PersonManager | None" = None


class PersonManager:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def ensure_person(
        self,
        name: str = "Alex Johnson",
        dob: str = "1985-03-15",
        sex: str = "Male",
        blood_type: str = "O+",
    ) -> dict:
        """Create or update the single Person node."""
        return self.neo4j.get_or_create_person(name, dob, sex, blood_type)

    def get_person(self) -> dict:
        results = self.neo4j.run_query("MATCH (p:Person {id: 'primary'}) RETURN p")
        return dict(results[0]["p"]) if results else {}

    def get_person_summary(self) -> dict:
        person = self.get_person()
        domain_stats = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_DOMAIN]->(d:Domain)
            RETURN d.name as domain, d.status as status, d.description as description
            """
        )
        doc_counts = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_DOCUMENT]->(doc:Document)
            RETURN doc.domain as domain, count(doc) as count
            """
        )
        counts_by_domain = {r["domain"]: r["count"] for r in doc_counts}
        return {
            "person": person,
            "domains": [
                {**r, "document_count": counts_by_domain.get(r["domain"], 0)}
                for r in domain_stats
            ],
        }


def get_person_manager(neo4j_client=None) -> PersonManager:
    global _manager_instance
    if _manager_instance is None:
        if neo4j_client is None:
            from src.core.neo4j_client import get_client
            neo4j_client = get_client()
        _manager_instance = PersonManager(neo4j_client)
    return _manager_instance
