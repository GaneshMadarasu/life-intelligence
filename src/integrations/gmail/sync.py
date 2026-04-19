"""Gmail integration — reads domain-relevant emails into the knowledge graph.

Uses the Gmail API (read-only scope) to fetch emails classified by domain,
extract structured entities using Claude, and write them as Email nodes.

Setup:
  1. In Google Cloud Console, add Gmail API to your existing project
  2. Edit your OAuth2 credentials to add the gmail.readonly scope
  3. Re-download client_secret.json (or reuse the existing one)
  4. Add to .env:
       GOOGLE_CLIENT_SECRET_FILE=client_secret.json
       GMAIL_MAX_EMAILS_PER_DOMAIN=50

Run:
  python scripts/gmail_sync.py auth
  python scripts/gmail_sync.py auth-complete --code YOUR_CODE
  python scripts/gmail_sync.py sync
  python scripts/gmail_sync.py search --query "lab results"
  python scripts/gmail_sync.py status
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKEN_FILE = Path(".gmail_tokens.json")
_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Domain-specific Gmail search queries
_DOMAIN_QUERIES: dict[str, str] = {
    "healthcare": (
        "subject:(appointment OR results OR lab OR prescription OR referral OR "
        "medication OR diagnosis OR test OR blood OR imaging OR MRI OR ultrasound OR "
        "therapy OR checkup OR vaccine OR insurance EOB) OR "
        "from:(lab OR doctor OR clinic OR hospital OR pharmacy OR health OR medical OR "
        "quest OR labcorp OR kaiser OR mayo OR aetna OR bcbs OR cigna)"
    ),
    "finances": (
        "subject:(invoice OR payment OR statement OR tax OR insurance OR renewal OR "
        "bill OR account OR transaction OR receipt OR W-2 OR 1099 OR deductible OR "
        "premium OR balance OR deposit OR wire OR transfer) OR "
        "from:(bank OR chase OR wellsfargo OR bofa OR citi OR paypal OR stripe OR "
        "venmo OR quickbooks OR intuit OR irs OR turbotax OR insurance OR fidelity OR "
        "schwab OR vanguard OR robinhood)"
    ),
    "career": (
        "subject:(offer letter OR interview OR performance review OR salary OR "
        "promotion OR contract OR onboarding OR job offer OR background check OR "
        "reference OR resignation OR termination OR raise OR bonus OR equity) OR "
        "from:(linkedin OR workday OR greenhouse OR lever OR icims OR taleo OR "
        "bamboohr OR rippling OR gusto OR adp)"
    ),
}

# Keywords for fallback local classification (subject + sender)
_HEALTH_KW = [
    "doctor", "clinic", "hospital", "lab", "prescription", "appointment",
    "medication", "diagnosis", "results", "blood test", "referral", "therapy",
    "pharmacy", "vaccine", "health", "medical", "dental", "vision", "eob",
]
_FINANCE_KW = [
    "invoice", "payment", "statement", "tax", "insurance", "renewal", "bill",
    "account", "transaction", "receipt", "deposit", "bank", "credit", "debit",
    "w-2", "1099", "premium", "deductible", "balance", "refund",
]
_CAREER_KW = [
    "offer letter", "interview", "performance review", "salary", "promotion",
    "contract", "onboarding", "job offer", "background check", "resignation",
    "bonus", "equity", "raise", "termination", "hr", "recruiter",
]

# Claude extraction prompt per domain
_EXTRACT_PROMPTS: dict[str, str] = {
    "healthcare": """Extract structured health information from this email.
Return JSON only with these fields (use null if not found):
{
  "provider": "doctor/lab/clinic name",
  "appointment_date": "YYYY-MM-DD or null",
  "appointment_type": "e.g. lab test, checkup, therapy",
  "test_names": ["list of lab test names"],
  "results_summary": "brief summary of any results",
  "medications_mentioned": ["list of medication names"],
  "follow_up_required": true/false,
  "follow_up_date": "YYYY-MM-DD or null"
}""",
    "finances": """Extract structured financial information from this email.
Return JSON only with these fields (use null if not found):
{
  "transaction_type": "e.g. invoice, payment, statement, tax document",
  "amount": 0.00,
  "currency": "USD",
  "merchant_or_sender": "company/sender name",
  "account_last4": "last 4 digits or null",
  "due_date": "YYYY-MM-DD or null",
  "document_period": "e.g. January 2024",
  "is_actionable": true/false,
  "action_required": "brief description or null"
}""",
    "career": """Extract structured career information from this email.
Return JSON only with these fields (use null if not found):
{
  "event_type": "e.g. offer letter, interview, review, contract",
  "company": "company name",
  "role": "job title or null",
  "salary_mentioned": 0.00,
  "currency": "USD",
  "start_date": "YYYY-MM-DD or null",
  "deadline": "YYYY-MM-DD or null",
  "location": "city/remote or null",
  "is_actionable": true/false,
  "action_required": "brief description or null"
}""",
}


class GmailSync:
    """Syncs domain-relevant Gmail emails into the Life Intelligence graph."""

    def __init__(self, neo4j_client, anthropic_client=None) -> None:
        self.neo4j = neo4j_client
        self._anthropic = anthropic_client
        self._max_per_domain = int(os.getenv("GMAIL_MAX_EMAILS_PER_DOMAIN", "50"))

    # ── Authentication ──────────────────────────────────────────────────────

    def authenticate(self) -> str:
        """Start OAuth2 flow — returns URL for the user to open."""
        flow = self._make_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        return auth_url

    def complete_auth(self, code: str) -> dict:
        """Complete OAuth2 with the authorization code from the redirect URL."""
        flow = self._make_flow()
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
        logger.info("Gmail OAuth2 tokens saved to %s", _TOKEN_FILE)
        return {"authenticated": True, "scopes": token_data["scopes"]}

    def _make_flow(self):
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
        return InstalledAppFlow.from_client_secrets_file(secret_file, _SCOPES)

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
            raise RuntimeError("Not authenticated. Run: python scripts/gmail_sync.py auth")

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

        return build("gmail", "v1", credentials=creds)

    # ── Sync ────────────────────────────────────────────────────────────────

    def run(
        self,
        days_back: int = 90,
        domains: list[str] | None = None,
        extract_entities: bool = True,
    ) -> dict[str, Any]:
        """Fetch and ingest domain-relevant emails."""
        service = self._get_service()
        target_domains = domains or list(_DOMAIN_QUERIES.keys())

        after_ts = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp())
        total_ingested = 0
        total_skipped = 0
        by_domain: dict[str, int] = {}

        for domain in target_domains:
            query = _DOMAIN_QUERIES.get(domain, "")
            full_query = f"{query} after:{after_ts}"
            emails = self._fetch_emails(service, full_query, self._max_per_domain)
            ingested = 0
            for email_data in emails:
                # Reclassify locally in case API query over-fetched
                email_data["domain"] = self._classify(
                    email_data.get("subject", ""),
                    email_data.get("sender", ""),
                    email_data.get("snippet", ""),
                ) or domain

                if extract_entities and self._anthropic:
                    email_data["extracted_entities"] = self._extract_entities(
                        email_data, email_data["domain"]
                    )

                if self._ingest_email(email_data):
                    ingested += 1
                else:
                    total_skipped += 1

            by_domain[domain] = ingested
            total_ingested += ingested
            logger.info("Gmail sync: %d emails ingested for domain=%s", ingested, domain)

        return {
            "total_ingested": total_ingested,
            "total_skipped": total_skipped,
            "by_domain": by_domain,
            "days_back": days_back,
        }

    def search_and_ingest(self, gmail_query: str, domain: str = "general") -> dict[str, Any]:
        """Ad-hoc search using any Gmail query string."""
        service = self._get_service()
        emails = self._fetch_emails(service, gmail_query, 100)
        ingested = 0
        for email_data in emails:
            email_data["domain"] = domain
            if self._ingest_email(email_data):
                ingested += 1
        return {"ingested": ingested, "query": gmail_query}

    # ── Fetch & parse ───────────────────────────────────────────────────────

    def _fetch_emails(self, service, query: str, max_results: int) -> list[dict]:
        """List message IDs matching query, then fetch each message."""
        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except Exception as e:
            logger.warning("Gmail list failed for query '%s': %s", query[:80], e)
            return []

        messages = response.get("messages", [])
        results = []
        for msg_stub in messages:
            try:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_stub["id"], format="full")
                    .execute()
                )
                parsed = self._parse_message(msg)
                if parsed:
                    results.append(parsed)
            except Exception as e:
                logger.debug("Failed to fetch message %s: %s", msg_stub["id"], e)
        return results

    def _parse_message(self, msg: dict) -> dict | None:
        """Parse a Gmail API message into a clean dict."""
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(no subject)")
        sender = headers.get("from", "")
        date_str = headers.get("date", "")
        msg_id = msg.get("id", "")
        snippet = msg.get("snippet", "")
        labels = msg.get("labelIds", [])

        # Parse date
        email_date = self._parse_email_date(date_str)

        # Extract body text
        body = self._extract_body(msg.get("payload", {}))

        # Build a deduplicated node ID
        node_id = "gmail_" + hashlib.md5(msg_id.encode()).hexdigest()[:16]

        return {
            "id": node_id,
            "message_id": msg_id,
            "subject": subject[:500],
            "sender": sender[:200],
            "date": email_date,
            "snippet": snippet[:500],
            "body": body[:3000],  # Truncate for privacy + token limits
            "labels": labels,
            "domain": "general",
            "extracted_entities": {},
        }

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract plain-text body from MIME payload."""
        mime = payload.get("mimeType", "")

        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        if mime == "text/html":
            data = payload.get("body", {}).get("data", "")
            if data:
                html = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                return re.sub(r"<[^>]+>", " ", html).strip()

        # Recurse into multipart
        for part in payload.get("parts", []):
            text = self._extract_body(part)
            if text:
                return text
        return ""

    def _parse_email_date(self, date_str: str) -> str:
        """Parse RFC 2822 date string to ISO date."""
        if not date_str:
            return ""
        from email.utils import parsedate_to_datetime
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.date().isoformat()
        except Exception:
            # Try simple pattern
            m = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
            return m.group(1) if m else ""

    # ── Classification ──────────────────────────────────────────────────────

    def _classify(self, subject: str, sender: str, snippet: str) -> str | None:
        """Classify email into a domain using keyword matching."""
        text = (subject + " " + sender + " " + snippet).lower()
        hc = sum(1 for kw in _HEALTH_KW if kw in text)
        fi = sum(1 for kw in _FINANCE_KW if kw in text)
        ca = sum(1 for kw in _CAREER_KW if kw in text)
        best = max(hc, fi, ca)
        if best == 0:
            return None
        if hc == best:
            return "healthcare"
        if fi == best:
            return "finances"
        return "career"

    # ── Entity extraction ───────────────────────────────────────────────────

    def _extract_entities(self, email_data: dict, domain: str) -> dict:
        """Use Claude to extract structured entities from email body."""
        if not self._anthropic or domain not in _EXTRACT_PROMPTS:
            return {}
        body = email_data.get("body", "") or email_data.get("snippet", "")
        if not body.strip():
            return {}
        try:
            prompt = _EXTRACT_PROMPTS[domain]
            response = self._anthropic.messages.create(
                model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
                max_tokens=512,
                system=prompt,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Subject: {email_data.get('subject', '')}\n"
                        f"From: {email_data.get('sender', '')}\n"
                        f"Date: {email_data.get('date', '')}\n\n"
                        f"{body[:2000]}"
                    ),
                }],
            )
            text = response.content[0].text.strip()
            # Extract JSON block
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as e:
            logger.debug("Entity extraction failed for email %s: %s", email_data.get("id"), e)
        return {}

    # ── Graph ingestion ─────────────────────────────────────────────────────

    def _ingest_email(self, email_data: dict) -> bool:
        """Write an Email node to Neo4j. Returns True if new/updated."""
        node_id = email_data.get("id", "")
        if not node_id or not email_data.get("date"):
            return False

        entities_json = json.dumps(email_data.get("extracted_entities", {}))
        labels_str = ",".join(email_data.get("labels", []))

        self.neo4j.run_query(
            """
            MERGE (e:Email {id: $id})
            SET e.subject = $subject,
                e.sender = $sender,
                e.date = $date,
                e.snippet = $snippet,
                e.domain = $domain,
                e.labels = $labels,
                e.extracted_entities = $entities,
                e.source = 'gmail'
            WITH e
            MATCH (p:Person {id: 'primary'})
            MERGE (p)-[:HAS_EMAIL]->(e)
            """,
            {
                "id": node_id,
                "subject": email_data.get("subject", ""),
                "sender": email_data.get("sender", ""),
                "date": email_data.get("date", ""),
                "snippet": email_data.get("snippet", ""),
                "domain": email_data.get("domain", "general"),
                "labels": labels_str,
                "entities": entities_json,
            },
        )

        # Link to timeline
        if email_data.get("date"):
            try:
                self.neo4j.link_document_to_timepoint(node_id, email_data["date"])
            except Exception:
                pass

        return True

    # ── Query helpers ───────────────────────────────────────────────────────

    def get_emails(
        self,
        domain: str | None = None,
        limit: int = 50,
        days_back: int | None = None,
    ) -> list[dict]:
        """Query ingested emails from Neo4j."""
        from datetime import date, timedelta
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if domain:
            conditions.append("e.domain = $domain")
            params["domain"] = domain
        if days_back:
            cutoff = (date.today() - timedelta(days=days_back)).isoformat()
            conditions.append("e.date >= $cutoff")
            params["cutoff"] = cutoff

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        return self.neo4j.run_query(
            f"""
            MATCH (p:Person {{id: 'primary'}})-[:HAS_EMAIL]->(e:Email)
            {where}
            RETURN e.id AS id, e.subject AS subject, e.sender AS sender,
                   e.date AS date, e.domain AS domain, e.snippet AS snippet,
                   e.extracted_entities AS extracted_entities
            ORDER BY e.date DESC
            LIMIT $limit
            """,
            params,
        )

    def get_status(self) -> dict[str, Any]:
        if not _TOKEN_FILE.exists():
            return {"authenticated": False, "message": "Run: python scripts/gmail_sync.py auth"}
        try:
            token_data = json.loads(_TOKEN_FILE.read_text())
            counts = self.neo4j.run_query(
                """
                MATCH (p:Person {id: 'primary'})-[:HAS_EMAIL]->(e:Email)
                RETURN e.domain AS domain, count(e) AS count
                ORDER BY count DESC
                """
            )
            return {
                "authenticated": True,
                "scopes": token_data.get("scopes", []),
                "email_counts": {r["domain"]: r["count"] for r in counts},
                "total_emails": sum(r["count"] for r in counts),
            }
        except Exception as e:
            return {"authenticated": False, "error": str(e)}
