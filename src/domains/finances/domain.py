"""Finances domain — stub. See PLANNED.md for the implementation roadmap."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain


class FinancesDomain(BaseDomain):
    domain_name = "finances"
    domain_description = "Banking, investments, insurance, and tax records."

    def _init_verticals(self) -> list:
        return []  # No verticals implemented yet

    def get_all_node_types(self) -> list[str]:
        return [
            "BankAccount", "Transaction", "Investment",
            "InsurancePlan", "TaxReturn", "Expense", "Benefit",
        ]

    def get_all_relationship_types(self) -> list[str]:
        return ["HAS_ACCOUNT", "HAS_TRANSACTION", "HAS_INVESTMENT",
                "HAS_INSURANCE", "HAS_TAX_RETURN", "HAS_EXPENSE", "HAS_BENEFIT"]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Insurance covers conditions; HSA funds medications",
                "link_types": [
                    "(InsurancePlan)-[:COVERS]->(Condition)",
                    "(Benefit {type:HSA})-[:FUNDS]->(Medication)",
                    "(InsurancePlan)-[:PAYS_CLAIM_FOR]->(Hospitalization)",
                ],
            },
            "legal-contracts": {
                "description": "Employment contracts specify compensation and benefits",
                "link_types": [
                    "(Contract)-[:SPECIFIES_COMPENSATION]->(Transaction)",
                    "(Obligation)-[:TRIGGERS]->(Expense)",
                ],
            },
        }

    def ingest(self, file_path: str, vertical: str) -> dict:
        raise NotImplementedError(
            "The finances domain is planned but not yet implemented. "
            "See src/domains/finances/PLANNED.md for the roadmap."
        )

    def get_cypher_templates(self) -> dict[str, str]:
        return {}

    def get_status(self) -> dict:
        return {
            "domain": self.domain_name,
            "description": self.domain_description,
            "status": "planned",
            "verticals": ["banking", "investments", "insurance", "taxes"],
            "stats": {"document_count": 0},
        }
