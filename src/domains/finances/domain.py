"""Finances domain — banking, investments, insurance, and taxes."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain
from src.core.document_loader import DocumentLoader
from src.core.chunker import SmartChunker


class FinancesDomain(BaseDomain):
    domain_name = "finances"
    domain_description = (
        "Personal financial records — bank accounts, investments, insurance policies, and taxes."
    )

    def _init_verticals(self) -> list:
        from src.domains.finances.loaders import (
            BankingVertical, InvestmentsVertical, InsuranceVertical, TaxesVertical
        )
        loader = DocumentLoader()
        chunker = SmartChunker()
        args = (self.neo4j, self.vector_store, loader, chunker)
        return [
            BankingVertical(*args),
            InvestmentsVertical(*args),
            InsuranceVertical(*args),
            TaxesVertical(*args),
        ]

    def get_all_node_types(self) -> list[str]:
        return [
            "FinancialAccount", "Transaction", "Investment",
            "InsurancePlan", "TaxItem", "Debt",
        ]

    def get_all_relationship_types(self) -> list[str]:
        return [
            "HAS_ACCOUNT", "HAS_TRANSACTION", "HAS_INVESTMENT",
            "HAS_INSURANCE", "HAS_TAX_ITEM", "HAS_DEBT",
        ]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Health insurance coverage for conditions and medications",
                "link_types": [
                    "(InsurancePlan {type:health})-[:COVERS]->(Condition)",
                    "(InsurancePlan {type:health})-[:COVERS]->(Medication)",
                ],
            },
            "legal-contracts": {
                "description": "Employment contracts referencing benefits and insurance",
                "link_types": [
                    "(Contract)-[:INCLUDES_BENEFIT]->(InsurancePlan)",
                ],
            },
        }

    def get_cypher_templates(self) -> dict[str, str]:
        from src.domains.finances.queries import QUERIES
        return QUERIES
