"""CLI command to extract and import conversation history.

Wraps tools/extract_conversations.py as `charlie import`.
Auto-discovers Claude, Copilot, and Codex session files, extracts
messages, and writes a combined JSONL file for the Storyteller.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer

from charlieverse.config import config

DEFAULT_OUTPUT = Path.home() / ".charlieverse" / "import" / "conversations.jsonl"
DEFAULT_HOST = config.server.host
DEFAULT_PORT = config.server.port


def import_conversations(
    output: Path = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Output JSONL file path"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Filter to specific provider (claude, copilot, codex)"),
    extra_dirs: list[str] = typer.Option([], "--dir", "-d", help="Extra directories to scan"),
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    skip_existing: bool = typer.Option(True, help="Skip sessions that already have stories"),
) -> None:
    """Extract conversation history from AI providers into JSONL."""
    asyncio.run(_import(output, provider, extra_dirs, host, port, skip_existing))


async def _import(
    output: Path,
    provider: str | None,
    extra_dirs: list[str],
    host: str,
    port: int,
    skip_existing: bool,
) -> None:
    # Import the extraction module from tools/
    tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
    sys.path.insert(0, str(tools_dir))

    try:
        from extract_conversations import (
            _discover_providers,
            PROVIDER_PROCESSORS,
        )
    except ImportError:
        typer.echo("Can't find tools/extract_conversations.py", err=True)
        raise typer.Exit(1)

    extra_paths = [Path(d) for d in extra_dirs]
    providers = _discover_providers(extra_paths)

    if provider:
        providers = [(name, path) for name, path in providers if name == provider]

    if not providers:
        typer.echo("No provider data found.", err=True)
        raise typer.Exit(1)

    # Ensure output directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Discovered: {', '.join(f'{name} ({path})' for name, path in providers)}")

    total_entries = 0
    total_sessions = 0
    provider_stats: dict[str, dict] = {}

    with open(output, "w") as out:
        for provider_name, provider_dir in providers:
            finder, processor = PROVIDER_PROCESSORS.get(provider_name, (None, None))
            if not finder or not processor:
                continue

            typer.echo(f"\n[{provider_name}] Scanning {provider_dir}")
            jsonl_files = finder(provider_dir)
            typer.echo(f"[{provider_name}] Found {len(jsonl_files)} files")

            p_entries = 0
            p_sessions = 0

            for i, jsonl_path in enumerate(jsonl_files):
                entries = processor(jsonl_path)
                if entries:
                    p_sessions += 1
                    for entry in entries:
                        out.write(json.dumps(entry) + "\n")
                        p_entries += 1

                if (i + 1) % 100 == 0:
                    typer.echo(f"[{provider_name}]   {i + 1}/{len(jsonl_files)} files...")

            typer.echo(f"[{provider_name}] {p_sessions} sessions, {p_entries} entries")
            provider_stats[provider_name] = {"sessions": p_sessions, "entries": p_entries}
            total_entries += p_entries
            total_sessions += p_sessions

    # Output summary as JSON to stdout for skill consumption
    summary = {
        "output_file": str(output),
        "total_sessions": total_sessions,
        "total_entries": total_entries,
        "providers": provider_stats,
    }

    typer.echo(f"\nDone. {total_sessions} sessions, {total_entries} entries → {output}")
    typer.echo(f"\n<import_summary>{json.dumps(summary)}</import_summary>")
