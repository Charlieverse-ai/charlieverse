"""Init command — `charlie init`."""

from __future__ import annotations

import shutil
import subprocess
from charlieverse.config import config
from pathlib import Path

import typer


def init(
    path: str = typer.Option(
        str(config.path),
        help="Root directory for Charlieverse data",
    ),
) -> None:
    """Initialize Charlieverse — creates directory structure, builds web UI, and verifies dependencies."""
    root = Path(path)
    repo_dir = Path(__file__).resolve().parent.parent.parent

    # ── Directory structure ──────────────────────────────────
    root.mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(exist_ok=True)

    # ── User hook directories ─────────────────────────────────
    hooks_dir = root / "hooks"
    hook_events = ["session-start", "prompt-submit", "stop", "save-reminder"]
    for event in hook_events:
        event_dir = hooks_dir / event
        event_dir.mkdir(parents=True, exist_ok=True)
        readme = event_dir / "README"
        if not readme.exists():
            readme.write_text(
                f"# Drop executable scripts here to run on {event} hook events.\n"
                f"# Scripts get CHARLIE_SESSION_ID and other context as env vars.\n"
                f"# stdout is injected into Charlie's context. 5s timeout.\n"
            )
    typer.echo(f"✔ Hook directories at {hooks_dir}")

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
