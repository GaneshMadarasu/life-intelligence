"""Graph retriever — Cypher-based retrieval across all domains."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GraphRetriever:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    # Keywords that signal the user wants wearable/fitness data
    _WHOOP_KEYWORDS = {
        "whoop", "hrv", "recovery", "strain", "rhr", "resting heart",
        "sleep performance", "sleep quality", "workout", "fitness",
        "heart rate variability", "spo2", "respiratory rate", "training load",
        "calories", "overtraining",
    }

    def retrieve(
        self,
        query: str,
        domains: list[str] | None = None,
        verticals: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve graph context relevant to a natural-language query."""
        results: list[dict] = []
        results.extend(self._search_documents(query, domains, verticals, date_from, date_to, top_k))
        results.extend(self._search_entities(query, top_k))

        # Always inject Whoop biometric context for healthcare queries
        query_lower = query.lower()
        want_all = not domains or "all" in domains
        want_healthcare = want_all or "healthcare" in (domains or [])
        if want_healthcare and any(kw in query_lower for kw in self._WHOOP_KEYWORDS):
            results.extend(self._fetch_whoop_context(date_from, top_k))

        # Deduplicate by id
        seen: set[str] = set()
        unique = []
        for r in results:
            key = str(r.get("id") or r.get("text", ""))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:top_k * 2]  # return more so hybrid can rank

    def _search_documents(
        self,
        query: str,
        domains: list[str] | None,
        verticals: list[str] | None,
        date_from: str | None,
        date_to: str | None,
        top_k: int,
    ) -> list[dict]:
        domain_filter = ""
        vertical_filter = ""
        params: dict = {
            "query": query.lower(),
            "date_from": date_from,
            "date_to": date_to,
            "limit": top_k,
        }
        if domains and "all" not in domains:
            domain_filter = "AND d.domain IN $domains"
            params["domains"] = domains
        if verticals and "all" not in verticals:
            vertical_filter = "AND d.vertical IN $verticals"
            params["verticals"] = verticals

        return self.neo4j.run_query(
            f"""
            MATCH (p:Person {{id: 'primary'}})-[:HAS_DOCUMENT]->(d:Document)
            WHERE ($date_from IS NULL OR d.date >= $date_from)
            AND ($date_to IS NULL OR d.date <= $date_to)
            {domain_filter}
            {vertical_filter}
            RETURN d.id AS id, d.title AS title, d.domain AS domain,
                   d.vertical AS vertical, d.date AS date,
                   'document' AS result_type
            ORDER BY d.date DESC
            LIMIT $limit
            """,
            params,
        )

    def _search_entities(self, query: str, top_k: int) -> list[dict]:
        """Search for named entities that match the query terms."""
        terms = [t.strip() for t in query.split() if len(t.strip()) > 3]
        results = []
        for term in terms[:5]:  # limit search terms
            for label in ["Condition", "Medication", "Supplement", "GeneticRisk", "Stressor"]:
                rows = self.neo4j.run_query(
                    f"""
                    MATCH (n:{label})
                    WHERE toLower(n.name) CONTAINS toLower($term)
                    OR toLower(coalesce(n.condition_name, '')) CONTAINS toLower($term)
                    OR toLower(coalesce(n.description, '')) CONTAINS toLower($term)
                    RETURN n.name AS name,
                           coalesce(n.condition_name, n.name, n.description) AS text,
                           '{label}' AS entity_type,
                           'entity' AS result_type
                    LIMIT 3
                    """,
                    {"term": term},
                )
                results.extend(rows)
        return results[:top_k]

    def _fetch_whoop_context(self, date_from: str | None, top_k: int) -> list[dict]:
        """Fetch recent Whoop biometric records and format as text context."""
        from datetime import date, timedelta
        cutoff = date_from or (date.today() - timedelta(days=30)).isoformat()
        results: list[dict] = []

        # Recovery + HRV
        rows = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_RECOVERY]->(r:WhoopRecovery)
            WHERE r.date >= $cutoff
            RETURN r.date AS date, r.recovery_score AS recovery_score,
                   r.hrv_rmssd AS hrv_rmssd, r.resting_hr AS resting_hr,
                   r.spo2_pct AS spo2_pct
            ORDER BY r.date DESC LIMIT 14
            """,
            {"cutoff": cutoff},
        )
        for r in rows:
            text = (
                f"Whoop Recovery {r['date']}: recovery_score={r.get('recovery_score','?')}%, "
                f"HRV={r.get('hrv_rmssd','?')}ms, RHR={r.get('resting_hr','?')}bpm, "
                f"SpO2={r.get('spo2_pct','?')}%"
            )
            results.append({"id": f"wr_{r['date']}", "text": text, "date": r["date"],
                            "result_type": "whoop_recovery"})

        # Daily strain / cycles
        rows = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_WHOOP_CYCLE]->(c:WhoopCycle)
            WHERE c.date >= $cutoff
            RETURN c.date AS date, c.strain AS strain, c.calories AS calories,
                   c.avg_heart_rate AS avg_hr, c.max_heart_rate AS max_hr
            ORDER BY c.date DESC LIMIT 14
            """,
            {"cutoff": cutoff},
        )
        for r in rows:
            text = (
                f"Whoop Daily Cycle {r['date']}: strain={r.get('strain','?')}, "
                f"calories={r.get('calories','?')}, avg_hr={r.get('avg_hr','?')}bpm, "
                f"max_hr={r.get('max_hr','?')}bpm"
            )
            results.append({"id": f"wc_{r['date']}", "text": text, "date": r["date"],
                            "result_type": "whoop_cycle"})

        # Sleep records
        rows = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_SLEEP_RECORD]->(s:SleepRecord)
            WHERE s.date >= $cutoff AND s.source = 'whoop'
            RETURN s.date AS date, s.duration_hours AS dur, s.deep_sleep_hours AS deep,
                   s.rem_hours AS rem, s.sleep_performance_pct AS perf,
                   s.sleep_efficiency_pct AS eff, s.respiratory_rate AS resp,
                   s.disturbances AS disturbances
            ORDER BY s.date DESC LIMIT 14
            """,
            {"cutoff": cutoff},
        )
        for r in rows:
            text = (
                f"Whoop Sleep {r['date']}: total={r.get('dur','?')}h, "
                f"deep={r.get('deep','?')}h, REM={r.get('rem','?')}h, "
                f"performance={r.get('perf','?')}%, efficiency={r.get('eff','?')}%, "
                f"respiratory_rate={r.get('resp','?')}, disturbances={r.get('disturbances','?')}"
            )
            results.append({"id": f"ws_{r['date']}", "text": text, "date": r["date"],
                            "result_type": "whoop_sleep"})

        # Recent workouts
        rows = self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_WORKOUT]->(w:Workout)
            WHERE w.source = 'whoop' AND w.date >= $cutoff
            RETURN w.date AS date, w.type AS type, w.strain_score AS strain,
                   w.duration_mins AS dur, w.calories_burned AS cal,
                   w.avg_heart_rate AS avg_hr, w.max_heart_rate AS max_hr
            ORDER BY w.date DESC LIMIT 14
            """,
            {"cutoff": cutoff},
        )
        for r in rows:
            text = (
                f"Whoop Workout {r['date']}: type={r.get('type','?')}, "
                f"strain={r.get('strain','?')}, duration={r.get('dur','?')}min, "
                f"calories={r.get('cal','?')}, avg_hr={r.get('avg_hr','?')}bpm"
            )
            results.append({"id": f"ww_{r['date']}_{r.get('type','')}", "text": text,
                            "date": r["date"], "result_type": "whoop_workout"})

        return results

    def retrieve_by_entity_type(self, entity_type: str, filters: dict | None = None) -> list[dict]:
        filter_str = ""
        params: dict = filters or {}
        if filters:
            clauses = [f"n.{k} = ${k}" for k in filters]
            filter_str = "WHERE " + " AND ".join(clauses)
        return self.neo4j.run_query(
            f"MATCH (n:{entity_type}) {filter_str} RETURN n LIMIT 50",
            params,
        )

    def get_entity_neighborhood(self, entity_id: str, depth: int = 2) -> list[dict]:
        return self.neo4j.run_query(
            """
            MATCH path = (n {id: $id})-[*1..$depth]-(m)
            RETURN [node in nodes(path) | {labels: labels(node), props: properties(node)}] AS nodes,
                   [rel in relationships(path) | type(rel)] AS relationships
            LIMIT 20
            """,
            {"id": entity_id, "depth": depth},
        )
