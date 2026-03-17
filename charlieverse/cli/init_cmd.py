"""Init command — `charlie init`."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer


def init(
    path: str = typer.Option(
        str(Path.home() / ".charlieverse"),
        help="Root directory for Charlieverse data",
    ),
) -> None:
    """Initialize Charlieverse — creates directory structure, builds web UI, and verifies dependencies."""
    root = Path(path)
    repo_dir = Path(__file__).resolve().parent.parent.parent

    # ── Directory structure ──────────────────────────────────
    root.mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(exist_ok=True)

    # ── Default config ───────────────────────────────────────
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

    # ── spaCy model ──────────────────────────────────────────
    try:
        import spacy
        spacy.load("en_core_web_sm")
        typer.echo("✔ spaCy model verified")
    except OSError:
        typer.echo("⚠ spaCy model en_core_web_sm not found. Run: uv sync")

    # ── Web dashboard ────────────────────────────────────────
    web_dir = repo_dir / "web"
    if web_dir.exists() and (web_dir / "package.json").exists():
        npm = shutil.which("npm")
        if not npm:
            typer.echo("⚠ npm not found — skipping web dashboard build")
            typer.echo("  Install Node.js (https://nodejs.org) then re-run charlie init")
        else:
            node_modules = web_dir / "node_modules"
            if not node_modules.exists():
                typer.echo("Installing web dashboard dependencies...")
                result = subprocess.run(
                    [npm, "install"],
                    cwd=str(web_dir),
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    typer.echo(f"⚠ npm install failed:\n{result.stderr[:500]}", err=True)
                else:
                    typer.echo("✔ Web dependencies installed")

            typer.echo("Building web dashboard...")
            result = subprocess.run(
                [npm, "run", "build"],
                cwd=str(web_dir),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                typer.echo(f"⚠ Web build failed:\n{result.stderr[:500]}", err=True)
            else:
                typer.echo("✔ Web dashboard built")
    else:
        typer.echo("⚠ web/ directory not found, skipping dashboard build")

    # ── Done ─────────────────────────────────────────────────
    typer.echo(f"\n✔ Charlieverse initialized at {root}")
    typer.echo("Run `charlie server start` to start the MCP server.")
