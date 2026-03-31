"""Universal timeline manager — cross-domain chronological events."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TimelineManager:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client

    def add_event(
        self,
        date_str: str,
        domain: str,
        vertical: str,
        doc_id: str,
        event_type: str,
        description: str,
    ) -> None:
        self.neo4j.create_timepoint(date_str)
        self.neo4j.run_query(
            """
            MATCH (t:TimePoint {date: date($date)})
            MERGE (e:TimelineEvent {
                doc_id: $doc_id,
                domain: $domain,
                vertical: $vertical,
                event_type: $event_type
            })
            SET e.description = $description,
                e.date = date($date)
            MERGE (e)-[:AT]->(t)
            WITH e
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_EVENT]->(e)
            """,
            {
                "date": date_str[:10],
                "domain": domain,
                "vertical": vertical,
                "doc_id": doc_id,
                "event_type": event_type,
                "description": description,
            },
        )

    def get_timeline(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        domains: list[str] | None = None,
    ) -> list[dict]:
        domain_filter = ""
        params: dict = {"date_from": date_from, "date_to": date_to}
        if domains and "all" not in domains:
            domain_filter = "AND e.domain IN $domains"
            params["domains"] = domains

        results = self.neo4j.run_query(
            f"""
            MATCH (p:Person {{id: 'primary'}})-[:HAS_EVENT]->(e:TimelineEvent)-[:AT]->(t:TimePoint)
            WHERE ($date_from IS NULL OR t.date >= date($date_from))
            AND ($date_to IS NULL OR t.date <= date($date_to))
            {domain_filter}
            RETURN e.domain as domain, e.vertical as vertical,
                   e.event_type as event_type, e.description as description,
                   toString(t.date) as date
            ORDER BY t.date
            """,
            params,
        )
        return results

    def get_events_near(
        self, date_str: str, days_window: int = 30, domains: list[str] | None = None
    ) -> list[dict]:
        return self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_EVENT]->(e:TimelineEvent)-[:AT]->(t:TimePoint)
            WHERE abs(duration.inDays(date($date), t.date).days) <= $window
            RETURN e.domain as domain, e.vertical as vertical,
                   e.event_type as event_type, e.description as description,
                   toString(t.date) as date
            ORDER BY t.date
            """,
            {"date": date_str[:10], "window": days_window},
        )
