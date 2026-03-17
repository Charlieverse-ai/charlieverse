"""Init command — `charlie init`."""

from __future__ import annotations

from pathlib import Path

import typer


def init(
    path: str = typer.Option(
        str(Path.home() / ".charlieverse"),
        help="Root directory for Charlieverse data",
    ),
) -> None:
    """Initialize Charlieverse — creates directory structure and default config."""
    root = Path(path)

    # Create directory structure
    root.mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(exist_ok=True)

    # Create default config if it doesn't exist
    config_path = root / "config.json"
    if not config_path.exists():
        import json

        config = {
            "host": "127.0.0.1",
            "port": 8765,
        }
        config_path.write_text(json.dumps(config, indent=2))
        typer.echo(f"Created config at {config_path}")
    else:
        typer.echo(f"Config already exists at {config_path}")

    # Download spaCy model for NER-based memory injection
    try:
        import spacy
        spacy.load("en_core_web_sm")
        typer.echo("spaCy model already installed.")
    except OSError:
        typer.echo("Downloading spaCy language model...")
        import subprocess
        subprocess.run(
            ["python", "-m", "spacy", "download", "en_core_web_sm"],
            check=True,
        )

    typer.echo(f"Charlieverse initialized at {root}")
    typer.echo("Run `charlie server start` to start the MCP server.")
