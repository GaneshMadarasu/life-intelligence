"""Life Intelligence MCP Server.

Exposes the personal knowledge graph as MCP tools so Claude Desktop
(or any MCP-compatible client) can query your life data natively.

Usage — add to your Claude Desktop MCP config:
  {
    "mcpServers": {
      "life-intelligence": {
        "command": "python",
        "args": ["-m", "src.mcp_server"],
        "cwd": "/path/to/life-intelligence"
      }
    }
  }

Then in Claude Desktop you can ask:
  - "Use life_query to find my latest HRV"
  - "Use life_me to get my health summary"
  - "Use life_alerts to check if I have any health alerts"
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING"), stream=sys.stderr)
logger = logging.getLogger(__name__)

# ── MCP protocol helpers ──────────────────────────────────────────────────────

def _write(obj: dict) -> None:
    print(json.dumps(obj), flush=True)


def _read() -> dict | None:
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line.strip())
    except (json.JSONDecodeError, EOFError):
        return None


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "life_query",
        "description": (
            "Ask any natural-language question about the user's personal life data "
            "(health, fitness, finances, career, legal). Returns a structured answer "
            "with supporting facts, safety warnings, and cross-domain insights."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Natural language question about the user's personal data",
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Domains to search: healthcare, finances, career, legal-contracts, or all",
                    "default": ["all"],
                },
            },
            "required": ["question"],
        },
    },
    {
        "name": "life_me",
        "description": "Get a summary of the user's personal profile and health stats.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "life_timeline",
        "description": "Get a chronological timeline of life events across all domains.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "date_to": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "domains": {"type": "string", "description": "Comma-separated domains, or 'all'", "default": "all"},
            },
        },
    },
    {
        "name": "life_alerts",
        "description": "Get proactive health and life alerts — declining HRV, overdue labs, expiring certifications, insurance renewals.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "life_safety",
        "description": "Run a full safety check — drug interactions, supplement conflicts, genetic pharmacology risks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "life_whoop_today",
        "description": "Get today's Whoop biometrics: recovery score, HRV, resting heart rate, strain, sleep performance.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ── Tool execution ────────────────────────────────────────────────────────────

def _api_get(path: str) -> dict:
    """Call the local Life Intelligence API."""
    import httpx
    base = f"http://127.0.0.1:{os.getenv('APP_PORT', '8000')}"
    try:
        r = httpx.get(f"{base}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _api_post(path: str, body: dict) -> dict:
    import httpx
    base = f"http://127.0.0.1:{os.getenv('APP_PORT', '8000')}"
    try:
        r = httpx.post(f"{base}{path}", json=body, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _execute_tool(name: str, arguments: dict) -> str:
    if name == "life_query":
        result = _api_post("/query", {
            "question": arguments.get("question", ""),
            "domains": arguments.get("domains", ["all"]),
            "top_k": 8,
        })
        if "error" in result:
            return f"Error: {result['error']}"
        answer = result.get("answer", "No answer returned.")
        warnings = result.get("warnings", [])
        insights = result.get("cross_domain_insights", [])
        out = answer
        if warnings:
            out += f"\n\n**Safety Warnings ({len(warnings)}):**\n" + "\n".join(
                f"- {w.get('message', str(w))}" for w in warnings[:5]
            )
        if insights:
            out += f"\n\n**Cross-domain insights ({len(insights)} found)**"
        return out

    elif name == "life_me":
        result = _api_get("/me")
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2)

    elif name == "life_timeline":
        params = []
        if arguments.get("date_from"):
            params.append(f"date_from={arguments['date_from']}")
        if arguments.get("date_to"):
            params.append(f"date_to={arguments['date_to']}")
        if arguments.get("domains"):
            params.append(f"domains={arguments['domains']}")
        qs = ("?" + "&".join(params)) if params else ""
        result = _api_get(f"/timeline{qs}")
        if "error" in result:
            return f"Error: {result['error']}"
        events = result.get("events", [])
        if not events:
            return "No timeline events found for the specified period."
        lines = [f"**{e.get('date', '?')}** — {e.get('title', '')} ({e.get('domain', '')})" for e in events[:30]]
        return f"{result.get('count', 0)} events found:\n\n" + "\n".join(lines)

    elif name == "life_alerts":
        result = _api_get("/alerts")
        if "error" in result:
            return f"Error: {result['error']}"
        alerts = result.get("alerts", [])
        if not alerts:
            return "No active alerts. Everything looks good!"
        lines = []
        for a in alerts:
            severity = a.get("severity", "info")
            emoji = {"high": "🔴", "medium": "🟡", "low": "🔵"}.get(severity, "ℹ️")
            lines.append(f"{emoji} **{a.get('title', '')}**: {a.get('message', '')}")
        return "\n".join(lines)

    elif name == "life_safety":
        result = _api_get("/safety/full")
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2)

    elif name == "life_whoop_today":
        recovery = _api_get("/healthcare/fitness/recovery?days=1")
        strain = _api_get("/healthcare/fitness/strain?days=1")
        sleep = _api_get("/healthcare/fitness/sleep?days=1")

        rec = (recovery.get("records") or [{}])[0]
        cyc = (strain.get("daily_cycles") or [{}])[0]
        slp = (sleep.get("records") or [{}])[0]

        lines = ["**Today's Whoop Biometrics:**"]
        if rec:
            lines.append(f"- Recovery: {rec.get('recovery_score', '—')}%")
            lines.append(f"- HRV: {rec.get('hrv_rmssd', '—')} ms")
            lines.append(f"- Resting HR: {rec.get('resting_hr', '—')} bpm")
            lines.append(f"- SpO2: {rec.get('spo2_pct', '—')}%")
        if cyc:
            lines.append(f"- Day Strain: {cyc.get('strain', '—')}")
        if slp:
            lines.append(f"- Sleep Performance: {slp.get('sleep_performance_pct', '—')}%")
            lines.append(f"- Sleep Duration: {slp.get('duration_hours', '—')} hrs")
        return "\n".join(lines) if len(lines) > 1 else "No Whoop data available for today."

    return f"Unknown tool: {name}"


# ── MCP event loop ────────────────────────────────────────────────────────────

def main() -> None:
    while True:
        msg = _read()
        if msg is None:
            break

        msg_id = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            _write({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "life-intelligence",
                        "version": "1.0.0",
                        "description": "Personal life intelligence — health, finances, career, legal",
                    },
                },
            })

        elif method == "tools/list":
            _write({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})

        elif method == "tools/call":
            params = msg.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                content = _execute_tool(tool_name, arguments)
                _write({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": content}],
                        "isError": False,
                    },
                })
            except Exception as e:
                logger.error("Tool execution error: %s", e)
                _write({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                        "isError": True,
                    },
                })

        elif method == "notifications/initialized":
            pass  # no response needed

        else:
            if msg_id is not None:
                _write({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                })


if __name__ == "__main__":
    main()
