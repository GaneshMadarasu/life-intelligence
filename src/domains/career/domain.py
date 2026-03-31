"""Career domain — stub. See PLANNED.md for the implementation roadmap."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain


class CareerDomain(BaseDomain):
    domain_name = "career"
    domain_description = "Employment history, skills, education, and performance."

    def _init_verticals(self) -> list:
        return []

    def get_all_node_types(self) -> list[str]:
        return ["Job", "PerformanceReview", "Skill", "Certification", "Education"]

    def get_all_relationship_types(self) -> list[str]:
        return ["HAS_JOB", "HAS_REVIEW", "HAS_SKILL", "HAS_CERTIFICATION", "HAS_EDUCATION"]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Work stress correlates with health outcomes",
                "link_types": ["(Stressor {category:work})-[:CORRELATES_WITH]->(PerformanceReview)"],
            },
            "finances": {
                "description": "Jobs generate income transactions",
                "link_types": ["(Job)-[:GENERATES]->(Transaction {type:income})"],
            },
        }

    def ingest(self, file_path: str, vertical: str) -> dict:
        raise NotImplementedError(
            "The career domain is planned but not yet implemented. "
            "See src/domains/career/PLANNED.md for the roadmap."
        )

    def get_cypher_templates(self) -> dict[str, str]:
        return {}

    def get_status(self) -> dict:
        return {
            "domain": self.domain_name,
            "description": self.domain_description,
            "status": "planned",
            "verticals": ["employment-history", "skills", "education"],
            "stats": {"document_count": 0},
        }
