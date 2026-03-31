"""Medical graph builder — creates Neo4j nodes and relationships from extracted entities."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class MedicalGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        doc_id = self._make_doc_id(file_path, metadata)
        doc_date = metadata.get("date") or self._infer_date(entities)

        # Create Document node
        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title,
                d.domain = 'healthcare',
                d.vertical = 'medical',
                d.doc_type = $doc_type,
                d.source_file = $source_file,
                d.date = $date
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {
                "id": doc_id,
                "title": metadata.get("title", file_path.split("/")[-1]),
                "doc_type": metadata.get("doc_type", "medical_record"),
                "source_file": file_path,
                "date": doc_date or "",
            },
        )
        if doc_date:
            self.neo4j.link_document_to_timepoint(doc_id, doc_date)

        self._build_conditions(entities.get("conditions", []))
        self._build_medications(entities.get("medications", []))
        self._build_symptoms(entities.get("symptoms", []))
        self._build_lab_results(entities.get("lab_results", []))
        self._build_vitals(entities.get("vitals", []))
        self._build_allergies(entities.get("allergies", []))
        self._build_procedures(entities.get("procedures", []))
        self._build_vaccines(entities.get("vaccines", []))
        self._build_hospitalizations(entities.get("hospitalizations", []))
        self._build_providers(entities.get("providers", []))
        self._link_conditions_to_medications(entities)

        return doc_id

    def _build_conditions(self, conditions: list[dict]) -> None:
        for c in conditions:
            if not c.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (c:Condition {name: $name})
                SET c.icd_code = $icd_code,
                    c.status = $status,
                    c.diagnosed_date = $diagnosed_date,
                    c.severity = $severity
                WITH c
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_CONDITION]->(c)
                """,
                {
                    "name": c["name"],
                    "icd_code": c.get("icd_code", ""),
                    "status": c.get("status", "active"),
                    "diagnosed_date": c.get("diagnosed_date", ""),
                    "severity": c.get("severity", ""),
                },
            )

    def _build_medications(self, medications: list[dict]) -> None:
        for m in medications:
            if not m.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (m:Medication {name: $name})
                SET m.dosage = $dosage,
                    m.frequency = $frequency,
                    m.prescribed_date = $prescribed_date,
                    m.prescriber = $prescriber,
                    m.indication = $indication
                WITH m
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:TAKES_MEDICATION]->(m)
                """,
                {
                    "name": m["name"],
                    "dosage": m.get("dosage", ""),
                    "frequency": m.get("frequency", ""),
                    "prescribed_date": m.get("prescribed_date", ""),
                    "prescriber": m.get("prescriber", ""),
                    "indication": m.get("indication", ""),
                },
            )

    def _build_symptoms(self, symptoms: list[dict]) -> None:
        for s in symptoms:
            if not s.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (s:Symptom {name: $name})
                SET s.severity = $severity,
                    s.onset_date = $onset_date,
                    s.resolved_date = $resolved_date
                WITH s
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:EXPERIENCES]->(s)
                """,
                {
                    "name": s["name"],
                    "severity": s.get("severity", ""),
                    "onset_date": s.get("onset_date", ""),
                    "resolved_date": s.get("resolved_date", ""),
                },
            )

    def _build_lab_results(self, lab_results: list[dict]) -> None:
        for lr in lab_results:
            if not lr.get("test_name"):
                continue
            lab_id = f"lab_{hashlib.md5(f'{lr[\"test_name\"]}_{lr.get(\"date\",\"\")}_{lr.get(\"value\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (l:LabResult {id: $id})
                SET l.test_name = $test_name,
                    l.value = $value,
                    l.unit = $unit,
                    l.reference_range = $reference_range,
                    l.date = $date,
                    l.is_abnormal = $is_abnormal
                WITH l
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_LAB_RESULT]->(l)
                """,
                {
                    "id": lab_id,
                    "test_name": lr["test_name"],
                    "value": str(lr.get("value", "")),
                    "unit": lr.get("unit", ""),
                    "reference_range": lr.get("reference_range", ""),
                    "date": lr.get("date", ""),
                    "is_abnormal": bool(lr.get("is_abnormal", False)),
                },
            )

    def _build_vitals(self, vitals: list[dict]) -> None:
        for v in vitals:
            if not v.get("type"):
                continue
            vital_id = f"vital_{hashlib.md5(f'{v[\"type\"]}_{v.get(\"date\",\"\")}_{v.get(\"value\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (v:Vital {id: $id})
                SET v.type = $type, v.value = $value, v.unit = $unit, v.date = $date
                WITH v
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_VITAL]->(v)
                """,
                {
                    "id": vital_id,
                    "type": v["type"],
                    "value": str(v.get("value", "")),
                    "unit": v.get("unit", ""),
                    "date": v.get("date", ""),
                },
            )

    def _build_allergies(self, allergies: list[dict]) -> None:
        for a in allergies:
            if not a.get("allergen"):
                continue
            self.neo4j.run_query(
                """
                MERGE (a:Allergy {allergen: $allergen})
                SET a.reaction = $reaction,
                    a.severity = $severity,
                    a.discovered_date = $discovered_date
                WITH a
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_ALLERGY]->(a)
                """,
                {
                    "allergen": a["allergen"],
                    "reaction": a.get("reaction", ""),
                    "severity": a.get("severity", ""),
                    "discovered_date": a.get("discovered_date", ""),
                },
            )

    def _build_procedures(self, procedures: list[dict]) -> None:
        for pr in procedures:
            if not pr.get("name"):
                continue
            proc_id = f"proc_{hashlib.md5(f'{pr[\"name\"]}_{pr.get(\"date\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (pr:Procedure {id: $id})
                SET pr.name = $name,
                    pr.date = $date,
                    pr.provider = $provider,
                    pr.location = $location,
                    pr.notes = $notes
                WITH pr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAD_PROCEDURE]->(pr)
                """,
                {
                    "id": proc_id,
                    "name": pr["name"],
                    "date": pr.get("date", ""),
                    "provider": pr.get("provider", ""),
                    "location": pr.get("location", ""),
                    "notes": pr.get("notes", ""),
                },
            )

    def _build_vaccines(self, vaccines: list[dict]) -> None:
        for v in vaccines:
            if not v.get("name"):
                continue
            vac_id = f"vac_{hashlib.md5(f'{v[\"name\"]}_{v.get(\"date\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (v:Vaccine {id: $id})
                SET v.name = $name,
                    v.date = $date,
                    v.lot_number = $lot_number,
                    v.provider = $provider
                WITH v
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:RECEIVED_VACCINE]->(v)
                """,
                {
                    "id": vac_id,
                    "name": v["name"],
                    "date": v.get("date", ""),
                    "lot_number": v.get("lot_number", ""),
                    "provider": v.get("provider", ""),
                },
            )

    def _build_hospitalizations(self, hospitalizations: list[dict]) -> None:
        for h in hospitalizations:
            if not h.get("reason"):
                continue
            hosp_id = f"hosp_{hashlib.md5(f'{h[\"reason\"]}_{h.get(\"admit_date\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (h:Hospitalization {id: $id})
                SET h.reason = $reason,
                    h.admit_date = $admit_date,
                    h.discharge_date = $discharge_date,
                    h.facility = $facility,
                    h.discharge_summary = $discharge_summary
                WITH h
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAD_HOSPITALIZATION]->(h)
                """,
                {
                    "id": hosp_id,
                    "reason": h["reason"],
                    "admit_date": h.get("admit_date", ""),
                    "discharge_date": h.get("discharge_date", ""),
                    "facility": h.get("facility", ""),
                    "discharge_summary": h.get("discharge_summary", ""),
                },
            )

    def _build_providers(self, providers: list[dict]) -> None:
        for pr in providers:
            if not pr.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (pr:Provider {name: $name})
                SET pr.specialty = $specialty,
                    pr.institution = $institution,
                    pr.contact = $contact,
                    pr.type = 'physician'
                WITH pr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:SAW_PROVIDER]->(pr)
                """,
                {
                    "name": pr["name"],
                    "specialty": pr.get("specialty", ""),
                    "institution": pr.get("institution", ""),
                    "contact": pr.get("contact", ""),
                },
            )

    def _link_conditions_to_medications(self, entities: dict) -> None:
        """Link conditions to medications when medication indication matches condition name."""
        conditions = entities.get("conditions", [])
        medications = entities.get("medications", [])
        for cond in conditions:
            for med in medications:
                if cond.get("name") and med.get("indication"):
                    if cond["name"].lower() in med["indication"].lower():
                        self.neo4j.run_query(
                            """
                            MATCH (c:Condition {name: $cname})
                            MATCH (m:Medication {name: $mname})
                            MERGE (c)-[:TREATED_BY]->(m)
                            """,
                            {"cname": cond["name"], "mname": med["name"]},
                        )

    def _make_doc_id(self, file_path: str, metadata: dict) -> str:
        key = f"{file_path}_{metadata.get('date', '')}_{metadata.get('title', '')}"
        return f"med_{hashlib.md5(key.encode()).hexdigest()[:16]}"

    def _infer_date(self, entities: dict) -> str | None:
        for lr in entities.get("lab_results", []):
            if lr.get("date"):
                return lr["date"]
        for pr in entities.get("procedures", []):
            if pr.get("date"):
                return pr["date"]
        return None
