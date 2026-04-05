"""
WhoopSync — fetches the last N days from the Whoop API and writes everything
into Neo4j via the existing FitnessGraphBuilder.

  from src.integrations.whoop.sync import WhoopSync
  sync = WhoopSync(neo4j_client, vector_store)
  result = sync.run(days=30)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.integrations.whoop.client import WhoopClient, TOKEN_FILE
from src.integrations.whoop import mapper
from src.domains.healthcare.verticals.fitness.graph_builder import FitnessGraphBuilder

logger = logging.getLogger(__name__)

SYNC_STATE_FILE = Path(".whoop_sync_state.json")


class WhoopSync:
    def __init__(self, neo4j_client, vector_store=None) -> None:
        self.neo4j         = neo4j_client
        self.client        = WhoopClient.from_env()
        self.graph_builder = FitnessGraphBuilder(neo4j_client)

    # ── State tracking ────────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if SYNC_STATE_FILE.exists():
            return json.loads(SYNC_STATE_FILE.read_text())
        return {}

    def _save_state(self, state: dict) -> None:
        SYNC_STATE_FILE.write_text(json.dumps(state, indent=2))

    def last_sync_at(self) -> str | None:
        return self._load_state().get("last_sync_at")

    # ── Date window helpers ───────────────────────────────────────────────────

    @staticmethod
    def _window(days: int) -> tuple[str, str]:
        now   = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        fmt   = "%Y-%m-%dT%H:%M:%SZ"
        return start.strftime(fmt), now.strftime(fmt)

    # ── Main sync ─────────────────────────────────────────────────────────────

    def run(self, days: int = 30) -> dict[str, Any]:
        """
        Fetch and ingest the last `days` days of Whoop data.
        Returns a summary dict with counts for each data type.
        """
        if not self.client.is_authenticated():
            raise RuntimeError(
                "Not authenticated. Run: python scripts/whoop_sync.py auth"
            )

        start, end = self._window(days)
        logger.info("Syncing Whoop data from %s to %s", start, end)

        counts: dict[str, int] = {
            "recoveries": 0,
            "sleeps": 0,
            "workouts": 0,
            "cycles": 0,
            "errors": 0,
        }

        # ── Recoveries (HRV, RHR, recovery score) ────────────────────────────
        try:
            recoveries = self.client.get_recoveries(start, end)
            for r in recoveries:
                try:
                    mapped = mapper.map_recovery(r)
                    if mapped.get("date"):
                        self.graph_builder.build_whoop_recovery(mapped)
                        counts["recoveries"] += 1
                except Exception as e:
                    logger.warning("Recovery mapping error: %s", e)
                    counts["errors"] += 1
            logger.info("Ingested %d recovery records", counts["recoveries"])
        except Exception as e:
            logger.error("Failed to fetch recoveries: %s", e)
            counts["errors"] += 1

        # ── Sleeps ────────────────────────────────────────────────────────────
        try:
            sleeps = self.client.get_sleeps(start, end)
            for s in sleeps:
                if s.get("nap"):
                    continue  # skip naps by default
                try:
                    mapped = mapper.map_sleep(s)
                    if mapped.get("date"):
                        self.graph_builder._build_sleep_records([mapped])
                        counts["sleeps"] += 1
                except Exception as e:
                    logger.warning("Sleep mapping error: %s", e)
                    counts["errors"] += 1
            logger.info("Ingested %d sleep records", counts["sleeps"])
        except Exception as e:
            logger.error("Failed to fetch sleeps: %s", e)
            counts["errors"] += 1

        # ── Workouts ──────────────────────────────────────────────────────────
        try:
            workouts = self.client.get_workouts(start, end)
            for w in workouts:
                try:
                    mapped = mapper.map_workout(w)
                    if mapped.get("date"):
                        self.graph_builder._build_workouts([mapped])
                        counts["workouts"] += 1
                except Exception as e:
                    logger.warning("Workout mapping error: %s", e)
                    counts["errors"] += 1
            logger.info("Ingested %d workouts", counts["workouts"])
        except Exception as e:
            logger.error("Failed to fetch workouts: %s", e)
            counts["errors"] += 1

        # ── Daily cycles (strain) ─────────────────────────────────────────────
        try:
            cycles = self.client.get_cycles(start, end)
            for c in cycles:
                try:
                    mapped = mapper.map_cycle(c)
                    if mapped.get("date"):
                        self.graph_builder.build_whoop_cycle(mapped)
                        counts["cycles"] += 1
                except Exception as e:
                    logger.warning("Cycle mapping error: %s", e)
                    counts["errors"] += 1
            logger.info("Ingested %d daily cycles", counts["cycles"])
        except Exception as e:
            logger.error("Failed to fetch cycles: %s", e)
            counts["errors"] += 1

        # ── Save sync state ───────────────────────────────────────────────────
        now_iso = datetime.now(timezone.utc).isoformat()
        self._save_state({
            "last_sync_at": now_iso,
            "last_sync_days": days,
            "last_sync_counts": counts,
        })

        return {
            "synced_at": now_iso,
            "date_range": {"start": start, "end": end},
            "days": days,
            "counts": counts,
        }

    def get_status(self) -> dict[str, Any]:
        """Return connection + last sync status."""
        state = self._load_state()
        token_exists = TOKEN_FILE.exists()

        profile = None
        if token_exists and self.client.is_authenticated():
            try:
                profile = self.client.get_profile()
            except Exception:
                pass

        return {
            "connected": token_exists,
            "authenticated": self.client.is_authenticated(),
            "profile": profile,
            "last_sync_at": state.get("last_sync_at"),
            "last_sync_days": state.get("last_sync_days"),
            "last_sync_counts": state.get("last_sync_counts"),
            "token_file": str(TOKEN_FILE),
        }
