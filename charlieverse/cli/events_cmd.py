"""Events command — `charlie events`."""

from __future__ import annotations

import asyncio
import json

import typer

from charlieverse.config import config

DEFAULT_HOST = config.server.ip_address()
DEFAULT_PORT = config.server.port


def events(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    session_id: str | None = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    since: str | None = typer.Option(None, help="Events since (ISO datetime)"),
    limit: int = typer.Option(50, "-n", help="Max events to return"),
    event_type: str | None = typer.Option(None, "--type", "-t", help="Filter by event type"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Show full metadata/input"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List recent hook events from the server."""
    asyncio.run(_events(host, port, session_id, since, limit, event_type, verbose, json_output))


async def _events(
    host: str,
    port: int,
    session_id: str | None,
    since: str | None,
    limit: int,
    event_type: str | None,
    verbose: bool,
    json_output: bool,
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

    events_list = data.get("events", [])

    if event_type:
        events_list = [e for e in events_list if e.get("event_type") == event_type]

    if not events_list:
        typer.echo("No events found.")
        return

    if json_output:
        typer.echo(json.dumps(events_list, indent=2))
        return

    for event in reversed(events_list):
        ts = event.get("created_at", "")[:19].replace("T", " ")
        etype = event.get("event_type", "?")
        tool = event.get("tool_name", "")
        content = event.get("content") or ""
        metadata_raw = event.get("metadata")
        metadata = {}
        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
            except (json.JSONDecodeError, TypeError):
                pass

        # Format line
        if etype == "tool_use":
            tool_input = metadata.get("input", {})
            if verbose:
                # Show full tool input
                if isinstance(tool_input, dict):
                    input_summary = _summarize_input(tool, tool_input)
                else:
                    input_summary = str(tool_input)[:200]
                line = f"  {ts}  🔧 {tool}\n      {input_summary}"
            else:
                input_brief = _brief_input(tool, metadata.get("input", {}))
                line = f"  {ts}  🔧 {tool}  {input_brief}"
        elif etype == "stop":
            line = f"  {ts}  ⏹  {content[:120]}"
        elif etype == "session_start":
            line = f"  {ts}  🟢 {content}"
        elif etype == "session_end":
            line = f"  {ts}  🔴 {content}"
        else:
            line = f"  {ts}  ·  [{etype}] {content[:100]}"

        typer.echo(line)

    typer.echo(f"\n  {len(events_list)} events")


def _brief_input(tool: str, tool_input: dict) -> str:
    """One-line summary of tool input."""
    if not isinstance(tool_input, dict):
        return ""

    if tool in ("Edit", "Write"):
        path = tool_input.get("file_path", "")
        return f"→ {path}" if path else ""
    elif tool == "Read":
        path = tool_input.get("file_path", "")
        return f"→ {path}" if path else ""
    elif tool == "Bash":
        cmd = tool_input.get("command", "")
        return f"$ {cmd[:80]}" if cmd else ""
    elif tool == "Glob":
        pattern = tool_input.get("pattern", "")
        return f"→ {pattern}" if pattern else ""
    elif tool == "Grep":
        pattern = tool_input.get("pattern", "")
        return f"/{pattern}/" if pattern else ""
    elif tool == "Agent":
        desc = tool_input.get("description", "")
        agent = tool_input.get("subagent_type", "")
        return f"→ {agent}: {desc}" if agent else desc
    elif tool.startswith("mcp__"):
        # MCP tool — show key params
        short = tool.split("__")[-1]
        params = {k: str(v)[:50] for k, v in tool_input.items() if v and k != "ctx"}
        return f"({short}) {params}" if params else f"({short})"
    else:
        return ""


def _summarize_input(tool: str, tool_input: dict) -> str:
    """Verbose multi-line summary of tool input."""
    if not isinstance(tool_input, dict):
        return str(tool_input)[:300]

    lines = []
    for k, v in tool_input.items():
        val = str(v)
        if len(val) > 200:
            val = val[:200] + "..."
        lines.append(f"    {k}: {val}")
    return "\n".join(lines) if lines else "(no input)"
