"""Shared Neo4j client — backbone schema, domain/vertical registration, all domains share this."""

from __future__ import annotations

import os
import logging
from datetime import date, datetime
from typing import Any

from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_client_instance: "Neo4jClient | None" = None


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self._driver: Driver | None = None

    def connect(self) -> None:
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self._driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", self.uri)

    def close(self) -> None:
        if self._driver:
            self._driver.close()
            self._driver = None

    def run_query(self, cypher: str, params: dict | None = None) -> list[dict]:
        if not self._driver:
            self.connect()
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [dict(record) for record in result]

    def init_backbone_schema(self) -> None:
        """Create all constraints and indexes for the backbone shared schema."""
        constraints = [
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT timepoint_date IF NOT EXISTS FOR (n:TimePoint) REQUIRE n.date IS UNIQUE",
            "CREATE CONSTRAINT provider_name IF NOT EXISTS FOR (n:Provider) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (n:Domain) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT vertical_id IF NOT EXISTS FOR (n:Vertical) REQUIRE n.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX document_domain IF NOT EXISTS FOR (n:Document) ON (n.domain)",
            "CREATE INDEX document_vertical IF NOT EXISTS FOR (n:Document) ON (n.vertical)",
            "CREATE INDEX document_doc_type IF NOT EXISTS FOR (n:Document) ON (n.doc_type)",
            "CREATE INDEX chunk_domain IF NOT EXISTS FOR (n:Chunk) ON (n.domain)",
            "CREATE INDEX chunk_vertical IF NOT EXISTS FOR (n:Chunk) ON (n.vertical)",
        ]
        for stmt in constraints + indexes:
            try:
                self.run_query(stmt)
            except Exception as e:
                logger.debug("Schema stmt skipped: %s — %s", stmt[:60], e)
        logger.info("Backbone schema initialized")

    def register_domain(self, domain_name: str, description: str) -> None:
        self.run_query(
            """
            MERGE (d:Domain {name: $name})
            SET d.description = $description,
                d.status = 'active',
                d.last_updated = $now
            WITH d
            MATCH (p:Person)
            MERGE (p)-[:HAS_DOMAIN]->(d)
            """,
            {"name": domain_name, "description": description, "now": datetime.utcnow().isoformat()},
        )

    def register_vertical(self, domain_name: str, vertical_name: str, description: str) -> None:
        self.run_query(
            """
            MERGE (v:Vertical {id: $vid})
            SET v.name = $vname,
                v.domain = $domain,
                v.description = $description
            WITH v
            MATCH (d:Domain {name: $domain})
            MERGE (d)-[:CONTAINS_VERTICAL]->(v)
            """,
            {
                "vid": f"{domain_name}:{vertical_name}",
                "vname": vertical_name,
                "domain": domain_name,
                "description": description,
            },
        )

    def get_or_create_person(
        self, name: str, dob: str, sex: str, blood_type: str
    ) -> dict:
        results = self.run_query(
            """
            MERGE (p:Person {id: 'primary'})
            SET p.name = $name,
                p.dob = $dob,
                p.sex = $sex,
                p.blood_type = $blood_type
            RETURN p
            """,
            {"name": name, "dob": dob, "sex": sex, "blood_type": blood_type},
        )
        return results[0]["p"] if results else {}

    def create_timepoint(self, date_str: str) -> str:
        """MERGE a TimePoint node and return the date string."""
        try:
            d = date.fromisoformat(date_str[:10])
            week = d.isocalendar()[1]
        except ValueError:
            return date_str
        self.run_query(
            """
            MERGE (t:TimePoint {date: date($date)})
            SET t.year = $year, t.month = $month, t.week = $week
            """,
            {"date": date_str[:10], "year": d.year, "month": d.month, "week": week},
        )
        return date_str[:10]

    def link_document_to_timepoint(self, doc_id: str, date_str: str) -> None:
        self.create_timepoint(date_str)
        self.run_query(
            """
            MATCH (d:Document {id: $doc_id})
            MATCH (t:TimePoint {date: date($date)})
            MERGE (d)-[:OCCURRED_AT]->(t)
            """,
            {"doc_id": doc_id, "date": date_str[:10]},
        )

    def get_domain_stats(self, domain_name: str) -> dict:
        result = self.run_query(
            """
            MATCH (d:Domain {name: $name})
            OPTIONAL MATCH (p:Person)-[:HAS_DOCUMENT]->(doc:Document {domain: $name})
            RETURN d.name as name,
                   count(DISTINCT doc) as document_count
            """,
            {"name": domain_name},
        )
        if not result:
            return {"domain": domain_name, "document_count": 0}
        row = result[0]
        return {"domain": domain_name, "document_count": row.get("document_count", 0)}


def get_client() -> Neo4jClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = Neo4jClient(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "lifeintell2024"),
        )
        _client_instance.connect()
        _client_instance.init_backbone_schema()
    return _client_instance
