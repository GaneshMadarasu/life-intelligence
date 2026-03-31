#!/usr/bin/env python3
"""AES-256 encrypted backup and restore for all personal data."""

import sys
import os
import tarfile
import io
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from dotenv import load_dotenv

load_dotenv()


def _get_fernet():
    from cryptography.fernet import Fernet
    key = os.getenv("BACKUP_ENCRYPTION_KEY", "").encode()
    if not key:
        raise ValueError(
            "BACKUP_ENCRYPTION_KEY not set in .env. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key)


@click.group()
def cli():
    """Life Intelligence System — encrypted backup and restore."""
    pass


@cli.command()
@click.option("--output-dir", default=None, help="Output directory (default: BACKUP_DIR from .env)")
@click.option("--include-neo4j", is_flag=True, default=False, help="Include Neo4j data directory")
def backup(output_dir: str, include_neo4j: bool):
    """Create AES-256 encrypted backup of all personal data."""
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        import types
        console = types.SimpleNamespace(print=print, status=lambda x: __import__('contextlib').nullcontext())

    backup_dir = Path(output_dir or os.getenv("BACKUP_DIR", "./data/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"life-intel-backup-{timestamp}.enc"

    project_root = Path(__file__).parent.parent
    dirs_to_backup = ["data/uploads", "data/chroma_db"]
    if include_neo4j:
        dirs_to_backup.append("data/neo4j")

    console.print(f"[cyan]Creating encrypted backup → {backup_file}[/cyan]")

    # Create in-memory tar archive
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
        for dir_name in dirs_to_backup:
            dir_path = project_root / dir_name
            if dir_path.exists():
                tar.add(str(dir_path), arcname=dir_name)
                console.print(f"  [green]✓[/green] Added {dir_name}/")
            else:
                console.print(f"  [yellow]⚠[/yellow] Skipped {dir_name}/ (not found)")

    tar_bytes = tar_buffer.getvalue()

    # Encrypt
    fernet = _get_fernet()
    encrypted = fernet.encrypt(tar_bytes)

    backup_file.write_bytes(encrypted)
    size_mb = len(encrypted) / 1024 / 1024
    console.print(f"[bold green]✓ Backup complete: {backup_file} ({size_mb:.1f} MB)[/bold green]")


@cli.command()
@click.argument("backup_file")
@click.option("--output-dir", default=".", help="Directory to restore into")
def restore(backup_file: str, output_dir: str):
    """Decrypt and restore a backup."""
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        import types
        console = types.SimpleNamespace(print=print)

    backup_path = Path(backup_file)
    if not backup_path.exists():
        console.print(f"[red]Backup file not found: {backup_file}[/red]")
        sys.exit(1)

    console.print(f"[cyan]Restoring from: {backup_file}[/cyan]")

    fernet = _get_fernet()
    encrypted = backup_path.read_bytes()
    tar_bytes = fernet.decrypt(encrypted)

    tar_buffer = io.BytesIO(tar_bytes)
    with tarfile.open(fileobj=tar_buffer, mode="r:gz") as tar:
        tar.extractall(output_dir)

    console.print(f"[bold green]✓ Restore complete → {output_dir}[/bold green]")


if __name__ == "__main__":
    cli()
