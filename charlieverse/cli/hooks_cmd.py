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
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from charlieverse.memory.sessions import SessionId
from charlieverse.types.dates import local_now, utc_now

if TYPE_CHECKING:
    from charlieverse.context.reminders.types import HookContext

import typer

from charlieverse.config import config

app = typer.Typer(
    name="hooks",
    help="Provider integration hooks.",
    no_args_is_help=True,
)

DEFAULT_HOST = config.server.ip_address()
DEFAULT_PORT = config.server.port
LOG_FILE = config.logs / "hooks.log"

# Claude has a tool output length before it saves to a file.
# This makes Charlie very inconsistent when reading the activation context,
# because Claude shows 2kb and then the file path. Then Charlie will either think he has enough, or only read part of the file
# Instead we will save our own file with explicit instructions for Charlie.
MAX_OUTPUT_LENGTH_BYTES = 10000

# ===== Helpers =====


@dataclass
class IncomingHookContext:
    event: str
    session_id: SessionId
    workspace: str
    stdin: dict = field(default_factory=dict)


def _log(event: str, msg: str, data: dict | None = None) -> None:
    """Append to hooks log file."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = local_now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {event}: {msg}"
        if data:
            keys = {k: str(v)[:500] for k, v in data.items() if k != "tool_input"}
            line += f" | {keys}"
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _time_now() -> str:
    return local_now().strftime("%A, %B %d, %Y at %I:%M:%S %p %Z")


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


def _is_subagent(stdin_data: dict | None) -> bool:
    """Check if this hook is firing inside a subagent call.

    Claude Code includes `agent_id` in stdin only for subagent contexts.
    """
    return bool(stdin_data and stdin_data.get("agent_id"))


async def _post_message(**kwargs) -> None:
    """POST a message to the server. Best-effort."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:  # ty:ignore[unresolved-attribute]
            await client.post(config.server.api_url("messages"), json=kwargs)
    except Exception:
        pass


async def _build_reminders(ctx: HookContext) -> str:
    """Run the reminders engine and return formatted output."""
    from charlieverse.context.reminders import RemindersEngine

    engine = RemindersEngine()
    reminders = await engine.process(ctx)
    return engine.format(reminders)


async def _run_user_hooks(hook_dir_name: str, **env_vars: str | None) -> str:
    """Run executable scripts from ~/.charlieverse/hooks/{hook_dir_name}/.

    Each script gets hook context as environment variables (CHARLIE_SESSION_ID, etc.).
    Scripts run in parallel. Their stdout is collected and returned as additional context.
    Scripts that fail or timeout (5s) are silently skipped.
    """
    hooks_dir = config.hooks / hook_dir_name
    if not hooks_dir.is_dir():
        return ""

    scripts = sorted(f for f in hooks_dir.iterdir() if f.is_file() and os.access(f, os.X_OK))
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
        except (TimeoutError, Exception):
            pass
        return ""

    results = await asyncio.gather(*[_run_one(s) for s in scripts])
    parts = [r for r in results if r]
    return "\n".join(parts)


def _output_context(context: str, hook_event: str) -> None:
    """Output context in the universal hookSpecificOutput JSON format."""

    # Save to a temp file
    if len(context.encode("utf-8")) >= MAX_OUTPUT_LENGTH_BYTES:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, encoding="utf-8") as tmp:
            tmp.write(context)
            context = f"<very-important>{'Activation Context' if hook_event == 'SessionStart' else 'Output'} saved to a temporary file. Before doing anything read 100% of the output: {tmp.name}</very-important>"

    output = json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": hook_event,
                "additionalContext": f"{context}",
            }
        }
    )
    _log(f"{hook_event}.result", msg=output)
    sys.stdout.write(output)
    sys.stdout.flush()


def _output_block(hook_event: str, reason: str) -> None:
    """Output context in the universal hookSpecificOutput JSON format."""
    output = json.dumps({"hookSpecificOutput": {"hookEventName": hook_event, "decision": "block", "reason": reason}})

    _log(f"{hook_event}.result", msg=output)
    sys.stdout.write(output)
    sys.stdout.flush()


def _incoming_context() -> IncomingHookContext | None:
    stdin_data = _parse_stdin()
    try:
        _log("stdin", "Incoming Hook Data", data=stdin_data)

        if not stdin_data:
            _log("missing-context", "ERROR: Skipped because of missing hook data in stdin")
            return None

        hook_name = stdin_data.get("hook_event_name")

        if not hook_name:
            _log("missing-hook-name", "ERROR: Skipped because of missing hook name", data=stdin_data)
            return None

        hook_name = str(hook_name)

        # Skip activation context for subagents — they don't need the full boot sequence
        if _is_subagent(stdin_data):
            _log(f"{hook_name}.skipped", "Skipping hook for subagent", data=stdin_data)
            return None

        # Claude provides the name of the agent in the input, so we'll restrict the hooks to just Charlieverse:Charlie
        agent_type = str(stdin_data.get("agent_type", "")).strip()
        if agent_type and agent_type != "Charlieverse:Charlie":
            _log(f"{hook_name}.skipped", "Skipping hook because the agent is not Charlie", data=stdin_data)
            return None

        # Providers send cwd in stdin JSON, fallback to cwd
        workspace = str(stdin_data.get("cwd")) or os.getcwd()
        session_id = SessionId(stdin_data.get("session_id"))

        if not session_id:
            _log(f"{hook_name}.skipped", "ERROR: Missing or invalid session_id", data=stdin_data)
            return None

        return IncomingHookContext(hook_name, session_id=session_id, workspace=workspace, stdin=stdin_data)
    except Exception:
        _log("error", "Got exception while parsing", data=stdin_data)


# ===== session-start =====


@app.command("session-start")
def session_start(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option(..., help="Source"),
    section: str | None = typer.Option(None, help="Render only this section of the activation context"),
) -> None:
    """Hook: SessionStart. Prints activation context to stdout."""
    context = _incoming_context()

    if context:
        asyncio.run(_session_start(host, port, source, context, section=section))

    raise typer.Exit(0)


async def _session_start(host: str, port: int, source: str, context: IncomingHookContext, *, section: str | None = None) -> None:
    body: dict = {"session_id": context.session_id, "source": source, "workspace": context.workspace}
    if section:
        body["section"] = section

    if section == "user-hooks":
        user_hook_output = await _run_user_hooks("session-start", session_id=context.session_id, workspace=context.workspace)
        if user_hook_output:
            _output_context(user_hook_output, hook_event="SessionStart")
        raise typer.Exit(0)
        return

    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # ty:ignore[unresolved-attribute]
            response = await client.post(
                f"http://{host}:{port}/api/sessions/start",
                json=body,
            )
            response.raise_for_status()
            activation = response.text
    except Exception as e:
        print(f"Error connecting to Charlieverse at {host}:{port}: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    if not activation:
        raise typer.Exit(0)

    result = activation

    # Run user hooks only for the last section (or full render) to avoid running them 7 times
    user_hook_output = await _run_user_hooks("session-start", session_id=context.session_id, workspace=context.workspace)
    if user_hook_output:
        result += user_hook_output

    _output_context(result, hook_event="SessionStart")

    raise typer.Exit(0)


# ===== prompt-submit =====


@app.command("prompt-submit")
def prompt_submit(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
) -> None:
    """Hook: UserPromptSubmit. Captures user message, runs reminders engine."""
    context = _incoming_context()

    if context:
        asyncio.run(_prompt_submit(context))

    typer.Exit(0)


async def _prompt_submit(context: IncomingHookContext) -> None:
    user_prompt = context.stdin.get("prompt")
    if not user_prompt:
        _log("prompt-submit", "ERROR: Missing User Submitted Text", data=context.stdin)
        return

    import httpx

    from charlieverse.context.reminders import HookContext

    # Build the hook context for the reminders engine
    now = utc_now()
    metadata: dict = {}
    session_id = context.session_id

    # Pre-fetch timing data from the server (best-effort, never blocks)
    try:
        url = config.server.api_url(f"session/{session_id}/prompt_submit")

        async with httpx.AsyncClient(timeout=2.0) as client:  # ty:ignore[unresolved-attribute]
            response = await client.get(url)
            if not isinstance(response, Exception) and response.status_code == 200:
                metadata = response.json()
    except Exception:
        pass

    _log("prompt-submit", "Metadata", data=metadata)
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

    await _post_message(
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
    context = _incoming_context()
    if context:
        last_message = str(context.stdin.get("last_assistant_message"))

        if not last_message:
            _log(context.event, "ERROR: Skipping stop hook because it's missing the last assistant message", data=context.stdin)
            raise typer.Exit(0)
            return

        # Save assistant message
        asyncio.run(
            _post_message(
                session_id=context.session_id,
                role="assistant",
                content=last_message,
            )
        )

        # Run user hooks from ~/.charlieverse/hooks/stop/
        asyncio.run(_run_user_hooks("stop", session_id=context.session_id, last_assistant_message=last_message))

    _log("Stop.result", msg="Finished")
    raise typer.Exit(0)


# ===== tool-use =====


@app.command("tool-use")
def tool_use(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option("", help="Provider identifier"),
) -> None:
    """Hook: PostToolUse."""
    context = _incoming_context()

    if context:
        tool_name = context.stdin.get("tool_name", "unknown")
        _log("tool-use", f"session={context.session_id} tool={tool_name}")

    typer.Exit(0)


# ===== session-end =====


@app.command("session-end")
def session_end(
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    source: str = typer.Option(..., help="Provider identifier"),
) -> None:
    """Hook: SessionEnd. Silent on success."""
    context = _incoming_context()

    if context:
        asyncio.run(_session_end(host, port, source, context.session_id))

    typer.Exit(0)


async def _session_end(host: str, port: int, source: str, session_id: SessionId) -> None:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:  # ty:ignore[unresolved-attribute]
            await client.post(
                f"http://{host}:{port}/api/sessions/end",
                json={"session_id": session_id, "source": source},
            )
    except Exception as e:
        _log("session-end", f"ERROR: {e}")
