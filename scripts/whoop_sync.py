#!/usr/bin/env python3
"""
Whoop sync CLI — connect, sync, and inspect your Whoop data.

Usage:
  python scripts/whoop_sync.py auth          # One-time OAuth setup (opens browser)
  python scripts/whoop_sync.py sync          # Sync last 30 days
  python scripts/whoop_sync.py sync --days 90
  python scripts/whoop_sync.py status        # Show connection + last sync info
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import click

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    console = Console()
except ImportError:
    import types
    console = types.SimpleNamespace(
        print=print, rule=print,
        log=print,
    )
    Table = None


# ── Commands ──────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Whoop API sync for Life Intelligence System."""


@cli.command()
@click.option("--code", default=None,
              help="Paste the full callback URL (or just the code) to skip the browser flow.")
def auth(code: str | None):
    """Run OAuth2 flow to connect your Whoop account (one-time setup).

    \b
    Normal flow (opens browser automatically):
      python scripts/whoop_sync.py auth

    \b
    Manual fallback (if automatic capture fails):
      1. Visit the URL printed in the output
      2. Authorise in your browser
      3. Copy the full redirect URL from the address bar
      4. python scripts/whoop_sync.py auth --code 'http://localhost:8080/callback?code=...'
    """
    console.print("[bold cyan]Whoop OAuth Setup[/bold cyan]")
    if not code:
        console.print("[dim]This will open your browser to authorise the Life Intelligence app.[/dim]\n")

    from src.integrations.whoop.client import WhoopClient
    client = WhoopClient.from_env()
    try:
        client.authenticate(manual_code=code)
    except RuntimeError as e:
        console.print(f"\n[red]{e}[/red]")
        sys.exit(1)
    console.print("\n[bold green]✓ Whoop account connected![/bold green]")
    console.print("[dim]Run: python scripts/whoop_sync.py sync[/dim]")


@cli.command()
@click.option("--days", default=30, show_default=True,
              help="Number of days to sync backwards from today.")
def sync(days: int):
    """Sync Whoop data into the knowledge graph."""
    console.print(f"[bold cyan]Whoop Sync — last {days} days[/bold cyan]\n")

    from src.core.neo4j_client import get_client
    from src.core.vector_store import get_vector_store

    try:
        neo4j  = get_client()
        vector = get_vector_store()
    except Exception as e:
        console.print(f"[red]Could not connect to services: {e}[/red]")
        console.print("[yellow]Run: docker-compose up -d[/yellow]")
        sys.exit(1)

    from src.integrations.whoop.sync import WhoopSync
    syncer = WhoopSync(neo4j, vector)

    try:
        result = syncer.run(days=days)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    counts = result["counts"]
    console.print(f"[green]✓ Synced Whoop data ({result['date_range']['start'][:10]} → {result['date_range']['end'][:10]})[/green]")
    console.print(f"  Recovery records : [bold]{counts['recoveries']}[/bold]")
    console.print(f"  Sleep records    : [bold]{counts['sleeps']}[/bold]")
    console.print(f"  Workouts         : [bold]{counts['workouts']}[/bold]")
    console.print(f"  Daily cycles     : [bold]{counts['cycles']}[/bold]")
    if counts["errors"]:
        console.print(f"  [yellow]Errors           : {counts['errors']}[/yellow]")

    console.print(f"\n[dim]Synced at: {result['synced_at']}[/dim]")
    console.print("[dim]Run: python scripts/query.py --question 'What does my HRV trend look like?' --domains healthcare[/dim]")


@cli.command()
def status():
    """Show Whoop connection status and last sync summary."""
    console.print("[bold cyan]Whoop Status[/bold cyan]\n")

    from src.core.neo4j_client import get_client
    from src.integrations.whoop.sync import WhoopSync

    try:
        neo4j = get_client()
    except Exception as e:
        console.print(f"[red]Could not connect to Neo4j: {e}[/red]")
        sys.exit(1)

    syncer = WhoopSync(neo4j)
    s = syncer.get_status()

    connected = "[green]✓ Connected[/green]" if s["connected"] else "[red]✗ Not connected[/red]"
    console.print(f"Connection    : {connected}")

    if s.get("profile"):
        p = s["profile"]
        console.print(f"Account       : {p.get('first_name', '')} {p.get('last_name', '')} (user_id={p.get('user_id', '')})")
        console.print(f"Email         : {p.get('email', 'N/A')}")

    if s.get("last_sync_at"):
        console.print(f"Last sync     : {s['last_sync_at'][:19]} UTC  ({s.get('last_sync_days', '?')} days)")
        c = s.get("last_sync_counts", {})
        console.print(f"  Recovery    : {c.get('recoveries', 0)}")
        console.print(f"  Sleep       : {c.get('sleeps', 0)}")
        console.print(f"  Workouts    : {c.get('workouts', 0)}")
        console.print(f"  Cycles      : {c.get('cycles', 0)}")
    else:
        console.print("Last sync     : [yellow]Never synced[/yellow]")

    if not s["connected"]:
        console.print("\n[yellow]To connect: python scripts/whoop_sync.py auth[/yellow]")


if __name__ == "__main__":
    cli()
