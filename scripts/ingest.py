#!/usr/bin/env python3
"""CLI: ingest any file or folder into any domain/vertical."""

import sys
import os
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from dotenv import load_dotenv

load_dotenv()

ACTIVE_DOMAINS = {"healthcare"}
DOMAIN_VERTICALS = {
    "healthcare": ["medical", "fitness", "mental_health", "genetics"],
}


@click.command()
@click.option("--file", "file_path", default=None, help="Single file to ingest")
@click.option("--folder", "folder_path", default=None, help="Folder to ingest recursively")
@click.option("--domain", required=True, help="Domain: healthcare | finances | legal-contracts | career | relationships")
@click.option("--vertical", default=None, help="Vertical within domain (required for --file)")
def ingest(file_path: str, folder_path: str, domain: str, vertical: str):
    """Ingest personal data files into the Life Intelligence knowledge base."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        console = Console()
    except ImportError:
        print("Install rich: pip install rich")
        sys.exit(1)

    if domain not in ACTIVE_DOMAINS:
        console.print(f"[red]Domain '{domain}' is planned but not yet active.[/red]")
        console.print(f"[yellow]See src/domains/{domain}/PLANNED.md for the roadmap.[/yellow]")
        sys.exit(1)

    if file_path and not vertical:
        console.print("[red]--vertical is required when ingesting a single file.[/red]")
        console.print(f"Available verticals: {DOMAIN_VERTICALS.get(domain, [])}")
        sys.exit(1)

    console.print(Panel(f"[bold green]Life Intelligence Ingestor[/bold green]\nDomain: {domain} | Vertical: {vertical or 'auto-detect'}"))

    from src.core.neo4j_client import get_client
    from src.core.vector_store import get_vector_store

    try:
        neo4j = get_client()
        vector = get_vector_store()
    except Exception as e:
        console.print(f"[red]Failed to connect to services: {e}[/red]")
        console.print("[yellow]Ensure Neo4j and ChromaDB are running: docker-compose up -d[/yellow]")
        sys.exit(1)

    if domain == "healthcare":
        from src.domains.healthcare.domain import HealthcareDomain
        hc = HealthcareDomain(neo4j, vector)
        hc.register()

        results = []
        if file_path:
            console.print(f"[cyan]Ingesting: {file_path}[/cyan]")
            try:
                result = hc.ingest(file_path, vertical)
                results.append(result)
                console.print(f"[green]✓ {file_path.split('/')[-1]}[/green] → {result.get('chunks', 0)} chunks, doc_id={result.get('doc_id', '')}")
            except Exception as e:
                console.print(f"[red]✗ Failed: {e}[/red]")

        elif folder_path:
            files = [p for p in Path(folder_path).rglob("*") if p.is_file() and not p.name.startswith(".")]
            console.print(f"[cyan]Found {len(files)} files in {folder_path}[/cyan]")
            for fp in files:
                # Auto-detect vertical from folder structure
                vert = vertical or _detect_vertical(str(fp))
                if not vert:
                    console.print(f"[yellow]⚠ Could not detect vertical for {fp.name}, skipping[/yellow]")
                    continue
                try:
                    result = hc.ingest(str(fp), vert)
                    results.append(result)
                    console.print(f"[green]✓ {fp.name}[/green] ({vert}) → {result.get('chunks', 0)} chunks")
                except Exception as e:
                    console.print(f"[red]✗ {fp.name}: {e}[/red]")

        # Run linkers
        if results:
            from src.domains.healthcare.cross_vertical_linker import HealthcareCrossVerticalLinker
            from src.core.cross_domain_linker import CrossDomainLinker
            with console.status("[cyan]Running cross-vertical linker...[/cyan]"):
                counts = HealthcareCrossVerticalLinker(neo4j).run_all_links()
                CrossDomainLinker(neo4j).run_all_rules()

            table = Table(title="Ingestion Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Files ingested", str(len(results)))
            table.add_row("Total chunks", str(sum(r.get("chunks", 0) for r in results)))
            table.add_row("Cross-vertical links", str(sum(counts.values())))
            console.print(table)


def _detect_vertical(file_path: str) -> str | None:
    path = file_path.lower()
    if "/medical/" in path or "lab" in path or "prescription" in path:
        return "medical"
    if "/fitness/" in path or "workout" in path or "sleep" in path:
        return "fitness"
    if "/mental_health/" in path or "/mental/" in path or "therapy" in path or "mood" in path:
        return "mental_health"
    if "/genetics/" in path or "dna" in path or "gene" in path or "23andme" in path:
        return "genetics"
    return None


if __name__ == "__main__":
    ingest()
