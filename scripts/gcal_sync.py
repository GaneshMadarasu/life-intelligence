#!/usr/bin/env python
"""CLI for Google Calendar sync.

Usage:
    python scripts/gcal_sync.py auth       # Start OAuth2 flow
    python scripts/gcal_sync.py sync       # Sync next 90 days + last 30 days
    python scripts/gcal_sync.py upcoming   # Show upcoming events
    python scripts/gcal_sync.py status     # Check connection status
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()


def _get_syncer():
    from src.core.neo4j_client import get_client
    from src.integrations.google_calendar.sync import GoogleCalendarSync
    return GoogleCalendarSync(get_client())


@click.group()
def cli():
    """Google Calendar → Life Intelligence sync."""


@cli.command()
def auth():
    """Start OAuth2 browser flow to connect Google Calendar."""
    syncer = _get_syncer()
    url = syncer.authenticate()
    console.print(f"\n[bold cyan]Open this URL in your browser:[/]\n{url}\n")
    console.print("[dim]After authorizing, copy the 'code' parameter from the redirect URL and run:[/]")
    console.print("[bold]  python scripts/gcal_sync.py auth-complete --code 'YOUR_CODE'[/]\n")


@cli.command("auth-complete")
@click.option("--code", required=True, help="Authorization code from OAuth2 redirect URL")
def auth_complete(code: str):
    """Complete OAuth2 with the authorization code."""
    syncer = _get_syncer()
    result = syncer.complete_auth(code)
    console.print("[bold green]Google Calendar connected![/]")
    console.print(f"Scopes: {', '.join(result.get('scopes', []))}")


@cli.command()
@click.option("--days-ahead", default=90, help="Days into the future to sync")
@click.option("--days-back", default=30, help="Days into the past to sync")
def sync(days_ahead: int, days_back: int):
    """Sync calendar events into the knowledge graph."""
    syncer = _get_syncer()
    console.print(f"Syncing Google Calendar (last {days_back} days + next {days_ahead} days)…")
    result = syncer.run(days_ahead=days_ahead, days_back=days_back)
    console.print(f"[bold green]Done! Ingested {result['ingested']} events from {len(result['calendars'])} calendar(s)[/]")


@cli.command()
@click.option("--days", default=14, help="Days ahead to look")
def upcoming(days: int):
    """Show upcoming calendar events."""
    syncer = _get_syncer()
    events = syncer.get_upcoming_events(days=days)
    if not events:
        console.print("[dim]No upcoming events found. Run sync first.[/]")
        return
    table = Table(title=f"Upcoming {days} Days", show_header=True)
    table.add_column("Date")
    table.add_column("Title")
    table.add_column("Domain")
    table.add_column("Location")
    for e in events:
        domain_color = {"healthcare": "green", "finances": "blue", "career": "yellow"}.get(e.get("domain", ""), "white")
        table.add_row(
            e.get("date", ""),
            e.get("title", ""),
            f"[{domain_color}]{e.get('domain', 'general')}[/]",
            e.get("location", ""),
        )
    console.print(table)


@cli.command()
def status():
    """Check Google Calendar connection status."""
    syncer = _get_syncer()
    s = syncer.get_status()
    if s.get("authenticated"):
        console.print("[bold green]Connected[/]")
        console.print(f"Calendars: {', '.join(s.get('calendars', []))}")
    else:
        console.print("[bold red]Not connected[/]")
        console.print("Run: python scripts/gcal_sync.py auth")


if __name__ == "__main__":
    cli()
