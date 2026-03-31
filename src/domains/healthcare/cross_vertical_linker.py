"""Links nodes across the 4 healthcare verticals — runs after every healthcare ingestion."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

KNOWN_SUPPLEMENT_DRUG_INTERACTIONS = [
    ("Berberine", "Metformin", "high", "Both lower blood glucose — additive hypoglycemia risk"),
    ("Omega-3", "Warfarin", "medium", "May increase bleeding risk"),
    ("St. John's Wort", "Sertraline", "high", "Serotonin syndrome risk"),
    ("St. John's Wort", "Escitalopram", "high", "Serotonin syndrome risk"),
    ("Magnesium", "Metformin", "low", "Magnesium may slightly enhance metformin effect"),
    ("Vitamin E", "Warfarin", "medium", "May increase anticoagulant effect"),
    ("Ginkgo", "Aspirin", "medium", "Increased bleeding risk"),
    ("Valerian", "Sertraline", "medium", "May enhance sedative effects"),
]

KNOWN_DRUG_DRUG_INTERACTIONS = [
    ("Sertraline", "Escitalopram", "high", "Duplicate serotonergic mechanism — serotonin syndrome risk"),
    ("Metformin", "Lisinopril", "low", "Monitor renal function"),
    ("Atorvastatin", "Escitalopram", "low", "Minor CYP interaction — monitor"),
]


class HealthcareCrossVerticalLinker:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def run_all_links(self) -> dict[str, int]:
        counts = {}
        counts["supplement_drug"] = self._link_supplement_drug_interactions()
        counts["drug_drug"] = self._seed_known_drug_interactions()
        counts["workout_vital"] = self._link_workout_to_vital()
        counts["body_metric_lab"] = self._link_body_metric_to_lab()
        counts["meal_lab"] = self._link_meal_to_lab()
        counts["stressor_symptom"] = self._link_stressor_to_symptom()
        counts["mood_vital"] = self._link_mood_to_vital()
        counts["mental_medication"] = self._link_mental_condition_to_medication()
        counts["workout_mood"] = self._link_workout_to_mood()
        counts["sleep_mood"] = self._link_sleep_to_mood()
        counts["genetic_risk_condition"] = self._link_genetic_risk_to_condition()
        counts["pharmacogene_medication"] = self._link_pharmacogene_to_medication()
        counts["gene_mental"] = self._link_gene_to_mental_condition()
        total = sum(counts.values())
        logger.info("Healthcare cross-vertical: %d links %s", total, counts)
        return counts

    def _seed_known_drug_interactions(self) -> int:
        count = 0
        for drug1, drug2, severity, desc in KNOWN_DRUG_DRUG_INTERACTIONS:
            result = self.neo4j.run_query(
                """
                MATCH (m1:Medication) WHERE toLower(m1.name) CONTAINS toLower($d1)
                MATCH (m2:Medication) WHERE toLower(m2.name) CONTAINS toLower($d2)
                MERGE (m1)-[r:INTERACTS_WITH]->(m2)
                ON CREATE SET r.severity = $severity, r.description = $desc
                MERGE (m2)-[r2:INTERACTS_WITH]->(m1)
                ON CREATE SET r2.severity = $severity, r2.description = $desc
                RETURN count(r) as created
                """,
                {"d1": drug1, "d2": drug2, "severity": severity, "desc": desc},
            )
            count += result[0]["created"] if result else 0
        return count

    def _link_supplement_drug_interactions(self) -> int:
        count = 0
        for supp, drug, severity, desc in KNOWN_SUPPLEMENT_DRUG_INTERACTIONS:
            result = self.neo4j.run_query(
                """
                MATCH (s:Supplement) WHERE toLower(s.name) CONTAINS toLower($supp)
                MATCH (m:Medication) WHERE toLower(m.name) CONTAINS toLower($drug)
                MERGE (s)-[r:INTERACTS_WITH]->(m)
                ON CREATE SET r.severity = $severity, r.description = $desc
                RETURN count(r) as created
                """,
                {"supp": supp, "drug": drug, "severity": severity, "desc": desc},
            )
            count += result[0]["created"] if result else 0
        return count

    def _link_workout_to_vital(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (w:Workout)
            MATCH (v:Vital)
            WHERE w.date IS NOT NULL AND v.date IS NOT NULL
            AND abs(duration.inDays(date(w.date), date(v.date)).days) <= 1
            MERGE (w)-[r:AFFECTS]->(v)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_body_metric_to_lab(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (bm:BodyMetric {type: 'weight'})
            MATCH (lr:LabResult)
            WHERE bm.date IS NOT NULL AND lr.date IS NOT NULL
            AND abs(duration.inDays(date(bm.date), date(lr.date)).days) <= 14
            MERGE (bm)-[r:CORRELATES_WITH]->(lr)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_meal_to_lab(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (m:Meal)
            MATCH (lr:LabResult)
            WHERE m.date IS NOT NULL AND lr.date IS NOT NULL
            AND abs(duration.inDays(date(m.date), date(lr.date)).days) <= 3
            MERGE (m)-[r:AFFECTS]->(lr)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_stressor_to_symptom(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (s:Stressor)
            MATCH (sy:Symptom)
            WHERE s.start_date IS NOT NULL AND sy.onset_date IS NOT NULL
            AND abs(duration.inDays(date(s.start_date), date(sy.onset_date)).days) <= 30
            MERGE (s)-[r:TRIGGERS]->(sy)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_mood_to_vital(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (me:MoodEntry)
            MATCH (v:Vital {type: 'blood_pressure'})
            WHERE me.date IS NOT NULL AND v.date IS NOT NULL
            AND abs(duration.inDays(date(me.date), date(v.date)).days) <= 1
            MERGE (me)-[r:CORRELATES_WITH]->(v)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_mental_condition_to_medication(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (mc:MentalCondition)
            MATCH (med:Medication)
            WHERE toLower(mc.name) CONTAINS 'anxiety' AND toLower(med.name) CONTAINS 'sertraline'
            OR toLower(mc.name) CONTAINS 'depression' AND (toLower(med.name) CONTAINS 'escitalopram' OR toLower(med.name) CONTAINS 'sertraline')
            OR toLower(mc.name) CONTAINS 'adhd' AND toLower(med.name) CONTAINS 'methylphenidate'
            MERGE (mc)-[r:TREATED_BY]->(med)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_workout_to_mood(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (w:Workout)
            MATCH (me:MoodEntry)
            WHERE w.date IS NOT NULL AND me.date IS NOT NULL
            AND abs(duration.inDays(date(w.date), date(me.date)).days) <= 1
            MERGE (w)-[r:IMPROVES]->(me)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_sleep_to_mood(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (sr:SleepRecord)
            MATCH (me:MoodEntry)
            WHERE sr.date IS NOT NULL AND me.date IS NOT NULL
            AND abs(duration.inDays(date(sr.date), date(me.date)).days) <= 1
            MERGE (sr)-[r:AFFECTS]->(me)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_genetic_risk_to_condition(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (gr:GeneticRisk)
            MATCH (c:Condition)
            WHERE toLower(c.name) CONTAINS toLower(gr.condition_name)
            OR toLower(gr.condition_name) CONTAINS toLower(c.name)
            MERGE (gr)-[r:RELATES_TO_CONDITION]->(c)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_pharmacogene_to_medication(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (pg:Pharmacogene)
            UNWIND pg.affected_drugs as drug_name
            MATCH (m:Medication)
            WHERE toLower(m.name) CONTAINS toLower(drug_name)
            MERGE (pg)-[r:AFFECTS_METABOLISM_OF]->(m)
            ON CREATE SET r.auto_linked = true, r.metabolism = pg.drug_metabolism
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0

    def _link_gene_to_mental_condition(self) -> int:
        result = self.neo4j.run_query(
            """
            MATCH (g:Gene)
            MATCH (mc:MentalCondition)
            MATCH (gr:GeneticRisk)-[:INVOLVES_GENE]->(g)
            WHERE toLower(gr.condition_name) CONTAINS toLower(mc.name)
            OR toLower(mc.name) CONTAINS toLower(gr.condition_name)
            MERGE (g)-[r:INCREASES_RISK_OF]->(mc)
            ON CREATE SET r.auto_linked = true
            RETURN count(r) as created
            """
        )
        return result[0]["created"] if result else 0
