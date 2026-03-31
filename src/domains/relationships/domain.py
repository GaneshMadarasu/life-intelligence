"""Relationships domain — stub. See PLANNED.md for the implementation roadmap."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain


class RelationshipsDomain(BaseDomain):
    domain_name = "relationships"
    domain_description = "Family health history and professional network connections."

    def _init_verticals(self) -> list:
        return []

    def get_all_node_types(self) -> list[str]:
        return ["FamilyMember", "FamilyHealthHistory", "Contact"]

    def get_all_relationship_types(self) -> list[str]:
        return ["HAS_FAMILY_MEMBER", "HAS_HEALTH_HISTORY", "HAS_CONTACT"]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Family health history informs genetic risk assessment",
                "link_types": [
                    "(FamilyMember)-[:HAS_CONDITION]->(Condition)",
                    "(FamilyHealthHistory)-[:INCREASES_RISK]->(GeneticRisk)",
                ],
            },
        }

    def ingest(self, file_path: str, vertical: str) -> dict:
        raise NotImplementedError(
            "The relationships domain is planned but not yet implemented. "
            "See src/domains/relationships/PLANNED.md for the roadmap."
        )

    def get_cypher_templates(self) -> dict[str, str]:
        return {}

    def get_status(self) -> dict:
        return {
            "domain": self.domain_name,
            "description": self.domain_description,
            "status": "planned",
            "verticals": ["family", "professional"],
            "stats": {"document_count": 0},
        }
