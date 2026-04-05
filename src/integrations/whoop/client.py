"""
Whoop API OAuth2 client.

Flow:
  1. whoop_sync.py auth  — opens browser, captures callback, saves tokens to .whoop_tokens.json
  2. On each API call tokens are refreshed automatically when expired.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import queue
import secrets
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any, Iterator

import httpx

logger = logging.getLogger(__name__)

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE  = "https://api.prod.whoop.com/developer/v1"
REDIRECT_URI    = "http://localhost:8080/callback"
SCOPES          = "offline read:recovery read:sleep read:workout read:profile read:cycles read:body_measurement"

TOKEN_FILE = Path(".whoop_tokens.json")


# ── Local callback server ─────────────────────────────────────────────────────

def _make_handler(code_queue: queue.Queue):
    """Return a handler class that pushes the auth code into a Queue."""
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            params = dict(urllib.parse.parse_qsl(parsed.query))
            code = params.get("code")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            if code:
                code_queue.put(code)
                self.wfile.write(b"<h2>Whoop connected! You can close this tab.</h2>")
            else:
                self.wfile.write(b"<h2>No code received - please try again.</h2>")

        def log_message(self, fmt, *args) -> None:
            pass

    return _Handler


def _run_callback_server(code_queue: queue.Queue, stop_event: threading.Event) -> None:
    handler = _make_handler(code_queue)
    server = http.server.HTTPServer(("localhost", 8080), handler)
    server.timeout = 1
    while not stop_event.is_set():
        server.handle_request()
    server.server_close()


# ── Token storage ─────────────────────────────────────────────────────────────

def _save_tokens(tokens: dict) -> None:
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2))
    TOKEN_FILE.chmod(0o600)


def _load_tokens() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


# ── WhoopClient ───────────────────────────────────────────────────────────────

class WhoopClient:
    """Authenticated Whoop API client with auto token refresh."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id     = client_id
        self.client_secret = client_secret
        self._tokens: dict | None = _load_tokens()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def authenticate(self, manual_code: str | None = None) -> None:
        """
        Run the OAuth2 browser flow and save tokens.

        If `manual_code` is given (a raw code or full callback URL), skips the
        browser flow and exchanges it directly — useful when the automatic
        callback server can't be reached.
        """
        state = secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id":     self.client_id,
            "redirect_uri":  REDIRECT_URI,
            "scope":         SCOPES,
            "state":         state,
        }
        auth_url = WHOOP_AUTH_URL + "?" + urllib.parse.urlencode(params)

        # ── Manual code provided directly ─────────────────────────────────────
        if manual_code:
            code = self._parse_code(manual_code)
            if not code:
                raise RuntimeError("Could not extract code from provided value.")
            self._exchange_code(code)
            print("✓ Whoop tokens saved to .whoop_tokens.json")
            return

        # ── Automatic browser + callback server ───────────────────────────────
        code_queue: queue.Queue = queue.Queue()
        stop = threading.Event()
        server_thread = threading.Thread(
            target=_run_callback_server, args=(code_queue, stop), daemon=True
        )
        server_thread.start()

        print(f"\nOpening browser for Whoop authentication...")
        print(f"If the browser doesn't open, visit:\n  {auth_url}\n")
        webbrowser.open(auth_url)

        print("Waiting for Whoop callback (authorise in your browser)...", flush=True)
        code = None
        try:
            code = code_queue.get(timeout=180)
        except queue.Empty:
            pass
        finally:
            stop.set()
            server_thread.join(timeout=2)

        if not code:
            print(
                "\n[!] Automatic callback timed out.\n"
                "    After authorising, copy the URL from your browser's address bar\n"
                "    (it starts with: http://localhost:8080/callback?code=...)\n"
                "    Then run:\n\n"
                "      python scripts/whoop_sync.py auth --code 'PASTE_FULL_URL_HERE'\n"
            )
            raise RuntimeError("Auth timed out — see instructions above.")

        self._exchange_code(code)
        print("✓ Whoop tokens saved to .whoop_tokens.json")

    @staticmethod
    def _parse_code(raw: str) -> str:
        """Extract code from a full URL or return raw value if already a code."""
        raw = raw.strip()
        if raw.startswith("http"):
            parsed = urllib.parse.urlparse(raw)
            return dict(urllib.parse.parse_qsl(parsed.query)).get("code", "")
        return raw

    def _exchange_code(self, code: str) -> None:
        resp = httpx.post(
            WHOOP_TOKEN_URL,
            data={
                "grant_type":    "authorization_code",
                "code":          code,
                "redirect_uri":  REDIRECT_URI,
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        tokens["saved_at"] = time.time()
        _save_tokens(tokens)
        self._tokens = tokens

    def _refresh(self) -> None:
        if not self._tokens or "refresh_token" not in self._tokens:
            raise RuntimeError("No refresh token — run `whoop_sync.py auth` first.")
        resp = httpx.post(
            WHOOP_TOKEN_URL,
            data={
                "grant_type":    "refresh_token",
                "refresh_token": self._tokens["refresh_token"],
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        tokens["saved_at"] = time.time()
        _save_tokens(tokens)
        self._tokens = tokens
        logger.debug("Whoop tokens refreshed")

    def _is_expired(self) -> bool:
        if not self._tokens:
            return True
        saved_at = self._tokens.get("saved_at", 0)
        expires_in = self._tokens.get("expires_in", 3600)
        return (time.time() - saved_at) >= (expires_in - 60)  # 60s buffer

    def _access_token(self) -> str:
        if self._is_expired():
            self._refresh()
        return self._tokens["access_token"]

    def is_authenticated(self) -> bool:
        return self._tokens is not None

    # ── API helpers ───────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{WHOOP_API_BASE}{path}"
        headers = {"Authorization": f"Bearer {self._access_token()}"}
        resp = httpx.get(url, headers=headers, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str, params: dict | None = None) -> Iterator[dict]:
        """Yield every record across all pages."""
        params = dict(params or {})
        params.setdefault("limit", 25)
        while True:
            data = self._get(path, params)
            for record in data.get("records", []):
                yield record
            next_token = data.get("next_token")
            if not next_token:
                break
            params["nextToken"] = next_token

    # ── Public API calls ──────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        return self._get("/user/profile/basic")

    def get_recoveries(self, start: str, end: str) -> list[dict]:
        return list(self._paginate("/recovery", {"start": start, "end": end}))

    def get_sleeps(self, start: str, end: str) -> list[dict]:
        return list(self._paginate("/sleep", {"start": start, "end": end}))

    def get_workouts(self, start: str, end: str) -> list[dict]:
        return list(self._paginate("/workout", {"start": start, "end": end}))

    def get_cycles(self, start: str, end: str) -> list[dict]:
        return list(self._paginate("/cycle", {"start": start, "end": end}))

    # ── Convenience ───────────────────────────────────────────────────────────

    @staticmethod
    def from_env() -> "WhoopClient":
        client_id     = os.environ.get("WHOOP_CLIENT_ID", "")
        client_secret = os.environ.get("WHOOP_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise EnvironmentError(
                "WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET must be set in .env\n"
                "Get your credentials at https://developer.whoop.com/docs/developing/oauth2/"
            )
        return WhoopClient(client_id, client_secret)
