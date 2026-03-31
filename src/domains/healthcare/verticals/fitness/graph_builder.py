"""Fitness graph builder — creates Neo4j nodes from fitness entities."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FitnessGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        doc_id = f"fit_{hashlib.md5(f'{file_path}_{metadata.get(\"date\",\"\")}'.encode()).hexdigest()[:16]}"
        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title, d.domain = 'healthcare',
                d.vertical = 'fitness', d.source_file = $source_file
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {"id": doc_id, "title": file_path.split("/")[-1], "source_file": file_path},
        )

        self._build_workouts(entities.get("workouts", []))
        self._build_meals(entities.get("meals", []))
        self._build_body_metrics(entities.get("body_metrics", []))
        self._build_supplements(entities.get("supplements", []))
        self._build_fitness_goals(entities.get("fitness_goals", []))
        self._build_sleep_records(entities.get("sleep_records", []))
        return doc_id

    def _build_workouts(self, workouts: list[dict]) -> None:
        for w in workouts:
            if not w.get("date"):
                continue
            wid = f"workout_{hashlib.md5(f'{w[\"type\"]}_{w[\"date\"]}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (w:Workout {id: $id})
                SET w.type = $type, w.date = $date,
                    w.duration_mins = $duration_mins,
                    w.calories_burned = $calories_burned,
                    w.intensity = $intensity, w.notes = $notes
                WITH w
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_WORKOUT]->(w)
                """,
                {
                    "id": wid,
                    "type": w.get("type", "general"),
                    "date": w["date"],
                    "duration_mins": w.get("duration_mins", 0),
                    "calories_burned": w.get("calories_burned", 0),
                    "intensity": w.get("intensity", "moderate"),
                    "notes": w.get("notes", ""),
                },
            )

    def _build_meals(self, meals: list[dict]) -> None:
        for m in meals:
            if not m.get("name"):
                continue
            mid = f"meal_{hashlib.md5(f'{m[\"name\"]}_{m.get(\"date\",\"\")}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (m:Meal {id: $id})
                SET m.name = $name, m.date = $date,
                    m.calories = $calories, m.protein_g = $protein_g,
                    m.carbs_g = $carbs_g, m.fat_g = $fat_g,
                    m.meal_type = $meal_type
                WITH m
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:ATE]->(m)
                """,
                {
                    "id": mid,
                    "name": m["name"],
                    "date": m.get("date", ""),
                    "calories": m.get("calories", 0),
                    "protein_g": m.get("protein_g", 0),
                    "carbs_g": m.get("carbs_g", 0),
                    "fat_g": m.get("fat_g", 0),
                    "meal_type": m.get("meal_type", ""),
                },
            )

    def _build_body_metrics(self, metrics: list[dict]) -> None:
        for bm in metrics:
            if not bm.get("type") or not bm.get("date"):
                continue
            bmid = f"bm_{hashlib.md5(f'{bm[\"type\"]}_{bm[\"date\"]}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (bm:BodyMetric {id: $id})
                SET bm.type = $type, bm.value = $value,
                    bm.unit = $unit, bm.date = $date
                WITH bm
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_BODY_METRIC]->(bm)
                """,
                {
                    "id": bmid,
                    "type": bm["type"],
                    "value": str(bm.get("value", "")),
                    "unit": bm.get("unit", ""),
                    "date": bm["date"],
                },
            )

    def _build_supplements(self, supplements: list[dict]) -> None:
        for s in supplements:
            if not s.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (s:Supplement {name: $name})
                SET s.dosage = $dosage, s.frequency = $frequency,
                    s.brand = $brand, s.purpose = $purpose
                WITH s
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:TAKES_SUPPLEMENT]->(s)
                """,
                {
                    "name": s["name"],
                    "dosage": s.get("dosage", ""),
                    "frequency": s.get("frequency", ""),
                    "brand": s.get("brand", ""),
                    "purpose": s.get("purpose", ""),
                },
            )

    def _build_fitness_goals(self, goals: list[dict]) -> None:
        for g in goals:
            if not g.get("description"):
                continue
            gid = f"goal_{hashlib.md5(g['description'].encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (g:FitnessGoal {id: $id})
                SET g.description = $description,
                    g.target_date = $target_date,
                    g.target_value = $target_value,
                    g.metric = $metric, g.status = $status
                WITH g
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_FITNESS_GOAL]->(g)
                """,
                {
                    "id": gid,
                    "description": g["description"],
                    "target_date": g.get("target_date", ""),
                    "target_value": str(g.get("target_value", "")),
                    "metric": g.get("metric", ""),
                    "status": g.get("status", "active"),
                },
            )

    def _build_sleep_records(self, sleep_records: list[dict]) -> None:
        for sr in sleep_records:
            if not sr.get("date"):
                continue
            srid = f"sleep_{hashlib.md5(sr['date'].encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (sr:SleepRecord {id: $id})
                SET sr.date = $date,
                    sr.duration_hours = $duration_hours,
                    sr.quality = $quality,
                    sr.deep_sleep_hours = $deep_sleep_hours,
                    sr.notes = $notes
                WITH sr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_SLEEP_RECORD]->(sr)
                """,
                {
                    "id": srid,
                    "date": sr["date"],
                    "duration_hours": sr.get("duration_hours", 0),
                    "quality": sr.get("quality", 0),
                    "deep_sleep_hours": sr.get("deep_sleep_hours", 0),
                    "notes": sr.get("notes", ""),
                },
            )
