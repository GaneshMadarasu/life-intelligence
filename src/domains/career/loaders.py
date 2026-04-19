"""Career domain verticals — employment-history, skills, education."""

from __future__ import annotations

import logging
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.career.extractor import CareerExtractor
from src.domains.career.graph_builder import CareerGraphBuilder
from src.domains.career.queries import QUERIES

logger = logging.getLogger(__name__)


class _CareerVerticalBase(BaseVertical):
    domain_name = "career"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = CareerExtractor()
        self._graph_builder = CareerGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        metadata["vertical"] = self.vertical_name
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


class EmploymentHistoryVertical(_CareerVerticalBase):
    vertical_name = "employment-history"
    vertical_description = "Work history — job titles, companies, roles, and descriptions."


class SkillsVertical(_CareerVerticalBase):
    vertical_name = "skills"
    vertical_description = "Technical and soft skills with proficiency levels."


class EducationVertical(_CareerVerticalBase):
    vertical_name = "education"
    vertical_description = "Educational history — degrees, institutions, certifications."


def ingest_career_file(file_path: str, neo4j_client, vector_store, vertical: str = "employment-history") -> dict:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    verticals = {
        "employment-history": EmploymentHistoryVertical,
        "skills": SkillsVertical,
        "education": EducationVertical,
    }
    cls = verticals.get(vertical, EmploymentHistoryVertical)
    v = cls(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return v.ingest(file_path)
