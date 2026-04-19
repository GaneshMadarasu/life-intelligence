"""Google Calendar sync — pulls upcoming events into the Life Intelligence timeline graph.

Supports two auth paths:
  1. OAuth2 via browser (first-time setup)
  2. Service account JSON (for automated environments)

Setup:
  1. Create a project in Google Cloud Console
  2. Enable the Google Calendar API
  3. Create OAuth2 credentials (Desktop app) → download client_secret.json
  4. Add to .env:
       GOOGLE_CLIENT_SECRET_FILE=path/to/client_secret.json
       GOOGLE_CALENDAR_IDS=primary,work@example.com

Run:
  python scripts/gcal_sync.py auth     # first-time OAuth
  python scripts/gcal_sync.py sync     # pull next 90 days
  python scripts/gcal_sync.py status   # show last sync info
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_FILE = Path(".gcal_tokens.json")
_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Calendar event categories to ingest as timeline nodes
_HEALTH_KEYWORDS = [
    "doctor", "dentist", "therapy", "appointment", "clinic", "hospital",
    "checkup", "check-up", "lab", "blood test", "ultrasound", "mri", "scan",
    "prescription", "physio", "pharmacy", "optometrist", "dermatologist",
]
_FINANCE_KEYWORDS = [
    "tax", "accountant", "bank", "insurance", "renewal", "premium",
    "mortgage", "payment due", "bill", "invoice",
]
_CAREER_KEYWORDS = [
    "interview", "performance review", "1:1", "meeting", "conference",
    "standup", "sprint", "deadline", "presentation", "training",
]


class GoogleCalendarSync:
    def __init__(self, neo4j_client) -> None:
        self.neo4j = neo4j_client
        self._creds = None

    # ── Authentication ─────────────────────────────────────────────────────

    def authenticate(self) -> str:
        """Start OAuth2 flow — returns URL to open in browser."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise RuntimeError(
                "google-auth-oauthlib is required. Run: pip install google-auth-oauthlib google-api-python-client"
            )
        secret_file = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
        if not Path(secret_file).exists():
            raise RuntimeError(
                f"Google client secret not found at '{secret_file}'. "
                "Download from Google Cloud Console → APIs & Services → Credentials."
            )
        flow = InstalledAppFlow.from_client_secrets_file(secret_file, _SCOPES)
        # Return auth URL for the user to open
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    def complete_auth(self, code: str) -> dict:
        """Complete OAuth2 with the authorization code from the redirect URL."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise RuntimeError("google-auth-oauthlib is required.")
        secret_file = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
        flow = InstalledAppFlow.from_client_secrets_file(secret_file, _SCOPES)
        flow.fetch_token(code=code)
        creds = flow.credentials
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or _SCOPES),
        }
        _TOKEN_FILE.write_text(json.dumps(token_data))
        _TOKEN_FILE.chmod(0o600)
        return {"authenticated": True, "scopes": token_data["scopes"]}

    def _get_service(self):
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            raise RuntimeError(
                "google-api-python-client is required. Run: pip install google-api-python-client google-auth-oauthlib"
            )

        if not _TOKEN_FILE.exists():
            raise RuntimeError("Not authenticated. Run: python scripts/gcal_sync.py auth")

        token_data = json.loads(_TOKEN_FILE.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", _SCOPES),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            _TOKEN_FILE.write_text(json.dumps(token_data))

        self._creds = creds
        return build("calendar", "v3", credentials=creds)

    # ── Sync ───────────────────────────────────────────────────────────────

    def run(self, days_ahead: int = 90, days_back: int = 30) -> dict[str, Any]:
        """Sync calendar events into the timeline graph."""
        service = self._get_service()

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=days_back)).isoformat()
        time_max = (now + timedelta(days=days_ahead)).isoformat()

        calendar_ids = [
            c.strip()
            for c in os.getenv("GOOGLE_CALENDAR_IDS", "primary").split(",")
            if c.strip()
        ]

        ingested = 0
        skipped = 0

        for cal_id in calendar_ids:
            try:
                events_result = (
                    service.events()
                    .list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=500,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )
                events = events_result.get("items", [])
                for event in events:
                    self._ingest_event(event, cal_id)
                    ingested += 1
            except Exception as e:
                logger.warning("Failed to sync calendar %s: %s", cal_id, e)
                skipped += 1

        return {
            "ingested": ingested,
            "skipped": skipped,
            "calendars": calendar_ids,
            "time_range": {"from": time_min[:10], "to": time_max[:10]},
        }

    def _ingest_event(self, event: dict, calendar_id: str) -> None:
        title = event.get("summary", "Untitled Event")
        description = event.get("description", "")
        location = event.get("location", "")
        start_raw = event.get("start", {})
        event_date = start_raw.get("date") or start_raw.get("dateTime", "")[:10]
        event_id = event.get("id", hashlib.md5(title.encode()).hexdigest()[:12])
        node_id = f"gcal_{event_id[:16]}"

        # Classify the event
        text_lower = (title + " " + description).lower()
        domain = "general"
        if any(kw in text_lower for kw in _HEALTH_KEYWORDS):
            domain = "healthcare"
        elif any(kw in text_lower for kw in _FINANCE_KEYWORDS):
            domain = "finances"
        elif any(kw in text_lower for kw in _CAREER_KEYWORDS):
            domain = "career"

        self.neo4j.run_query(
            """
            MERGE (e:CalendarEvent {id: $id})
            SET e.title = $title, e.description = $description,
                e.location = $location, e.date = $date,
                e.calendar_id = $calendar_id, e.domain = $domain,
                e.source = 'google_calendar'
            WITH e
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_CALENDAR_EVENT]->(e)
            """,
            {
                "id": node_id,
                "title": title,
                "description": description[:500],
                "location": location,
                "date": event_date,
                "calendar_id": calendar_id,
                "domain": domain,
            },
        )

        if event_date:
            self.neo4j.link_document_to_timepoint(node_id, event_date)

    def get_status(self) -> dict[str, Any]:
        if not _TOKEN_FILE.exists():
            return {"authenticated": False}
        try:
            token_data = json.loads(_TOKEN_FILE.read_text())
            return {
                "authenticated": True,
                "calendars": os.getenv("GOOGLE_CALENDAR_IDS", "primary").split(","),
                "scopes": token_data.get("scopes", []),
            }
        except Exception as e:
            return {"authenticated": False, "error": str(e)}

    def get_upcoming_events(self, days: int = 14) -> list[dict]:
        """Return upcoming events for display in the UI."""
        from datetime import date
        cutoff = (date.today() + timedelta(days=days)).isoformat()
        today = date.today().isoformat()
        return self.neo4j.run_query(
            """
            MATCH (p:Person {id: 'primary'})-[:HAS_CALENDAR_EVENT]->(e:CalendarEvent)
            WHERE e.date >= $today AND e.date <= $cutoff
            RETURN e.title AS title, e.date AS date, e.location AS location,
                   e.domain AS domain, e.description AS description
            ORDER BY e.date
            LIMIT 20
            """,
            {"today": today, "cutoff": cutoff},
        )
