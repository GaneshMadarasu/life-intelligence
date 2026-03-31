"""Abstract base class for all verticals within a domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseVertical(ABC):
    vertical_name: str = ""
    vertical_description: str = ""
    domain_name: str = ""

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        self.neo4j = neo4j_client
        self.vector_store = vector_store
        self.loader = document_loader
        self.chunker = chunker

    def ingest(self, file_path: str) -> dict[str, Any]:
        """Full ingestion pipeline: load → chunk → extract → graph → embed."""
        logger.info("Ingesting %s into %s/%s", file_path, self.domain_name, self.vertical_name)
        doc = self.loader.load(file_path)
        metadata = {
            "domain": self.domain_name,
            "vertical": self.vertical_name,
            "source_file": file_path,
            **doc.get("metadata", {}),
        }
        chunks = self.chunker.chunk(doc["text"], metadata)
        entities = self.extract(doc["text"], doc.get("metadata", {}))
        doc_id = self.build_graph(entities, file_path, doc.get("metadata", {}))

        # Tag chunks with doc_id and embed
        for chunk in chunks:
            chunk["doc_id"] = doc_id
        self.vector_store.add_chunks(chunks, self.domain_name, self.vertical_name)

        logger.info(
            "Ingested %s: %d chunks, doc_id=%s", file_path, len(chunks), doc_id
        )
        return {
            "domain": self.domain_name,
            "vertical": self.vertical_name,
            "doc_id": doc_id,
            "entities": entities,
            "chunks": len(chunks),
        }

    @abstractmethod
    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        """Extract structured entities from text using Claude."""

    @abstractmethod
    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        """Build Neo4j graph from entities, return doc_id."""

    @abstractmethod
    def get_queries(self) -> dict[str, str]:
        """Return Cypher query templates for this vertical."""
