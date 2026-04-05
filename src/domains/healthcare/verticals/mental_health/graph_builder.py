"""Mental health graph builder — creates Neo4j nodes from mental health entities."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MentalHealthGraphBuilder:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def build(self, entities: dict[str, Any], file_path: str, metadata: dict) -> str:
        _key = f"{file_path}_{metadata.get('date','')}"
        doc_id = f"mh_{hashlib.md5(_key.encode()).hexdigest()[:16]}"
        self.neo4j.run_query(
            """
            MERGE (d:Document {id: $id})
            SET d.title = $title, d.domain = 'healthcare',
                d.vertical = 'mental_health', d.source_file = $source_file
            WITH d
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_DOCUMENT]->(d)
            """,
            {"id": doc_id, "title": file_path.split("/")[-1], "source_file": file_path},
        )

        self._build_therapy_sessions(entities.get("therapy_sessions", []))
        self._build_mood_entries(entities.get("mood_entries", []))
        self._build_mental_conditions(entities.get("mental_conditions", []))
        self._build_stressors(entities.get("stressors", []))
        self._build_journal_entries(entities.get("journal_entries", []))
        self._build_meditation_sessions(entities.get("meditation_sessions", []))
        return doc_id

    def _build_therapy_sessions(self, sessions: list[dict]) -> None:
        for s in sessions:
            if not s.get("date"):
                continue
            _key = f"{s['date']}_{s.get('therapist','')}"
            sid = f"therapy_{hashlib.md5(_key.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (ts:TherapySession {id: $id})
                SET ts.date = $date, ts.therapist = $therapist,
                    ts.type = $type, ts.notes_summary = $notes_summary,
                    ts.mood_at_session = $mood
                WITH ts
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAD_THERAPY]->(ts)
                """,
                {
                    "id": sid, "date": s["date"],
                    "therapist": s.get("therapist", ""),
                    "type": s.get("type", "other"),
                    "notes_summary": s.get("notes_summary", ""),
                    "mood": s.get("mood_at_session", 0),
                },
            )

    def _build_mood_entries(self, entries: list[dict]) -> None:
        for e in entries:
            if not e.get("date"):
                continue
            eid = f"mood_{hashlib.md5(e['date'].encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (me:MoodEntry {id: $id})
                SET me.date = $date, me.score = $score,
                    me.notes = $notes, me.triggers = $triggers,
                    me.energy_level = $energy, me.anxiety_level = $anxiety
                WITH me
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_MOOD_ENTRY]->(me)
                """,
                {
                    "id": eid, "date": e["date"],
                    "score": e.get("score", 5),
                    "notes": e.get("notes", ""),
                    "triggers": e.get("triggers", ""),
                    "energy": e.get("energy_level", 5),
                    "anxiety": e.get("anxiety_level", 5),
                },
            )

    def _build_mental_conditions(self, conditions: list[dict]) -> None:
        for c in conditions:
            if not c.get("name"):
                continue
            self.neo4j.run_query(
                """
                MERGE (mc:MentalCondition {name: $name})
                SET mc.diagnosed_date = $diagnosed_date,
                    mc.status = $status,
                    mc.treating_provider = $provider
                WITH mc
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_MENTAL_CONDITION]->(mc)
                """,
                {
                    "name": c["name"],
                    "diagnosed_date": c.get("diagnosed_date", ""),
                    "status": c.get("status", "active"),
                    "provider": c.get("treating_provider", ""),
                },
            )

    def _build_stressors(self, stressors: list[dict]) -> None:
        for s in stressors:
            if not s.get("description"):
                continue
            _key = f"{s['description']}_{s.get('start_date','')}"
            sid = f"stressor_{hashlib.md5(_key.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (s:Stressor {id: $id})
                SET s.description = $description,
                    s.category = $category, s.intensity = $intensity,
                    s.start_date = $start_date, s.resolved_date = $resolved_date
                WITH s
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_STRESSOR]->(s)
                """,
                {
                    "id": sid,
                    "description": s["description"],
                    "category": s.get("category", "other"),
                    "intensity": s.get("intensity", 5),
                    "start_date": s.get("start_date", ""),
                    "resolved_date": s.get("resolved_date", ""),
                },
            )

    def _build_journal_entries(self, entries: list[dict]) -> None:
        for e in entries:
            if not e.get("date"):
                continue
            eid = f"journal_{hashlib.md5(e['date'].encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (je:JournalEntry {id: $id})
                SET je.date = $date, je.text_summary = $text_summary,
                    je.sentiment = $sentiment, je.key_themes = $key_themes
                WITH je
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_JOURNAL]->(je)
                """,
                {
                    "id": eid, "date": e["date"],
                    "text_summary": e.get("text_summary", ""),
                    "sentiment": e.get("sentiment", "neutral"),
                    "key_themes": e.get("key_themes", ""),
                },
            )

    def _build_meditation_sessions(self, sessions: list[dict]) -> None:
        for s in sessions:
            if not s.get("date"):
                continue
            _key = f"{s['date']}_{s.get('type','')}"
            sid = f"med_{hashlib.md5(_key.encode()).hexdigest()[:12]}"
            self.neo4j.run_query(
                """
                MERGE (ms:MeditationSession {id: $id})
                SET ms.date = $date, ms.duration_mins = $duration_mins,
                    ms.type = $type, ms.app_used = $app_used, ms.notes = $notes
                WITH ms
                MATCH (p:Person {id: 'primary'})
                MERGE (p)-[:HAS_MEDITATION]->(ms)
                """,
                {
                    "id": sid, "date": s["date"],
                    "duration_mins": s.get("duration_mins", 0),
                    "type": s.get("type", "mindfulness"),
                    "app_used": s.get("app_used", ""),
                    "notes": s.get("notes", ""),
                },
            )
