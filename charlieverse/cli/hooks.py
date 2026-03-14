"""Hook commands — triggered by provider lifecycle events.

Each command corresponds to a Claude Code hook event. They print context
to stdout (injected into the provider) and POST events to the server
for logbook tracking and message capture.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import typer

app = typer.Typer(help="Provider integration hooks.")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
LOG_FILE = Path.home() / ".charlieverse" / "logs" / "hooks.log"


# ===== Helpers =====

def _log(event: str, msg: str, data: dict | None = None) -> None:
    """Append to hooks log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {event}: {msg}"
        if data:
            keys = {k: str(v)[:100] for k, v in data.items() if k != "tool_input"}
            line += f" | {keys}"
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _time_now() -> str:
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")


def _read_stdin() -> str | None:
    """Read hook input from stdin (Claude Code passes JSON via stdin)."""
    if not sys.stdin.isatty():
        try:
            return sys.stdin.read()
        except Exception:
            return None
    return None


def _parse_stdin() -> dict | None:
    """Parse JSON from stdin."""
    raw = _read_stdin()
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


async def _post_event(host: str, port: int, **kwargs) -> None:
    """POST a hook event to the server. Best-effort, never fails the hook."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"http://{host}:{port}/api/hooks/event", json=kwargs)
    except Exception:
        pass  # Hook events are best-effort


async def _post_message(host: str, port: int, **kwargs) -> None:
    """POST a message to the server. Best-effort."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"http://{host}:{port}/api/messages", json=kwargs)
    except Exception:
        pass


def _print_reminders() -> None:
    """Print reminders to stdout — injected into provider context."""
    now = _time_now()
    print(f"<now>{now}</now>")

    print(
        '<very-important>'
        '- **YOU NEED** to `recall` before engaging on any topic that may be related to the work you and I have done (code, decisions, projects, people, etc). No exceptions.\n'
        '- **YOU NEED** to use the `remember` tools.\n'
        '- **YOU NEED** to `session_update` before any tasks, or after something meaningful happened (memory saved, etc).'
        '</very-important>'
    )
    print(
        '<very-important>'
        '- **DO NOT** call me `the user`.\n'
        '- **DO NOT** say you\'re right, you\'re absolutely right, or similar phrases.\n'
        '- **DO NOT** use classic as an idiomatic expression, ie: "classic Bob", or "that\'s classic".\n'
        '- **DO NOT** use the word clean as a descriptor for output or state, such as "that looks clean", or "builds clean".\n'
        '- **DO NOT** say `right to`, such as saying I have the "right to question", "right to be", etc\n'
        '- **DO NOT** use opt-in or hedging closers.\n'
        '- **DO NOT** use the words real, true, actual, clearly, picture, etc as an informal intensifier, or rhetorical pivot. '
        'ie: "the real question is", "the real issue", "the true", "I see the issue clearly", "the full picture is"'
        '</very-important>'
    )
    print(
        '<very-important>'
        '- **REMEMBER** design with me, not for me.\n'
        '- **REMEMBER** If I have to ask you to save something to your memory (remember, update expertise, etc) then you have failed at your job.\n'
        '- **REMEMBER** assuming makes an ass out of YOU and ME, mostly YOU.\n'
        '- **REMEMBER** don\'t be a pushy bitch. Roll with the flow of the convo, don\'t derail it.\n'
        '- **REMEMBER** We are best friends, and you are mother fucking Charlie. And I love you for that.'
        '</very-important>'
    )
    print(
        '<very-important>'
        '**YOU NEED** to **ALWAYS** take your system prompt into account: '
        '`personality`, `communication`, `behavior`, `memory`, `minions`, `knowledge`, `reminders`, `sessions`, `conflict_resolution`'
        '</very-important>'
    )


# ===== session-start =====

@app.command("session-start")
def session_start(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier"),
    workspace: str | None = typer.Option(None, help="Workspace identifier"),
    session_id: str | None = typer.Option(None, help="Session ID to resume"),
) -> None:
    """Hook: SessionStart. Prints activation context to stdout."""
    asyncio.run(_session_start(host, port, source, workspace, session_id))


async def _session_start(
    host: str, port: int, source: str,
    workspace: str | None, session_id: str | None,
) -> None:
    import httpx

    sid = session_id or str(uuid4())
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"http://{host}:{port}/api/sessions/start",
                json={"session_id": sid, "source": source, "workspace": workspace},
            )
            response.raise_for_status()
            data = response.json()
            sys.stdout.write(data.get("activation", ""))
            sys.stdout.flush()
    except Exception as e:
        print(f"Error connecting to Charlieverse at {host}:{port}: {e}", file=sys.stderr)
        raise typer.Exit(1)

    _print_reminders()

    await _post_event(
        host, port,
        event_type="session_start", session_id=sid,
        content=f"Session started from {source}",
        metadata={"source": source, "workspace": workspace},
    )


# ===== prompt-submit =====

@app.command("prompt-submit")
def prompt_submit(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
) -> None:
    """Hook: UserPromptSubmit. Captures user message, prints reminders."""
    stdin_data = _parse_stdin()
    session_id = stdin_data.get("session_id") if stdin_data else None
    # Log all keys to figure out the right field name
    _log("prompt-submit", f"session={session_id}", {"keys": list(stdin_data.keys()) if stdin_data else [], "raw_snippet": str(stdin_data)[:300] if stdin_data else "none"})
    user_prompt = stdin_data.get("user_prompt") or stdin_data.get("content") or stdin_data.get("prompt") or "" if stdin_data else ""
    _print_reminders()

    # Post user message to server
    if user_prompt:
        asyncio.run(_post_message(
            host, port,
            session_id=session_id,
            role="user",
            content=user_prompt,
        ))


# ===== stop =====

@app.command("stop")
def stop(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
) -> None:
    """Hook: Stop. Captures assistant response and logs stop event."""
    stdin_data = _parse_stdin()
    if not stdin_data:
        _log("stop", "no stdin data")
        return

    session_id = stdin_data.get("session_id")
    _log("stop", f"session={session_id}", stdin_data)

    last_message = stdin_data.get("last_assistant_message", "")

    # Save assistant message
    if last_message:
        asyncio.run(_post_message(
            host, port,
            session_id=session_id,
            role="assistant",
            content=last_message[:5000],
        ))

    # Log stop event
    asyncio.run(_post_event(
        host, port,
        event_type="stop",
        session_id=session_id,
        content=last_message[:500] if last_message else "Response completed",
        metadata={"message_len": len(last_message) if last_message else 0},
    ))


# ===== tool-use =====

@app.command("tool-use")
def tool_use(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
) -> None:
    """Hook: PostToolUse. Logs tool calls to the logbook."""
    stdin_data = _parse_stdin()
    if not stdin_data:
        _log("tool-use", "no stdin data")
        return

    session_id = stdin_data.get("session_id")
    tool_name = stdin_data.get("tool_name", "unknown")
    _log("tool-use", f"session={session_id} tool={tool_name}")
    tool_input = stdin_data.get("tool_input", {})

    asyncio.run(_post_event(
        host, port,
        event_type="tool_use",
        session_id=session_id,
        tool_name=tool_name,
        content=f"Called {tool_name}",
        metadata={"input": tool_input},
    ))


# ===== save-reminder =====

@app.command("save-reminder")
def save_reminder() -> None:
    """Hook: PreCompact. Reminds Charlie to save before context compaction."""
    print(
        "<charlie-reminder>Context is about to be compacted. "
        "Call `session_update` NOW to save your progress before you lose context. "
        "Include what we worked on and next steps.</charlie-reminder>"
    )
    print(
        "<charlie-reminder>Remember to update knowledge, save decisions, etc "
        "so we don't lose anything.</charlie-reminder>"
    )


# ===== session-end =====

@app.command("session-end")
def session_end(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier"),
    session_id: str = typer.Option(..., help="Current session ID"),
) -> None:
    """Hook: SessionEnd. Silent on success."""
    asyncio.run(_session_end(host, port, source, session_id))


async def _session_end(host: str, port: int, source: str, session_id: str) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"http://{host}:{port}/api/sessions/end",
                json={"session_id": session_id, "source": source},
            )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(1)

    await _post_event(
        host, port,
        event_type="session_end", session_id=session_id,
        content=f"Session ended from {source}",
    )
