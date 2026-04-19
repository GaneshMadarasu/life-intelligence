#!/usr/bin/env python
"""CLI for Gmail sync — reads domain-relevant emails into the knowledge graph.

Usage:
    python scripts/gmail_sync.py auth
    python scripts/gmail_sync.py auth-complete --code YOUR_CODE
    python scripts/gmail_sync.py sync [--days 90] [--domain healthcare]
    python scripts/gmail_sync.py search --query "lab results"
    python scripts/gmail_sync.py emails [--domain healthcare] [--days 30]
    python scripts/gmail_sync.py status
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


def _get_syncer(with_claude: bool = False):
    from src.core.neo4j_client import get_client
    from src.integrations.gmail.sync import GmailSync
    anthropic_client = None
    if with_claude:
        try:
            import anthropic, os
            anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            pass
    return GmailSync(get_client(), anthropic_client)


@click.group()
def cli():
    """Gmail → Life Intelligence sync."""


@cli.command()
def auth():
    """Start OAuth2 browser flow to connect Gmail."""
    syncer = _get_syncer()
    url = syncer.authenticate()
    console.print(f"\n[bold cyan]Open this URL in your browser:[/]\n{url}\n")
    console.print("[dim]After authorizing, copy the 'code' parameter from the redirect URL and run:[/]")
    console.print("[bold]  python scripts/gmail_sync.py auth-complete --code 'YOUR_CODE'[/]\n")


@cli.command("auth-complete")
@click.option("--code", required=True, help="Authorization code from OAuth2 redirect URL")
def auth_complete(code: str):
    """Complete OAuth2 with the authorization code."""
    syncer = _get_syncer()
    result = syncer.complete_auth(code)
    console.print("[bold green]Gmail connected![/]")
    console.print(f"Scopes: {', '.join(result.get('scopes', []))}")


@cli.command()
@click.option("--days", default=90, help="How many days back to sync")
@click.option(
    "--domain",
    default=None,
    type=click.Choice(["healthcare", "finances", "career"]),
    help="Sync only a specific domain (default: all)",
)
@click.option("--extract/--no-extract", default=True, help="Use Claude to extract entities (requires ANTHROPIC_API_KEY)")
def sync(days: int, domain: str | None, extract: bool):
    """Sync domain-relevant emails into the knowledge graph."""
    syncer = _get_syncer(with_claude=extract)
    domains = [domain] if domain else None
    console.print(
        f"Syncing Gmail (last [bold]{days}[/] days"
        + (f", domain=[bold]{domain}[/]" if domain else ", all domains")
        + f", entity extraction=[bold]{'on' if extract else 'off'}[/])…"
    )
    result = syncer.run(days_back=days, domains=domains, extract_entities=extract)
    console.print(f"\n[bold green]Done![/]")
    console.print(f"  Total ingested: [bold]{result['total_ingested']}[/]")
    for d, count in result.get("by_domain", {}).items():
        color = {"healthcare": "green", "finances": "blue", "career": "yellow"}.get(d, "white")
        console.print(f"  [{color}]{d}[/]: {count} emails")


@cli.command()
@click.option("--query", required=True, help="Gmail search query (same syntax as Gmail search bar)")
@click.option("--domain", default="general", help="Domain to tag these emails with")
def search(query: str, domain: str):
    """Ad-hoc Gmail search — ingest any emails matching a Gmail query."""
    syncer = _get_syncer(with_claude=True)
    console.print(f"Searching Gmail: [bold]{query}[/]…")
    result = syncer.search_and_ingest(query, domain=domain)
    console.print(f"[bold green]Ingested {result['ingested']} emails[/]")


@cli.command()
@click.option(
    "--domain",
    default=None,
    type=click.Choice(["healthcare", "finances", "career", "general"]),
    help="Filter by domain",
)
@click.option("--days", default=None, type=int, help="Only show emails from last N days")
@click.option("--limit", default=30, help="Max emails to show")
def emails(domain: str | None, days: int | None, limit: int):
    """Show ingested emails from the knowledge graph."""
    syncer = _get_syncer()
    rows = syncer.get_emails(domain=domain, limit=limit, days_back=days)
    if not rows:
        console.print("[dim]No emails found. Run sync first.[/]")
        return
    table = Table(
        title=f"Emails{' — ' + domain if domain else ''}",
        show_header=True,
        show_lines=False,
    )
    table.add_column("Date", style="dim", width=11)
    table.add_column("Domain", width=12)
    table.add_column("Subject", no_wrap=False)
    table.add_column("From", width=30)
    for row in rows:
        d = row.get("domain", "general")
        color = {"healthcare": "green", "finances": "blue", "career": "yellow"}.get(d, "white")
        table.add_row(
            row.get("date", ""),
            f"[{color}]{d}[/]",
            row.get("subject", "")[:80],
            row.get("sender", "")[:35],
        )
    console.print(table)


@cli.command()
def status():
    """Check Gmail connection status and ingestion counts."""
    syncer = _get_syncer()
    s = syncer.get_status()
    if s.get("authenticated"):
        console.print("[bold green]Connected[/]")
        console.print(f"Total emails in graph: [bold]{s.get('total_emails', 0)}[/]")
        counts = s.get("email_counts", {})
        if counts:
            for domain, count in counts.items():
                color = {"healthcare": "green", "finances": "blue", "career": "yellow"}.get(domain, "white")
                console.print(f"  [{color}]{domain}[/]: {count}")
    else:
        console.print("[bold red]Not connected[/]")
        console.print(s.get("message", "Run: python scripts/gmail_sync.py auth"))


if __name__ == "__main__":
    cli()
