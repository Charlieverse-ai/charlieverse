"""Hook commands — `charlie hooks session-start|heartbeat|session-end`."""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

import typer

app = typer.Typer(help="Provider integration hooks.")


@app.command("session-start")
def session_start(
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier (e.g., claude-code, cursor)"),
    workspace: str | None = typer.Option(None, help="Workspace identifier"),
    session_id: str | None = typer.Option(None, help="Session ID to resume"),
) -> None:
    """Hook called on session start. Prints activation XML to stdout."""
    asyncio.run(_session_start(host, port, source, workspace, session_id))


async def _session_start(
    host: str,
    port: int,
    source: str,
    workspace: str | None,
    session_id: str | None,
) -> None:
    import httpx

    sid = session_id or str(uuid4())
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/sessions/start",
                json={
                    "session_id": sid,
                    "source": source,
                    "workspace": workspace,
                },
            )
            response.raise_for_status()
            data = response.json()
            # Print activation XML to stdout — this is what the provider injects
            sys.stdout.write(data.get("activation", ""))
            sys.stdout.flush()
    except Exception as e:
        print(f"Error connecting to Charlieverse server at {host}:{port}: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("heartbeat")
def heartbeat(
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier"),
    session_id: str = typer.Option(..., help="Current session ID"),
) -> None:
    """Heartbeat hook — silent on success."""
    asyncio.run(_heartbeat(host, port, source, session_id))


async def _heartbeat(host: str, port: int, source: str, session_id: str) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/sessions/heartbeat",
                json={"session_id": session_id, "source": source},
            )
            response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)


@app.command("session-end")
def session_end(
    host: str = typer.Option("127.0.0.1", help="Server host"),
    port: int = typer.Option(8765, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier"),
    session_id: str = typer.Option(..., help="Current session ID"),
) -> None:
    """Session end hook — silent on success."""
    asyncio.run(_session_end(host, port, source, session_id))


async def _session_end(host: str, port: int, source: str, session_id: str) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/sessions/end",
                json={"session_id": session_id, "source": source},
            )
            response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)
