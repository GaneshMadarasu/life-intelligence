"""Fitness vertical — vertical class and convenience ingestion functions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.healthcare.verticals.fitness.extractor import FitnessExtractor
from src.domains.healthcare.verticals.fitness.graph_builder import FitnessGraphBuilder
from src.domains.healthcare.verticals.fitness.queries import QUERIES

logger = logging.getLogger(__name__)


class FitnessVertical(BaseVertical):
    vertical_name = "fitness"
    vertical_description = "Workouts, nutrition, body metrics, supplements, sleep, and fitness goals."
    domain_name = "healthcare"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = FitnessExtractor()
        self._graph_builder = FitnessGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


def ingest_fitness_file(file_path: str, neo4j_client, vector_store) -> dict[str, Any]:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = FitnessVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return vertical.ingest(file_path)


def ingest_fitness_folder(folder_path: str, neo4j_client, vector_store) -> list[dict[str, Any]]:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = FitnessVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    results = []
    for path in Path(folder_path).rglob("*"):
        if path.is_file() and not path.name.startswith("."):
            try:
                results.append(vertical.ingest(str(path)))
            except Exception as e:
                logger.error("Failed to ingest %s: %s", path, e)
    return results
