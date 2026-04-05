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
        doc_date = metadata.get("date", "")
        doc_id = f"fit_{hashlib.md5(f'{file_path}_{doc_date}'.encode()).hexdigest()[:16]}"
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
            wtype, wdate = w.get("type", "general"), w["date"]
            wid = f"workout_{hashlib.md5(f'{wtype}_{wdate}'.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (w:Workout {id: $id})
                SET w.type = $type, w.date = $date,
                    w.duration_mins = $duration_mins,
                    w.calories_burned = $calories_burned,
                    w.intensity = $intensity,
                    w.strain_score = $strain_score,
                    w.avg_heart_rate = $avg_heart_rate,
                    w.max_heart_rate = $max_heart_rate,
                    w.distance_meters = $distance_meters,
                    w.altitude_gain_m = $altitude_gain_m,
                    w.hr_zone_1_mins = $hr_zone_1_mins,
                    w.hr_zone_2_mins = $hr_zone_2_mins,
                    w.hr_zone_3_mins = $hr_zone_3_mins,
                    w.hr_zone_4_mins = $hr_zone_4_mins,
                    w.hr_zone_5_mins = $hr_zone_5_mins,
                    w.source = $source,
                    w.notes = $notes
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
                    "strain_score": w.get("strain_score", 0),
                    "avg_heart_rate": w.get("avg_heart_rate", 0),
                    "max_heart_rate": w.get("max_heart_rate", 0),
                    "distance_meters": w.get("distance_meters", 0),
                    "altitude_gain_m": w.get("altitude_gain_m", 0),
                    "hr_zone_1_mins": w.get("hr_zone_1_mins", 0),
                    "hr_zone_2_mins": w.get("hr_zone_2_mins", 0),
                    "hr_zone_3_mins": w.get("hr_zone_3_mins", 0),
                    "hr_zone_4_mins": w.get("hr_zone_4_mins", 0),
                    "hr_zone_5_mins": w.get("hr_zone_5_mins", 0),
                    "source": w.get("source", "manual"),
                    "notes": w.get("notes", ""),
                },
            )

    def _build_meals(self, meals: list[dict]) -> None:
        for m in meals:
            if not m.get("name"):
                continue
            mname, mdate = m["name"], m.get("date", "")
            mid = f"meal_{hashlib.md5(f'{mname}_{mdate}'.encode()).hexdigest()[:12]}"
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
            bmtype, bmdate = bm["type"], bm["date"]
            bmid = f"bm_{hashlib.md5(f'{bmtype}_{bmdate}'.encode()).hexdigest()[:12]}"
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
                    sr.rem_hours = $rem_hours,
                    sr.light_sleep_hours = $light_sleep_hours,
                    sr.time_in_bed_hours = $time_in_bed_hours,
                    sr.sleep_performance_pct = $sleep_performance_pct,
                    sr.sleep_efficiency_pct = $sleep_efficiency_pct,
                    sr.sleep_consistency_pct = $sleep_consistency_pct,
                    sr.respiratory_rate = $respiratory_rate,
                    sr.cycle_count = $cycle_count,
                    sr.disturbances = $disturbances,
                    sr.is_nap = $is_nap,
                    sr.source = $source,
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
                    "rem_hours": sr.get("rem_hours", 0),
                    "light_sleep_hours": sr.get("light_sleep_hours", 0),
                    "time_in_bed_hours": sr.get("time_in_bed_hours", 0),
                    "sleep_performance_pct": sr.get("sleep_performance_pct", 0),
                    "sleep_efficiency_pct": sr.get("sleep_efficiency_pct", 0),
                    "sleep_consistency_pct": sr.get("sleep_consistency_pct", 0),
                    "respiratory_rate": sr.get("respiratory_rate", 0),
                    "cycle_count": sr.get("cycle_count", 0),
                    "disturbances": sr.get("disturbances", 0),
                    "is_nap": sr.get("is_nap", False),
                    "source": sr.get("source", "manual"),
                    "notes": sr.get("notes", ""),
                },
            )

    def build_whoop_recovery(self, recovery: dict) -> None:
        """Upsert a WhoopRecovery node (HRV, RHR, recovery score, SpO2)."""
        if not recovery.get("date"):
            return
        rid = f"whoop_rec_{recovery['date']}"
        self.neo4j.run_query(
            """
            MERGE (r:WhoopRecovery {id: $id})
            SET r.date = $date,
                r.recovery_score = $recovery_score,
                r.hrv_rmssd = $hrv_rmssd,
                r.resting_hr = $resting_hr,
                r.spo2_pct = $spo2_pct,
                r.skin_temp_celsius = $skin_temp_celsius,
                r.score_state = $score_state,
                r.whoop_cycle_id = $whoop_cycle_id,
                r.whoop_sleep_id = $whoop_sleep_id
            WITH r
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_RECOVERY]->(r)
            """,
            {
                "id": rid,
                "date": recovery["date"],
                "recovery_score": recovery.get("recovery_score", 0),
                "hrv_rmssd": recovery.get("hrv_rmssd", 0),
                "resting_hr": recovery.get("resting_hr", 0),
                "spo2_pct": recovery.get("spo2_pct", 0),
                "skin_temp_celsius": recovery.get("skin_temp_celsius", 0),
                "score_state": recovery.get("score_state", "SCORED"),
                "whoop_cycle_id": recovery.get("whoop_cycle_id"),
                "whoop_sleep_id": recovery.get("whoop_sleep_id"),
            },
        )

    def build_whoop_cycle(self, cycle: dict) -> None:
        """Upsert a WhoopCycle node (daily strain, calories, heart rate)."""
        if not cycle.get("date"):
            return
        cid = f"whoop_cycle_{cycle['date']}"
        self.neo4j.run_query(
            """
            MERGE (c:WhoopCycle {id: $id})
            SET c.date = $date,
                c.strain = $strain,
                c.kilojoule = $kilojoule,
                c.calories = $calories,
                c.avg_heart_rate = $avg_heart_rate,
                c.max_heart_rate = $max_heart_rate,
                c.score_state = $score_state,
                c.whoop_cycle_id = $whoop_cycle_id
            WITH c
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_WHOOP_CYCLE]->(c)
            """,
            {
                "id": cid,
                "date": cycle["date"],
                "strain": cycle.get("strain", 0),
                "kilojoule": cycle.get("kilojoule", 0),
                "calories": cycle.get("calories", 0),
                "avg_heart_rate": cycle.get("avg_heart_rate", 0),
                "max_heart_rate": cycle.get("max_heart_rate", 0),
                "score_state": cycle.get("score_state", "SCORED"),
                "whoop_cycle_id": cycle.get("whoop_cycle_id"),
            },
        )
