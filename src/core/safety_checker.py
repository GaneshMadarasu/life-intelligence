"""Safety checker — flags warnings across all active domains."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class SafetyChecker:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def run_full_check(self) -> dict[str, Any]:
        warnings: list[dict] = []
        warnings.extend(self._check_drug_interactions())
        warnings.extend(self._check_supplement_drug_interactions())
        warnings.extend(self._check_insurance_gaps())
        warnings.extend(self._check_upcoming_obligations())
        warnings.extend(self._check_overdue_screenings())
        warnings.sort(key=lambda w: {"high": 0, "medium": 1, "low": 2}[w["severity"]])
        return {
            "total_warnings": len(warnings),
            "high": [w for w in warnings if w["severity"] == "high"],
            "medium": [w for w in warnings if w["severity"] == "medium"],
            "low": [w for w in warnings if w["severity"] == "low"],
            "warnings": warnings,
        }

    def _check_drug_interactions(self) -> list[dict]:
        results = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:TAKES_MEDICATION]->(m1:Medication)
            MATCH (p)-[:TAKES_MEDICATION]->(m2:Medication)
            MATCH (m1)-[r:INTERACTS_WITH]->(m2)
            WHERE m1.name < m2.name
            RETURN m1.name as drug1, m2.name as drug2,
                   coalesce(r.severity, 'high') as severity,
                   coalesce(r.description, 'Known drug interaction') as description
            """
        )
        return [
            {
                "severity": r.get("severity", "high"),
                "domain": "healthcare",
                "category": "drug_interaction",
                "message": f"Drug interaction: {r['drug1']} + {r['drug2']} — {r['description']}",
                "entities": [r["drug1"], r["drug2"]],
            }
            for r in results
        ]

    def _check_supplement_drug_interactions(self) -> list[dict]:
        results = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:TAKES_SUPPLEMENT]->(s:Supplement)
            MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
            MATCH (s)-[r:INTERACTS_WITH]->(m)
            RETURN s.name as supplement, m.name as drug,
                   coalesce(r.severity, 'medium') as severity,
                   coalesce(r.description, 'Supplement-drug interaction') as description
            """
        )
        return [
            {
                "severity": r.get("severity", "medium"),
                "domain": "healthcare",
                "category": "supplement_interaction",
                "message": f"Supplement interaction: {r['supplement']} + {r['drug']} — {r['description']}",
                "entities": [r["supplement"], r["drug"]],
            }
            for r in results
        ]

    def _check_insurance_gaps(self) -> list[dict]:
        results = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_CONDITION]->(c:Condition)
            WHERE c.status IN ['active', 'chronic']
            AND NOT EXISTS {
                MATCH (ip:InsurancePlan)-[:RELEVANT_TO]->(c)
            }
            RETURN c.name as condition
            """
        )
        return [
            {
                "severity": "medium",
                "domain": "cross-domain",
                "category": "insurance_gap",
                "message": f"No insurance coverage linked for active condition: {r['condition']}",
                "entities": [r["condition"]],
            }
            for r in results
        ]

    def _check_upcoming_obligations(self) -> list[dict]:
        thirty_days = (date.today() + timedelta(days=30)).isoformat()
        results = self.neo4j.run_query(
            """
            MATCH (o:Obligation)
            WHERE o.due_date IS NOT NULL
            AND o.status = 'pending'
            AND o.due_date <= $cutoff
            RETURN o.description as description, o.due_date as due_date,
                   o.party_responsible as party
            ORDER BY o.due_date
            """,
            {"cutoff": thirty_days},
        )
        return [
            {
                "severity": "medium",
                "domain": "legal",
                "category": "upcoming_obligation",
                "message": f"Upcoming obligation by {r['due_date']}: {r['description']}",
                "entities": [r["description"]],
            }
            for r in results
        ]

    def _check_overdue_screenings(self) -> list[dict]:
        results = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_GENETIC_RISK]->(gr:GeneticRisk)
            WHERE gr.risk_level = 'high'
            AND NOT EXISTS {
                MATCH (p)-[:HAD_PROCEDURE]->(proc:Procedure)
                WHERE proc.date >= toString(date() - duration('P1Y'))
                AND toLower(proc.name) CONTAINS toLower(gr.condition_name)
            }
            RETURN gr.condition_name as condition, gr.recommendations as recommendations
            """
        )
        return [
            {
                "severity": "high",
                "domain": "healthcare",
                "category": "overdue_screening",
                "message": f"High genetic risk for {r['condition']} with no recent screening. Recommendations: {r.get('recommendations', 'Consult doctor')}",
                "entities": [r["condition"]],
            }
            for r in results
        ]
