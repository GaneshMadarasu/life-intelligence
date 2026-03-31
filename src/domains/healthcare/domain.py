"""Healthcare domain — registers all 4 verticals and exposes the domain interface."""

from __future__ import annotations

from src.domains.base_domain import BaseDomain
from src.core.document_loader import DocumentLoader
from src.core.chunker import SmartChunker


class HealthcareDomain(BaseDomain):
    domain_name = "healthcare"
    domain_description = (
        "Personal health records, fitness data, mental health journals, and genetic reports."
    )

    def _init_verticals(self) -> list:
        from src.domains.healthcare.verticals.medical.loaders import MedicalVertical
        from src.domains.healthcare.verticals.fitness.loaders import FitnessVertical
        from src.domains.healthcare.verticals.mental_health.loaders import MentalHealthVertical
        from src.domains.healthcare.verticals.genetics.loaders import GeneticsVertical

        loader = DocumentLoader()
        chunker = SmartChunker()
        args = (self.neo4j, self.vector_store, loader, chunker)
        return [
            MedicalVertical(*args),
            FitnessVertical(*args),
            MentalHealthVertical(*args),
            GeneticsVertical(*args),
        ]

    def get_all_node_types(self) -> list[str]:
        return [
            # Medical
            "Condition", "Medication", "Symptom", "LabResult", "Vital",
            "Allergy", "Procedure", "Vaccine", "Hospitalization",
            # Fitness
            "Workout", "Exercise", "Meal", "BodyMetric",
            "Supplement", "FitnessGoal", "SleepRecord",
            # Mental Health
            "TherapySession", "MoodEntry", "MentalCondition",
            "Stressor", "JournalEntry", "MeditationSession",
            # Genetics
            "Gene", "GeneticVariant", "GeneticRisk",
            "Pharmacogene", "AncestrySegment", "GeneticReport",
        ]

    def get_all_relationship_types(self) -> list[str]:
        return [
            "HAS_CONDITION", "TAKES_MEDICATION", "INTERACTS_WITH",
            "EXPERIENCES", "HAS_LAB_RESULT", "INDICATES", "HAS_VITAL",
            "HAS_ALLERGY", "HAD_PROCEDURE", "TREATED_BY_PROCEDURE",
            "RECEIVED_VACCINE", "HAD_HOSPITALIZATION", "TREATED_BY",
            "HAS_WORKOUT", "INCLUDES", "ATE", "HAS_BODY_METRIC",
            "TAKES_SUPPLEMENT", "HAS_FITNESS_GOAL", "HAS_SLEEP_RECORD",
            "HAD_THERAPY", "HAS_MOOD_ENTRY", "HAS_MENTAL_CONDITION",
            "HAS_STRESSOR", "HAS_JOURNAL", "HAS_MEDITATION",
            "HAS_GENE", "HAS_VARIANT", "HAS_GENETIC_RISK",
            "HAS_PHARMACOGENE", "HAS_ANCESTRY", "INVOLVES_GENE",
        ]

    def get_cross_domain_hints(self) -> dict:
        return {
            "finances": {
                "description": "Insurance coverage for conditions, HSA/FSA funding for medications",
                "link_types": [
                    "(InsurancePlan)-[:COVERS]->(Condition)",
                    "(Benefit {type:HSA})-[:FUNDS]->(Medication)",
                    "(InsurancePlan)-[:PAYS_CLAIM_FOR]->(Hospitalization)",
                ],
            },
            "legal-contracts": {
                "description": "Employment benefits covering health conditions",
                "link_types": [
                    "(Contract)-[:INCLUDES_BENEFIT]->(InsurancePlan)",
                    "(Clause)-[:RELATES_TO]->(Condition)",
                ],
            },
        }

    def get_cypher_templates(self) -> dict[str, str]:
        from src.domains.healthcare.verticals.medical.queries import QUERIES as MQ
        from src.domains.healthcare.verticals.fitness.queries import QUERIES as FQ
        from src.domains.healthcare.verticals.mental_health.queries import QUERIES as MHQ
        from src.domains.healthcare.verticals.genetics.queries import QUERIES as GQ
        return {**MQ, **FQ, **MHQ, **GQ}
