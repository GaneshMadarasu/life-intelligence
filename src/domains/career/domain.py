"""Career domain — employment history, skills, and education."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain
from src.core.document_loader import DocumentLoader
from src.core.chunker import SmartChunker


class CareerDomain(BaseDomain):
    domain_name = "career"
    domain_description = (
        "Career records — employment history, skills, education, certifications, and projects."
    )

    def _init_verticals(self) -> list:
        from src.domains.career.loaders import (
            EmploymentHistoryVertical, SkillsVertical, EducationVertical
        )
        loader = DocumentLoader()
        chunker = SmartChunker()
        args = (self.neo4j, self.vector_store, loader, chunker)
        return [
            EmploymentHistoryVertical(*args),
            SkillsVertical(*args),
            EducationVertical(*args),
        ]

    def get_all_node_types(self) -> list[str]:
        return ["Job", "Skill", "Education", "Certification", "Achievement", "Project"]

    def get_all_relationship_types(self) -> list[str]:
        return [
            "HAS_JOB", "HAS_SKILL", "HAS_EDUCATION",
            "HAS_CERTIFICATION", "HAS_ACHIEVEMENT", "HAS_PROJECT",
        ]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Work stress correlates with health outcomes",
                "link_types": ["(Stressor {category:work})-[:CORRELATES_WITH]->(Job)"],
            },
            "finances": {
                "description": "Jobs generate income; education costs appear as expenses",
                "link_types": ["(Job)-[:GENERATES]->(Transaction {type:credit})"],
            },
        }

    def get_cypher_templates(self) -> dict[str, str]:
        from src.domains.career.queries import QUERIES
        return QUERIES
