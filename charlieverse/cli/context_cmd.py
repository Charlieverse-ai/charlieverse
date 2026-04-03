"""CLI command to preview the activation context."""

from __future__ import annotations

import asyncio
import os
import tempfile

import typer

from charlieverse.config import config

DEFAULT_HOST = config.server.ip_address()
DEFAULT_PORT = config.server.port


def context(
    session_id: str | None = typer.Option(None, "--session", "-s", help="Session ID"),
    workspace: str | None = typer.Option(None, "--workspace", "-w", help="Workspace path"),
    save_to_file: bool = typer.Option(False, "--save", "-S", help="Save to a temporary file"),
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
) -> None:
    """Print the activation context (what Charlie sees on startup)."""
    asyncio.run(_context(session_id, workspace, host, port, save_to_file))


async def _context(
    session_id: str | None, workspace: str | None,
    host: str, port: int,
    save: bool
) -> None:
    import httpx

    params: dict[str, str] = {}
    if session_id:
        params["session_id"] = session_id
    if workspace:
        params["workspace"] = workspace
    else:
        params["workspace"] = os.getcwd()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                config.server.api_url("sessions/context"),
                params=params,
            )
            resp.raise_for_status()

            if save:
                with tempfile.NamedTemporaryFile(mode="w+t", delete=False) as tmpfile:
                    tmpfile.write(resp.text)
                    tmpfile.close()
                    typer.echo(tmpfile.name)
            else:
                typer.echo(resp.text)

    except httpx.ConnectError:
        typer.echo(f"Can't reach server at {host}:{port}. Is it running?", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
