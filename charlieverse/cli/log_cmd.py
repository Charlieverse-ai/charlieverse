"""Log command — `charlie log`."""

from __future__ import annotations

import asyncio
import json

import typer


def log(
    content: str = typer.Argument(..., help="Logbook entry content"),
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
    tags: str | None = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
) -> None:
    """Record a logbook entry."""
    asyncio.run(_log(content, host, port, session_id, tags))


async def _log(
    content: str, host: str, port: int,
    session_id: str | None, tags: str | None,
) -> None:
    import httpx

    body: dict = {"content": content}
    if session_id:
        body["session_id"] = session_id
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/log",
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            typer.echo(f"Logged: {data.get('id', 'ok')}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
