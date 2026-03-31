"""Abstract base class for all life intelligence domains."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDomain(ABC):
    domain_name: str = ""
    domain_description: str = ""

    def __init__(self, neo4j_client, vector_store) -> None:
        self.neo4j = neo4j_client
        self.vector_store = vector_store
        self.verticals = self._init_verticals()

    @abstractmethod
    def _init_verticals(self) -> list:
        """Return list of BaseVertical instances for this domain."""

    def register(self) -> None:
        """Register this domain and all its verticals in Neo4j."""
        self.neo4j.register_domain(self.domain_name, self.domain_description)
        for vertical in self.verticals:
            self.neo4j.register_vertical(
                self.domain_name, vertical.vertical_name, vertical.vertical_description
            )

    @abstractmethod
    def get_all_node_types(self) -> list[str]:
        """Return all Neo4j node labels owned by this domain."""

    @abstractmethod
    def get_all_relationship_types(self) -> list[str]:
        """Return all relationship types owned by this domain."""

    @abstractmethod
    def get_cross_domain_hints(self) -> dict[str, Any]:
        """Return which other domains this domain can connect to and how."""

    def ingest(self, file_path: str, vertical: str) -> dict[str, Any]:
        """Route file to the correct vertical for ingestion."""
        vertical_obj = next((v for v in self.verticals if v.vertical_name == vertical), None)
        if vertical_obj is None:
            raise ValueError(
                f"Unknown vertical '{vertical}' in domain '{self.domain_name}'. "
                f"Available: {[v.vertical_name for v in self.verticals]}"
            )
        return vertical_obj.ingest(file_path)

    @abstractmethod
    def get_cypher_templates(self) -> dict[str, str]:
        """Return all named Cypher query templates for this domain."""

    def get_status(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "description": self.domain_description,
            "status": "active",
            "verticals": [v.vertical_name for v in self.verticals],
            "stats": self.neo4j.get_domain_stats(self.domain_name),
        }
