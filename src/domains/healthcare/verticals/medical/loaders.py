"""Medical vertical — vertical class and convenience ingestion functions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.healthcare.verticals.medical.extractor import MedicalExtractor
from src.domains.healthcare.verticals.medical.graph_builder import MedicalGraphBuilder
from src.domains.healthcare.verticals.medical.queries import QUERIES

logger = logging.getLogger(__name__)


class MedicalVertical(BaseVertical):
    vertical_name = "medical"
    vertical_description = "Medical records, lab results, medications, conditions, procedures, and vaccines."
    domain_name = "healthcare"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = MedicalExtractor()
        self._graph_builder = MedicalGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


def ingest_medical_file(
    file_path: str, neo4j_client, vector_store
) -> dict[str, Any]:
    """Convenience function: ingest a single medical file."""
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = MedicalVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return vertical.ingest(file_path)


def ingest_medical_folder(
    folder_path: str, neo4j_client, vector_store
) -> list[dict[str, Any]]:
    """Convenience function: ingest all files in a folder."""
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = MedicalVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    results = []
    for path in Path(folder_path).rglob("*"):
        if path.is_file() and not path.name.startswith("."):
            try:
                result = vertical.ingest(str(path))
                results.append(result)
            except Exception as e:
                logger.error("Failed to ingest %s: %s", path, e)
    return results
