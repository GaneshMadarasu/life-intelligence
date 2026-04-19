"""Finances domain verticals — banking, investments, insurance, taxes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domains.healthcare.verticals.base_vertical import BaseVertical
from src.domains.finances.extractor import FinanceExtractor
from src.domains.finances.graph_builder import FinanceGraphBuilder
from src.domains.finances.queries import QUERIES

logger = logging.getLogger(__name__)


class _FinanceVerticalBase(BaseVertical):
    domain_name = "finances"

    def __init__(self, neo4j_client, vector_store, document_loader, chunker) -> None:
        super().__init__(neo4j_client, vector_store, document_loader, chunker)
        self._extractor = FinanceExtractor()
        self._graph_builder = FinanceGraphBuilder(neo4j_client)

    def extract(self, text: str, metadata: dict) -> dict[str, Any]:
        return self._extractor.extract(text, metadata)

    def build_graph(self, entities: dict, file_path: str, metadata: dict) -> str:
        metadata["vertical"] = self.vertical_name
        return self._graph_builder.build(entities, file_path, metadata)

    def get_queries(self) -> dict[str, str]:
        return QUERIES


class BankingVertical(_FinanceVerticalBase):
    vertical_name = "banking"
    vertical_description = "Bank statements, checking/savings accounts, and transactions."


class InvestmentsVertical(_FinanceVerticalBase):
    vertical_name = "investments"
    vertical_description = "Brokerage accounts, stocks, ETFs, bonds, and portfolio snapshots."


class InsuranceVertical(_FinanceVerticalBase):
    vertical_name = "insurance"
    vertical_description = "Insurance policies — health, life, auto, home, disability."


class TaxesVertical(_FinanceVerticalBase):
    vertical_name = "taxes"
    vertical_description = "Tax returns, W-2s, 1099s, deductions, and credits."


def ingest_finance_file(file_path: str, neo4j_client, vector_store, vertical: str = "banking") -> dict:
    from src.core.document_loader import DocumentLoader
    from src.core.chunker import SmartChunker
    verticals = {
        "banking": BankingVertical,
        "investments": InvestmentsVertical,
        "insurance": InsuranceVertical,
        "taxes": TaxesVertical,
    }
    cls = verticals.get(vertical, BankingVertical)
    v = cls(neo4j_client, vector_store, DocumentLoader(), SmartChunker())
    return v.ingest(file_path)
