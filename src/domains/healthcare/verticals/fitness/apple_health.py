"""Apple Health XML export ingestion.

Parses Apple Health's export.xml and ingests:
  - Steps, heart rate, resting heart rate history
  - Blood glucose (if CGM/glucometer paired)
  - Body weight / BMI
  - Sleep analysis (time in bed / asleep)
  - Workout sessions
  - VO2Max estimates
  - SPO2 readings

Usage:
    python scripts/ingest.py --file data/uploads/healthcare/fitness/export.xml \
        --domain healthcare --vertical fitness
"""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, date
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# Apple Health record type → our category mapping
_RECORD_MAP = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierBloodGlucose": "blood_glucose",
    "HKQuantityTypeIdentifierBodyMass": "body_weight",
    "HKQuantityTypeIdentifierBodyMassIndex": "bmi",
    "HKQuantityTypeIdentifierOxygenSaturation": "spo2",
    "HKQuantityTypeIdentifierVO2Max": "vo2max",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKCategoryTypeIdentifierSleepAnalysis": "sleep",
}

_WORKOUT_TYPE = "HKWorkoutActivityType"


def parse_apple_health_export(file_path: str) -> dict[str, Any]:
    """Parse Apple Health export.xml and return structured data."""
    logger.info("Parsing Apple Health export: %s", file_path)
    try:
        tree = ET.parse(file_path)
    except ET.ParseError as e:
        logger.error("Failed to parse Apple Health XML: %s", e)
        return _empty_result()

    root = tree.getroot()
    records: dict[str, list[dict]] = defaultdict(list)
    workouts: list[dict] = []

    for elem in root:
        if elem.tag == "Record":
            rec_type = elem.get("type", "")
            category = _RECORD_MAP.get(rec_type)
            if not category:
                continue
            value = elem.get("value", "")
            start = _parse_date(elem.get("startDate", ""))
            end = _parse_date(elem.get("endDate", ""))
            unit = elem.get("unit", "")
            source = elem.get("sourceName", "Apple Health")

            if category == "sleep":
                # value is "HKCategoryValueSleepAnalysisAsleep" or "InBed"
                records["sleep"].append({
                    "start": start,
                    "end": end,
                    "state": "asleep" if "Asleep" in value else "in_bed",
                    "source": source,
                })
            else:
                try:
                    numeric = float(value)
                except (ValueError, TypeError):
                    continue
                records[category].append({
                    "date": start or end,
                    "value": numeric,
                    "unit": unit,
                    "source": source,
                })

        elif elem.tag == "Workout":
            workouts.append(_parse_workout(elem))

    return {
        "records": dict(records),
        "workouts": workouts,
        "summary": {k: len(v) for k, v in records.items()},
        "workout_count": len(workouts),
    }


def _parse_workout(elem) -> dict:
    workout_type = elem.get("workoutActivityType", "")
    # Strip "HKWorkoutActivityType" prefix for readability
    workout_type = workout_type.replace("HKWorkoutActivityType", "")
    duration = elem.get("duration", "0")
    try:
        duration_mins = round(float(duration), 1)
    except (ValueError, TypeError):
        duration_mins = 0.0

    calories = 0.0
    distance = 0.0
    for stats in elem.findall("WorkoutStatistics"):
        stat_type = stats.get("type", "")
        val = stats.get("sum") or stats.get("average") or "0"
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            val_f = 0.0
        if "ActiveEnergyBurned" in stat_type:
            calories = round(val_f, 1)
        elif "DistanceWalkingRunning" in stat_type or "Distance" in stat_type:
            distance = round(val_f, 3)

    return {
        "type": workout_type,
        "start": _parse_date(elem.get("startDate", "")),
        "end": _parse_date(elem.get("endDate", "")),
        "duration_mins": duration_mins,
        "calories": calories,
        "distance_km": distance,
        "source": elem.get("sourceName", "Apple Health"),
    }


def _parse_date(date_str: str) -> str:
    """Convert Apple Health date format to ISO date string."""
    if not date_str:
        return ""
    # Apple Health format: "2024-01-15 08:30:00 -0500"
    try:
        dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
        return dt.date().isoformat()
    except ValueError:
        return date_str[:10] if len(date_str) >= 10 else ""


def _empty_result() -> dict:
    return {"records": {}, "workouts": [], "summary": {}, "workout_count": 0}


class AppleHealthGraphBuilder:
    """Writes parsed Apple Health data into Neo4j."""

    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, parsed: dict, file_path: str) -> str:
        doc_id = f"aph_{hashlib.md5(file_path.encode()).hexdigest()[:16]}"
        today = date.today().isoformat()

        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = 'Apple Health Export', d.domain = 'healthcare',
                d.vertical = 'fitness', d.doc_type = 'apple_health_export',
                d.source_file = $source_file, d.date = $date
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {"id": doc_id, "source_file": file_path, "date": today},
        )

        records = parsed.get("records", {})
        self._build_body_metrics(records.get("body_weight", []), records.get("bmi", []))
        self._build_vitals(records.get("heart_rate", []), "heart_rate", "Heart Rate", "bpm")
        self._build_vitals(records.get("resting_hr", []), "resting_hr", "Resting HR", "bpm")
        self._build_vitals(records.get("spo2", []), "spo2", "SpO2", "%")
        self._build_vitals(records.get("vo2max", []), "vo2max", "VO2Max", "mL/kg/min")
        self._build_vitals(records.get("respiratory_rate", []), "resp_rate", "Respiratory Rate", "bpm")
        self._build_blood_glucose(records.get("blood_glucose", []))
        self._build_sleep(records.get("sleep", []))
        self._build_workouts(parsed.get("workouts", []))
        self._build_daily_steps(records.get("steps", []))

        logger.info(
            "Apple Health import complete — doc_id=%s, types=%s, workouts=%d",
            doc_id, list(records.keys()), len(parsed.get("workouts", [])),
        )
        return doc_id

    def _build_body_metrics(self, weights: list, bmis: list) -> None:
        seen_dates: set[str] = set()
        for w in weights:
            d = w.get("date", "")
            if not d or d in seen_dates:
                continue
            seen_dates.add(d)
            metric_id = hashlib.md5(("weight_" + d).encode()).hexdigest()[:12]
            metric_id = "bm_" + metric_id
            self.neo4j.run_query(
                """
                MERGE (bm:BodyMetric {id: $id})
                SET bm.date = $date, bm.weight_kg = $weight, bm.source = 'apple_health'
                WITH bm
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_BODY_METRIC]->(bm)
                """,
                {"id": metric_id, "date": d, "weight": round(w["value"], 2)},
            )

    def _build_vitals(self, readings: list, vtype: str, name: str, unit: str) -> None:
        # Aggregate to daily average to avoid flooding the graph
        daily: dict[str, list[float]] = defaultdict(list)
        for r in readings:
            if r.get("date") and r.get("value") is not None:
                daily[r["date"]].append(r["value"])
        for day, values in daily.items():
            avg = round(sum(values) / len(values), 2)
            vital_id = "vital_" + hashlib.md5((vtype + "_" + day).encode()).hexdigest()[:12]
            self.neo4j.run_query(
                """
                MERGE (v:Vital {id: $id})
                SET v.type = $type, v.value = $value, v.unit = $unit,
                    v.date = $date, v.source = 'apple_health'
                WITH v
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_VITAL]->(v)
                """,
                {"id": vital_id, "type": name, "value": str(avg), "unit": unit, "date": day},
            )

    def _build_blood_glucose(self, readings: list) -> None:
        daily: dict[str, list[float]] = defaultdict(list)
        for r in readings:
            if r.get("date") and r.get("value") is not None:
                daily[r["date"]].append(r["value"])
        for day, values in daily.items():
            avg = round(sum(values) / len(values), 2)
            lab_id = "lab_" + hashlib.md5(("glucose_" + day).encode()).hexdigest()[:12]
            self.neo4j.run_query(
                """
                MERGE (l:LabResult {id: $id})
                SET l.test_name = 'Blood Glucose', l.value = $value,
                    l.unit = 'mg/dL', l.date = $date, l.source = 'apple_health',
                    l.is_abnormal = ($value > 180 OR $value < 70)
                WITH l
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_LAB_RESULT]->(l)
                """,
                {"id": lab_id, "value": avg, "date": day},
            )

    def _build_sleep(self, sleep_records: list) -> None:
        # Group by date and sum asleep minutes
        daily: dict[str, dict] = defaultdict(lambda: {"asleep_mins": 0, "in_bed_mins": 0})
        for r in sleep_records:
            d = r.get("start", "")
            if not d:
                continue
            # Rough duration calc would need start/end datetimes; use date as key
            daily[d][r["state"] + "_mins"] = daily[d].get(r["state"] + "_mins", 0) + 30  # approximation

        for day, data in daily.items():
            sleep_id = "slp_" + hashlib.md5(("apple_" + day).encode()).hexdigest()[:12]
            duration_hrs = round(data.get("asleep_mins", 0) / 60, 2)
            if duration_hrs < 0.5:
                continue
            self.neo4j.run_query(
                """
                MERGE (sr:SleepRecord {id: $id})
                SET sr.date = $date, sr.duration_hours = $duration_hours,
                    sr.source = 'apple_health'
                WITH sr
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_SLEEP_RECORD]->(sr)
                """,
                {"id": sleep_id, "date": day, "duration_hours": duration_hrs},
            )

    def _build_workouts(self, workouts: list) -> None:
        for w in workouts:
            if not w.get("start"):
                continue
            wid = "aph_w_" + hashlib.md5((w.get("type", "") + "_" + w.get("start", "")).encode()).hexdigest()[:12]
            self.neo4j.run_query(
                """
                MERGE (wo:Workout {id: $id})
                SET wo.type = $type, wo.date = $date,
                    wo.duration_mins = $duration_mins,
                    wo.calories_burned = $calories,
                    wo.distance_km = $distance,
                    wo.source = 'apple_health'
                WITH wo
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_WORKOUT]->(wo)
                """,
                {
                    "id": wid,
                    "type": w.get("type", ""),
                    "date": w.get("start", ""),
                    "duration_mins": w.get("duration_mins", 0),
                    "calories": w.get("calories", 0),
                    "distance": w.get("distance_km", 0),
                },
            )

    def _build_daily_steps(self, steps: list) -> None:
        daily: dict[str, float] = defaultdict(float)
        for r in steps:
            if r.get("date") and r.get("value") is not None:
                daily[r["date"]] += r["value"]
        for day, total in daily.items():
            step_id = f"steps_{hashlib.md5(day.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (v:Vital {id: $id})
                SET v.type = 'Steps', v.value = $value, v.unit = 'steps',
                    v.date = $date, v.source = 'apple_health'
                WITH v
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_VITAL]->(v)
                """,
                {"id": step_id, "value": str(int(total)), "date": day},
            )
