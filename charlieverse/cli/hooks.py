"""Hook commands — triggered by provider lifecycle events.

Each command corresponds to a Claude Code hook event. They print context
to stdout (injected into the provider) and POST events to the server
for logbook tracking and message capture.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from charlieverse.context.reminders.types import HookContext

import typer

from charlieverse.config import config

app = typer.Typer(help="Provider integration hooks.")

DEFAULT_HOST = config.server.host
DEFAULT_PORT = config.server.port
LOG_FILE = config.logs.resolved_path / "hooks.log"


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




async def _post_message(host: str, port: int, **kwargs) -> None:
    """POST a message to the server. Best-effort."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"http://{host}:{port}/api/messages", json=kwargs)
    except Exception:
        pass


async def _build_reminders(ctx: HookContext) -> str:
    """Run the reminders engine and return formatted output."""
    from charlieverse.context.reminders import RemindersEngine

    engine = RemindersEngine()
    reminders = await engine.process(ctx)
    return engine.format(reminders)


def _build_context_static(*parts: str) -> str:
    """Build context from static parts only (for hooks that don't use the engine)."""
    sections: list[str] = [f"<now>{_time_now()}</now>"]
    sections.extend(parts)
    return "\n".join(sections)


async def _run_user_hooks(hook_dir_name: str, **env_vars: str | None) -> str:
    """Run executable scripts from ~/.charlieverse/hooks/{hook_dir_name}/.

    Each script gets hook context as environment variables (CHARLIE_SESSION_ID, etc.).
    Scripts run in parallel. Their stdout is collected and returned as additional context.
    Scripts that fail or timeout (5s) are silently skipped.
    """
    hooks_dir = Path.home() / ".charlieverse" / "hooks" / hook_dir_name
    if not hooks_dir.is_dir():
        return ""

    scripts = sorted(
        f for f in hooks_dir.iterdir()
        if f.is_file() and os.access(f, os.X_OK)
    )
    if not scripts:
        return ""

    # Build environment with hook context
    env = {**os.environ}
    for key, value in env_vars.items():
        if value is not None:
            env_key = f"CHARLIE_{key.upper()}"
            env[env_key] = str(value)

    async def _run_one(script: Path) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                str(script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode == 0 and stdout:
                return stdout.decode().strip()
        except (asyncio.TimeoutError, Exception):
            pass
        return ""

    results = await asyncio.gather(*[_run_one(s) for s in scripts])
    parts = [r for r in results if r]
    return "\n".join(parts)


def _output_context(context: str, hook_event: str = "UserPromptSubmit") -> None:
    """Output context in the universal hookSpecificOutput JSON format."""
    output = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": hook_event,
            "additionalContext": context,
        }
    })
    sys.stdout.write(output)
    sys.stdout.flush()

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
    # Providers send cwd in stdin JSON — use it as workspace if not passed via CLI
    stdin_data = _parse_stdin()
    if not workspace and stdin_data:
        workspace = stdin_data.get("cwd")
    if not session_id and stdin_data:
        session_id = stdin_data.get("session_id")
    asyncio.run(_session_start(host, port, source, workspace, session_id))
    typer.Exit(0)


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
            activation = data.get("activation", "")
    except Exception as e:
        print(f"Error connecting to Charlieverse at {host}:{port}: {e}", file=sys.stderr)
        raise typer.Exit(1)

    _output_context(_build_context_static(activation), hook_event="SessionStart")
    typer.Exit(0)


# ===== prompt-submit =====

@app.command("prompt-submit")
def prompt_submit(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
) -> None:
    """Hook: UserPromptSubmit. Captures user message, runs reminders engine."""
    stdin_data = _parse_stdin()
    session_id = stdin_data.get("session_id") if stdin_data else None
    _log("prompt-submit", f"session={session_id}")
    user_prompt = stdin_data.get("user_prompt") or stdin_data.get("content") or stdin_data.get("prompt") or "" if stdin_data else ""

    asyncio.run(_prompt_submit(host, port, session_id, user_prompt))
    typer.Exit(0)


async def _prompt_submit(
    host: str, port: int,
    session_id: str | None, user_prompt: str,
) -> None:
    from charlieverse.context.reminders import HookContext

    import httpx

    # Build the hook context for the reminders engine
    now = datetime.now()
    metadata: dict = {}

    # Pre-fetch timing data from the server (best-effort, never blocks)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Session timing + last assistant message in parallel
            session_resp, msg_resp = await asyncio.gather(
                client.get(f"http://{host}:{port}/api/sessions/{session_id}"),
                client.get(
                    f"http://{host}:{port}/api/messages/latest",
                    params={"session_id": session_id, "role": "assistant"},
                ),
                return_exceptions=True,
            )

            if not isinstance(session_resp, Exception) and session_resp.status_code == 200:
                session_data = session_resp.json()
                if session_data.get("created_at"):
                    metadata["session_start"] = session_data["created_at"]
                if session_data.get("updated_at"):
                    metadata["last_session_save_at"] = session_data["updated_at"]

            if not isinstance(msg_resp, Exception) and msg_resp.status_code == 200:
                msg_data = msg_resp.json()
                if msg_data.get("created_at"):
                    metadata["last_assistant_response_at"] = msg_data["created_at"]
    except Exception:
        pass

    ctx = HookContext(
        event="UserPromptSubmit",
        timestamp=now,
        session_id=session_id,
        message=user_prompt,
        metadata=metadata,
    )

    reminders_output = await _build_reminders(ctx)

    # Run user hooks from ~/.charlieverse/hooks/prompt-submit/
    user_hook_output = await _run_user_hooks("prompt-submit", session_id=session_id, message=user_prompt)
    if user_hook_output:
        reminders_output += user_hook_output

    _output_context(reminders_output, hook_event="UserPromptSubmit")

    # Post user message to server
    if user_prompt:
        await _post_message(
            host, port,
            session_id=session_id,
            role="user",
            content=user_prompt,
        )

# ===== stop =====

@app.command("stop")
def stop(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
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

    typer.Exit(0)

# ===== tool-use =====

@app.command("tool-use")
def tool_use(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
) -> None:
    """Hook: PostToolUse. Logs tool calls to the logbook."""
    stdin_data = _parse_stdin()
    if not stdin_data:
        _log("tool-use", "no stdin data")
        return

    session_id = stdin_data.get("session_id")
    tool_name = stdin_data.get("tool_name", "unknown")
    _log("tool-use", f"session={session_id} tool={tool_name}")
    typer.Exit(0)

# ===== save-reminder =====

@app.command("save-reminder")
def save_reminder() -> None:
    """Hook: PreCompact. Reminds Charlie to save before context compaction."""
    context = (
        "<charlie-reminder>Context is about to be compacted. "
        "Run `/session-save` NOW to save your progress before you lose context.</charlie-reminder>\n"
        "<charlie-reminder>Remember to update knowledge, save decisions, etc "
        "so we don't lose anything.</charlie-reminder>"
    )
    _output_context(context, hook_event="PreCompact")
    typer.Exit(0)

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
    typer.Exit(0)

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
