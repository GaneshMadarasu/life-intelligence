"""Legal contracts domain — stub. See PLANNED.md for the implementation roadmap."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain


class LegalContractsDomain(BaseDomain):
    domain_name = "legal-contracts"
    domain_description = "Employment contracts, property agreements, and insurance policies."

    def _init_verticals(self) -> list:
        return []

    def get_all_node_types(self) -> list[str]:
        return ["Contract", "Clause", "Obligation", "Benefit", "Deadline"]

    def get_all_relationship_types(self) -> list[str]:
        return ["HAS_CONTRACT", "HAS_CLAUSE", "HAS_OBLIGATION", "INCLUDES_BENEFIT", "HAS_DEADLINE"]

    def get_cross_domain_hints(self) -> dict:
        return {
            "healthcare": {
                "description": "Employment contracts include health insurance benefits",
                "link_types": [
                    "(Contract {type:employment})-[:INCLUDES_BENEFIT]->(InsurancePlan)",
                    "(Clause)-[:RELATES_TO]->(Condition)",
                ],
            },
            "finances": {
                "description": "Contracts specify compensation triggering transactions",
                "link_types": [
                    "(Contract)-[:SPECIFIES_COMPENSATION]->(Transaction)",
                    "(Obligation)-[:TRIGGERS]->(Expense)",
                ],
            },
        }

    def ingest(self, file_path: str, vertical: str) -> dict:
        raise NotImplementedError(
            "The legal-contracts domain is planned but not yet implemented. "
            "See src/domains/legal-contracts/PLANNED.md for the roadmap."
        )

    def get_cypher_templates(self) -> dict[str, str]:
        return {}

    def get_status(self) -> dict:
        return {
            "domain": self.domain_name,
            "description": self.domain_description,
            "status": "planned",
            "verticals": ["employment", "property", "insurance-policies"],
            "stats": {"document_count": 0},
        }
