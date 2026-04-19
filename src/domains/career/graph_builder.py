"""Career graph builder — creates Neo4j nodes and relationships from extracted entities."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _md5(key: str, prefix: str) -> str:
    return prefix + hashlib.md5(key.encode()).hexdigest()[:12]


class CareerGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        doc_id = self._make_doc_id(file_path, metadata)
        doc_date = metadata.get("date", "")

        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title, d.domain = 'career', d.vertical = $vertical,
                d.doc_type = $doc_type, d.source_file = $source_file, d.date = $date
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {
                "id": doc_id,
                "title": metadata.get("title", file_path.split("/")[-1]),
                "vertical": metadata.get("vertical", "employment-history"),
                "doc_type": metadata.get("doc_type", "career_document"),
                "source_file": file_path,
                "date": doc_date,
            },
        )
        if doc_date:
            self.neo4j.link_document_to_timepoint(doc_id, doc_date)

        self._build_jobs(entities.get("jobs", []))
        self._build_skills(entities.get("skills", []))
        self._build_education(entities.get("education", []))
        self._build_certifications(entities.get("certifications", []))
        self._build_achievements(entities.get("achievements", []))
        self._build_projects(entities.get("projects", []))
        return doc_id

    def _build_jobs(self, jobs: list[dict]) -> None:
        for job in jobs:
            if not job.get("title") or not job.get("company"):
                continue
            key = job.get("title", "") + "_" + job.get("company", "") + "_" + job.get("start_date", "")
            job_id = _md5(key, "job_")
            self.neo4j.run_query(
                """
                MERGE (j:Job {id: $id})
                SET j.title = $title, j.company = $company, j.location = $location,
                    j.start_date = $start_date, j.end_date = $end_date,
                    j.description = $description, j.employment_type = $employment_type,
                    j.is_current = $is_current, j.salary = $salary, j.currency = $currency
                WITH j
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_JOB]->(j)
                """,
                {
                    "id": job_id,
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "start_date": job.get("start_date", ""),
                    "end_date": job.get("end_date", ""),
                    "description": job.get("description", ""),
                    "employment_type": job.get("employment_type", ""),
                    "is_current": bool(job.get("is_current", False)),
                    "salary": job.get("salary"),
                    "currency": job.get("currency", "USD"),
                },
            )

    def _build_skills(self, skills: list[dict]) -> None:
        for skill in skills:
            if not skill.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (s:Skill {name: $name})
                SET s.category = $category, s.proficiency = $proficiency,
                    s.years_experience = $years_experience, s.last_used_date = $last_used_date
                WITH s
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_SKILL]->(s)
                """,
                {
                    "name": skill.get("name", ""),
                    "category": skill.get("category", ""),
                    "proficiency": skill.get("proficiency", ""),
                    "years_experience": skill.get("years_experience"),
                    "last_used_date": skill.get("last_used_date", ""),
                },
            )

    def _build_education(self, education: list[dict]) -> None:
        for edu in education:
            if not edu.get("institution"):
                continue
            key = edu.get("institution", "") + "_" + edu.get("degree", "") + "_" + edu.get("field_of_study", "")
            edu_id = _md5(key, "edu_")
            self.neo4j.run_query(
                """
                MERGE (e:Education {id: $id})
                SET e.institution = $institution, e.degree = $degree,
                    e.field_of_study = $field_of_study, e.start_date = $start_date,
                    e.end_date = $end_date, e.gpa = $gpa, e.honors = $honors,
                    e.is_complete = $is_complete
                WITH e
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_EDUCATION]->(e)
                """,
                {
                    "id": edu_id,
                    "institution": edu.get("institution", ""),
                    "degree": edu.get("degree", ""),
                    "field_of_study": edu.get("field_of_study", ""),
                    "start_date": edu.get("start_date", ""),
                    "end_date": edu.get("end_date", ""),
                    "gpa": edu.get("gpa"),
                    "honors": edu.get("honors", ""),
                    "is_complete": bool(edu.get("is_complete", True)),
                },
            )

    def _build_certifications(self, certs: list[dict]) -> None:
        for cert in certs:
            if not cert.get("name"):
                continue
            key = cert.get("name", "") + "_" + cert.get("issuer", "")
            cert_id = _md5(key, "cert_")
            self.neo4j.run_query(
                """
                MERGE (c:Certification {id: $id})
                SET c.name = $name, c.issuer = $issuer, c.issued_date = $issued_date,
                    c.expiry_date = $expiry_date, c.credential_id = $credential_id
                WITH c
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_CERTIFICATION]->(c)
                """,
                {
                    "id": cert_id,
                    "name": cert.get("name", ""),
                    "issuer": cert.get("issuer", ""),
                    "issued_date": cert.get("issued_date", ""),
                    "expiry_date": cert.get("expiry_date", ""),
                    "credential_id": cert.get("credential_id", ""),
                },
            )

    def _build_achievements(self, achievements: list[dict]) -> None:
        for ach in achievements:
            if not ach.get("title"):
                continue
            key = ach.get("title", "") + "_" + ach.get("date", "")
            ach_id = _md5(key, "ach_")
            self.neo4j.run_query(
                """
                MERGE (a:Achievement {id: $id})
                SET a.title = $title, a.description = $description,
                    a.date = $date, a.context = $context
                WITH a
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_ACHIEVEMENT]->(a)
                """,
                {
                    "id": ach_id,
                    "title": ach.get("title", ""),
                    "description": ach.get("description", ""),
                    "date": ach.get("date", ""),
                    "context": ach.get("context", ""),
                },
            )

    def _build_projects(self, projects: list[dict]) -> None:
        for proj in projects:
            if not proj.get("name"):
                continue
            key = proj.get("name", "") + "_" + proj.get("start_date", "")
            proj_id = _md5(key, "proj_")
            self.neo4j.run_query(
                """
                MERGE (pr:Project {id: $id})
                SET pr.name = $name, pr.description = $description, pr.role = $role,
                    pr.start_date = $start_date, pr.end_date = $end_date,
                    pr.technologies = $technologies, pr.url = $url
                WITH pr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_PROJECT]->(pr)
                """,
                {
                    "id": proj_id,
                    "name": proj.get("name", ""),
                    "description": proj.get("description", ""),
                    "role": proj.get("role", ""),
                    "start_date": proj.get("start_date", ""),
                    "end_date": proj.get("end_date", ""),
                    "technologies": proj.get("technologies", []),
                    "url": proj.get("url", ""),
                },
            )

    def _make_doc_id(self, file_path: str, metadata: dict) -> str:
        key = file_path + "_" + metadata.get("date", "") + "_" + metadata.get("title", "")
        return _md5(key, "car_")
