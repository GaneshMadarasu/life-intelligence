"""Finance graph builder — creates Neo4j nodes and relationships from extracted entities."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _md5(key: str, prefix: str) -> str:
    return prefix + hashlib.md5(key.encode()).hexdigest()[:12]


class FinanceGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        doc_id = self._make_doc_id(file_path, metadata)
        doc_date = metadata.get("date", "")

        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title, d.domain = 'finances', d.vertical = $vertical,
                d.doc_type = $doc_type, d.source_file = $source_file, d.date = $date
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {
                "id": doc_id,
                "title": metadata.get("title", file_path.split("/")[-1]),
                "vertical": metadata.get("vertical", "banking"),
                "doc_type": metadata.get("doc_type", "financial_document"),
                "source_file": file_path,
                "date": doc_date,
            },
        )
        if doc_date:
            self.neo4j.link_document_to_timepoint(doc_id, doc_date)

        self._build_accounts(entities.get("accounts", []))
        self._build_transactions(entities.get("transactions", []))
        self._build_investments(entities.get("investments", []))
        self._build_insurance_plans(entities.get("insurance_plans", []))
        self._build_tax_items(entities.get("tax_items", []))
        self._build_debts(entities.get("debts", []))
        return doc_id

    def _build_accounts(self, accounts: list[dict]) -> None:
        for a in accounts:
            if not a.get("name") and not a.get("institution"):
                continue
            key = a.get("name", "") + "_" + a.get("institution", "")
            acc_id = _md5(key, "acc_")
            self.neo4j.run_query(
                """
                MERGE (a:FinancialAccount {id: $id})
                SET a.name = $name, a.type = $type, a.institution = $institution,
                    a.account_number_last4 = $last4, a.balance = $balance,
                    a.currency = $currency, a.opened_date = $opened_date, a.status = $status
                WITH a
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_ACCOUNT]->(a)
                """,
                {
                    "id": acc_id,
                    "name": a.get("name", ""),
                    "type": a.get("type", ""),
                    "institution": a.get("institution", ""),
                    "last4": a.get("account_number_last4", ""),
                    "balance": a.get("balance"),
                    "currency": a.get("currency", "USD"),
                    "opened_date": a.get("opened_date", ""),
                    "status": a.get("status", "active"),
                },
            )

    def _build_transactions(self, transactions: list[dict]) -> None:
        for t in transactions:
            if not t.get("description"):
                continue
            key = t.get("description", "") + "_" + t.get("date", "") + "_" + str(t.get("amount", ""))
            txn_id = _md5(key, "txn_")
            self.neo4j.run_query(
                """
                MERGE (t:Transaction {id: $id})
                SET t.description = $description, t.amount = $amount,
                    t.type = $type, t.category = $category, t.date = $date,
                    t.account = $account, t.merchant = $merchant
                WITH t
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_TRANSACTION]->(t)
                """,
                {
                    "id": txn_id,
                    "description": t.get("description", ""),
                    "amount": t.get("amount"),
                    "type": t.get("type", ""),
                    "category": t.get("category", ""),
                    "date": t.get("date", ""),
                    "account": t.get("account", ""),
                    "merchant": t.get("merchant", ""),
                },
            )

    def _build_investments(self, investments: list[dict]) -> None:
        for inv in investments:
            if not inv.get("name") and not inv.get("symbol"):
                continue
            key = inv.get("symbol", "") + "_" + inv.get("name", "")
            inv_id = _md5(key, "inv_")
            self.neo4j.run_query(
                """
                MERGE (i:Investment {id: $id})
                SET i.symbol = $symbol, i.name = $name, i.asset_type = $asset_type,
                    i.quantity = $quantity, i.price_per_unit = $price, i.total_value = $total_value,
                    i.purchase_date = $purchase_date, i.account = $account
                WITH i
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_INVESTMENT]->(i)
                """,
                {
                    "id": inv_id,
                    "symbol": inv.get("symbol", ""),
                    "name": inv.get("name", ""),
                    "asset_type": inv.get("asset_type", ""),
                    "quantity": inv.get("quantity"),
                    "price": inv.get("price_per_unit"),
                    "total_value": inv.get("total_value"),
                    "purchase_date": inv.get("purchase_date", ""),
                    "account": inv.get("account", ""),
                },
            )

    def _build_insurance_plans(self, plans: list[dict]) -> None:
        for plan in plans:
            if not plan.get("plan_name") and not plan.get("insurer"):
                continue
            key = plan.get("plan_name", "") + "_" + plan.get("insurer", "")
            plan_id = _md5(key, "ins_")
            self.neo4j.run_query(
                """
                MERGE (i:InsurancePlan {id: $id})
                SET i.plan_name = $plan_name, i.insurer = $insurer, i.type = $type,
                    i.premium_monthly = $premium, i.deductible = $deductible,
                    i.coverage_limit = $coverage_limit, i.start_date = $start_date,
                    i.end_date = $end_date, i.policy_number = $policy_number
                WITH i
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_INSURANCE]->(i)
                """,
                {
                    "id": plan_id,
                    "plan_name": plan.get("plan_name", ""),
                    "insurer": plan.get("insurer", ""),
                    "type": plan.get("type", ""),
                    "premium": plan.get("premium_monthly"),
                    "deductible": plan.get("deductible"),
                    "coverage_limit": plan.get("coverage_limit"),
                    "start_date": plan.get("start_date", ""),
                    "end_date": plan.get("end_date", ""),
                    "policy_number": plan.get("policy_number", ""),
                },
            )

    def _build_tax_items(self, tax_items: list[dict]) -> None:
        for item in tax_items:
            if not item.get("type"):
                continue
            key = item.get("type", "") + "_" + item.get("year", "") + "_" + item.get("description", "")
            tax_id = _md5(key, "tax_")
            self.neo4j.run_query(
                """
                MERGE (t:TaxItem {id: $id})
                SET t.year = $year, t.type = $type, t.amount = $amount,
                    t.description = $description, t.issuer = $issuer
                WITH t
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_TAX_ITEM]->(t)
                """,
                {
                    "id": tax_id,
                    "year": item.get("year", ""),
                    "type": item.get("type", ""),
                    "amount": item.get("amount"),
                    "description": item.get("description", ""),
                    "issuer": item.get("issuer", ""),
                },
            )

    def _build_debts(self, debts: list[dict]) -> None:
        for debt in debts:
            if not debt.get("name"):
                continue
            key = debt.get("name", "") + "_" + debt.get("type", "")
            debt_id = _md5(key, "debt_")
            self.neo4j.run_query(
                """
                MERGE (d:Debt {id: $id})
                SET d.name = $name, d.type = $type, d.balance = $balance,
                    d.interest_rate = $interest_rate, d.minimum_payment = $min_payment,
                    d.due_date = $due_date
                WITH d
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_DEBT]->(d)
                """,
                {
                    "id": debt_id,
                    "name": debt.get("name", ""),
                    "type": debt.get("type", ""),
                    "balance": debt.get("balance"),
                    "interest_rate": debt.get("interest_rate"),
                    "min_payment": debt.get("minimum_payment"),
                    "due_date": debt.get("due_date", ""),
                },
            )

    def _make_doc_id(self, file_path: str, metadata: dict) -> str:
        key = file_path + "_" + metadata.get("date", "") + "_" + metadata.get("title", "")
        return _md5(key, "fin_")
