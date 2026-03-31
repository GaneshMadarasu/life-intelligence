"""Cross-domain linker — finds and creates edges ACROSS domains after every ingestion."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CrossDomainLinker:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def run_all_rules(self) -> dict[str, int]:
        """Run all cross-domain linking rules. Returns count of links created per rule."""
        results = {}
        results["insurance_to_conditions"] = self._link_insurance_to_conditions()
        results["employment_to_benefits"] = self._link_employment_to_benefits()
        results["medical_expenses"] = self._link_medical_expenses()
        results["stress_to_performance"] = self._link_stress_to_performance()
        total = sum(results.values())
        logger.info("Cross-domain linker: %d total links created %s", total, results)
        return results

    def _link_insurance_to_conditions(self) -> int:
        """Link InsurancePlan nodes to Condition nodes when coverage type matches."""
        result = self.neo4j.run_query(
            """
            MATCH (ip:InsurancePlan)
            MATCH (c:Condition)
            WHERE ip.coverage_type IS NOT NULL
            AND toLower(c.name) CONTAINS toLower(ip.coverage_type)
            MERGE (ip)-[r:RELEVANT_TO]->(c)
            ON CREATE SET r.auto_linked = true, r.linked_at = datetime()
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_employment_to_benefits(self) -> int:
        """Link employment Contract nodes to FSA/HSA Benefit nodes."""
        result = self.neo4j.run_query(
            """
            MATCH (c:Contract {type: 'employment'})
            MATCH (b:Benefit)
            WHERE b.type IN ['FSA', 'HSA', '401k']
            MERGE (c)-[r:INCLUDES_BENEFIT]->(b)
            ON CREATE SET r.auto_linked = true, r.linked_at = datetime()
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_medical_expenses(self) -> int:
        """Link Expense nodes (is_medical=true) to Procedure and Medication nodes by date proximity."""
        result = self.neo4j.run_query(
            """
            MATCH (e:Expense {is_medical: true})
            MATCH (proc:Procedure)
            WHERE proc.date IS NOT NULL AND e.date IS NOT NULL
            AND abs(duration.inDays(date(e.date), date(proc.date)).days) <= 30
            MERGE (e)-[r:DOCUMENTS]->(proc)
            ON CREATE SET r.auto_linked = true
            WITH count(r) as proc_links
            MATCH (ex:Expense {is_medical: true})
            MATCH (med:Medication)
            MERGE (ex)-[r2:DOCUMENTS]->(med)
            ON CREATE SET r2.auto_linked = true
            RETURN proc_links + count(r2) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_stress_to_performance(self) -> int:
        """Link Stressor nodes to PerformanceReview nodes by TimePoint proximity."""
        result = self.neo4j.run_query(
            """
            MATCH (s:Stressor)
            MATCH (pr:PerformanceReview)
            WHERE s.start_date IS NOT NULL AND pr.date IS NOT NULL
            AND abs(duration.inDays(date(s.start_date), date(pr.date)).days) <= 90
            MERGE (s)-[r:CORRELATES_WITH]->(pr)
            ON CREATE SET r.auto_linked = true, r.window_days = 90
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def get_cross_domain_insights(self) -> list[dict]:
        """Return all discovered cross-domain connections."""
        return self.neo4j.run_query(
            """
            MATCH (a)-[r]->(b)
            WHERE r.auto_linked = true
            RETURN labels(a)[0] as from_type, a.name as from_name,
                   type(r) as relationship,
                   labels(b)[0] as to_type, b.name as to_name
            LIMIT 50
            """
        )
