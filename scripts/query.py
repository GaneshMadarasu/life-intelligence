#!/usr/bin/env python3
"""CLI: ask anything across all active domains."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from dotenv import load_dotenv

load_dotenv()


@click.command()
@click.option("--question", required=True, help="Your question")
@click.option("--domains", default="all", help="Comma-separated domains, or 'all'")
@click.option("--date-from", default=None, help="Filter from date (YYYY-MM-DD)")
@click.option("--date-to", default=None, help="Filter to date (YYYY-MM-DD)")
@click.option("--top-k", default=5, type=int, help="Number of results to retrieve")
def query(question: str, domains: str, date_from: str, date_to: str, top_k: int):
    """Ask your personal life intelligence system a question."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        console = Console()
    except ImportError:
        print("Install rich: pip install rich")
        sys.exit(1)

    domain_list = [d.strip() for d in domains.split(",")]

    console.print(Panel(f"[bold blue]Life Intelligence Query[/bold blue]\n{question}"))

    from src.core.neo4j_client import get_client
    from src.core.vector_store import get_vector_store
    from src.retrieval.hybrid_retriever import HybridRetriever
    from src.generation.answer_generator import AnswerGenerator
    from src.core.safety_checker import SafetyChecker
    from src.core.cross_domain_linker import CrossDomainLinker

    try:
        neo4j = get_client()
        vector = get_vector_store()
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")
        console.print("[yellow]Ensure Neo4j and ChromaDB are running: docker-compose up -d[/yellow]")
        sys.exit(1)

    with console.status("[cyan]Retrieving relevant context...[/cyan]"):
        retrieval = HybridRetriever(neo4j, vector).retrieve(
            question=question,
            domains=domain_list,
            date_from=date_from,
            date_to=date_to,
            top_k=top_k,
        )

    with console.status("[cyan]Running safety checks...[/cyan]"):
        try:
            warnings = SafetyChecker(neo4j).run_full_check()
            cross_insights = CrossDomainLinker(neo4j).get_cross_domain_insights()
        except Exception:
            warnings = {}
            cross_insights = []

    with console.status("[cyan]Generating answer...[/cyan]"):
        result = AnswerGenerator().generate(
            question=question,
            context=retrieval["total_context"],
            domains=domain_list,
            cross_domain_insights=cross_insights,
            warnings=warnings,
        )

    # Print answer
    console.print("\n")
    console.print(Panel(Markdown(result["answer"]), title="[bold green]Answer[/bold green]", border_style="green"))

    # Warnings
    high_warnings = [w for w in result.get("warnings", []) if w.get("severity") == "high"]
    if high_warnings:
        console.print("\n[bold red]⚠ SAFETY WARNINGS[/bold red]")
        for w in high_warnings:
            console.print(f"  [red]● {w['message']}[/red]")

    # Cross-domain insights
    insights = result.get("cross_domain_insights", [])
    if insights:
        console.print(f"\n[bold yellow]Cross-domain insights: {len(insights)} connections found[/bold yellow]")

    # Sources
    sources = result.get("sources", [])
    if sources:
        console.print(f"\n[dim]Sources: {', '.join(sources[:3])}[/dim]")

    console.print(f"\n[dim]Confidence: {result.get('confidence', 'unknown')} | "
                  f"Graph results: {len(retrieval['graph_results'])} | "
                  f"Vector results: {len(retrieval['vector_results'])}[/dim]")


if __name__ == "__main__":
    query()
