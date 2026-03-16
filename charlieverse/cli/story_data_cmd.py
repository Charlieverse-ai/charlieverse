"""Story data command — `charlie story-data`.

Fetches session or tier data from the server and outputs JSON to stdout.
Used by the /session-save skill's dynamic context injection.
"""

from __future__ import annotations

import asyncio
import json

import typer


def story_data(
    target: str = typer.Argument(help="Session ID or tier name (daily, weekly, monthly, quarterly, yearly)"),
    date: str | None = typer.Argument(None, help="Date for tier rollups (ISO format, e.g. 2026-03-16)"),
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
) -> None:
    """Fetch story data from the server. Outputs JSON to stdout for skill injection."""
    asyncio.run(_story_data(target, date, host, port))


async def _story_data(target: str, date: str | None, host: str, port: int) -> None:
    import httpx

    tier_names = {"daily", "weekly", "monthly", "quarterly", "yearly"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if target in tier_names:
                if not date:
                    typer.echo("Date required for tier rollups (e.g. charlie story-data weekly 2026-03-16)", err=True)
                    raise typer.Exit(1)
                response = await client.get(f"http://{host}:{port}/api/story-data/{target}/{date}")
            else:
                # Assume it's a session ID
                response = await client.get(f"http://{host}:{port}/api/story-data/{target}")

            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        typer.echo(f"Error fetching story data: {e}", err=True)
        raise typer.Exit(1)

    # Output JSON to stdout for skill consumption
    typer.echo(json.dumps(data, indent=2))
