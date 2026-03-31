"""Mental health vertical — vertical class and convenience ingestion functions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.healthcare.verticals.mental_health.extractor import MentalHealthExtractor
from src.domains.healthcare.verticals.mental_health.graph_builder import MentalHealthGraphBuilder
from src.domains.healthcare.verticals.mental_health.queries import QUERIES

logger = logging.getLogger(__name__)


class MentalHealthVertical(BaseVertical):
    vertical_name = "mental_health"
    vertical_description = "Therapy sessions, mood tracking, mental conditions, stress, journaling, and meditation."
    domain_name = "healthcare"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = MentalHealthExtractor()
        self._graph_builder = MentalHealthGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


def ingest_mental_health_file(file_path: str, neo4j_client, vector_store) -> dict[str, Any]:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = MentalHealthVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return vertical.ingest(file_path)
