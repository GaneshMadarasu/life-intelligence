"""Genetics vertical — vertical class and convenience ingestion functions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.healthcare.verticals.genetics.extractor import GeneticsExtractor
from src.domains.healthcare.verticals.genetics.graph_builder import GeneticsGraphBuilder
from src.domains.healthcare.verticals.genetics.queries import QUERIES

logger = logging.getLogger(__name__)


class GeneticsVertical(BaseVertical):
    vertical_name = "genetics"
    vertical_description = "Genetic variants, disease risks, pharmacogenomics, and ancestry data."
    domain_name = "healthcare"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = GeneticsExtractor()
        self._graph_builder = GeneticsGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


def ingest_genetics_file(file_path: str, neo4j_client, vector_store) -> dict[str, Any]:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    vertical = GeneticsVertical(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return vertical.ingest(file_path)
