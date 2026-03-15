"""Events command — `charlie events`."""

from __future__ import annotations

import asyncio
import json

import typer


def events(
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    since: str | None = typer.Option(None, help="Events since (ISO datetime)"),
    limit: int = typer.Option(50, "-n", help="Max events to return"),
    event_type: str | None = typer.Option(None, "--type", "-t", help="Filter by event type (tool_use, stop, session_start)"),
) -> None:
    """List recent hook events from the server."""
    asyncio.run(_events(host, port, session_id, since, limit, event_type))


async def _events(
    host: str, port: int,
    session_id: str | None, since: str | None,
    limit: int, event_type: str | None,
) -> None:
    import httpx

    body: dict = {"limit": limit}
    if session_id:
        body["session_id"] = session_id
    if since:
        body["since"] = since

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/hooks/events",
                json=body,
            )
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    events = data.get("events", [])

    # Filter by type if specified
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    if not events:
        typer.echo("No events found.")
        return

    for event in reversed(events):  # Show oldest first
        ts = event.get("created_at", "")[:19].replace("T", " ")
        etype = event.get("event_type", "?")
        tool = event.get("tool_name", "")
        content = (event.get("content") or "")[:80]

        # Color by type
        if etype == "tool_use":
            line = f"  {ts}  🔧 {tool}"
        elif etype == "stop":
            line = f"  {ts}  ⏹  {content}"
        elif etype == "session_start":
            line = f"  {ts}  🟢 {content}"
        elif etype == "session_end":
            line = f"  {ts}  🔴 {content}"
        else:
            line = f"  {ts}  ·  [{etype}] {content}"

        typer.echo(line)

    typer.echo(f"\n  {len(events)} events")
