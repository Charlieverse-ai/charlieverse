#!/usr/bin/env python3
"""Extract conversation data from AI provider session files.

Auto-discovers and extracts conversations from:
  - Claude Code (~/.claude/projects/)
  - VS Code / Copilot (~/Library/Application Support/Code/)

Extracts user messages, assistant messages, tool calls + results into a single
combined JSONL file suitable for the Storyteller.

Usage:
    python tools/extract_conversations.py [output_file]

Defaults:
    output_file: ./conversations.jsonl
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# Shared helpers
# ============================================================

SKIP_TAGS = [
    "<system-reminder>", "<very-important>",
    "<now>", "hook additional context",
    "<ide_opened_file>", "<local-command",
    "<reminderInstructions>", "<environment_info>",
]


def _is_system_noise(text: str) -> bool:
    """Check if text is system/reminder content to skip."""
    return any(tag in text for tag in SKIP_TAGS)


# ============================================================
# Claude Code extractor
# ============================================================

def _claude_extract_text(content) -> str | None:
    """Pull plain text from Claude message content."""
    if isinstance(content, str):
        return content if not _is_system_noise(content) else None

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            if not _is_system_noise(block):
                parts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            if not _is_system_noise(text):
                stripped = text.strip()
                if stripped:
                    parts.append(stripped)

    combined = "\n".join(parts).strip()
    return combined if combined else None


def _claude_extract_tool_use(content) -> list[dict]:
    """Extract tool_use blocks from Claude assistant content."""
    tools: list[dict] = []
    if not isinstance(content, list):
        return tools
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            tools.append({
                "tool_id": block.get("id"),
                "name": block.get("name"),
                "input": block.get("input"),
            })
    return tools


def _claude_extract_tool_results(content) -> list[dict]:
    """Extract tool_result blocks from Claude user content."""
    results: list[dict] = []
    if not isinstance(content, list):
        return results
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            result_content = block.get("content", [])
            text_parts = []
            for part in (result_content if isinstance(result_content, list) else [result_content]):
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            results.append({
                "tool_id": block.get("tool_use_id"),
                "output": "\n".join(text_parts)[:2000],
            })
    return results


def process_claude_file(jsonl_path: Path) -> list[dict]:
    """Process a Claude Code JSONL file."""
    entries: list[dict] = []
    session_id = jsonl_path.stem
    is_subagent = "subagents" in str(jsonl_path)

    # Workspace comes from the cwd field of the first user/assistant message
    workspace: str | None = None

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")
            if msg_type not in ("user", "assistant"):
                continue

            # Grab workspace from first message's cwd
            if workspace is None:
                workspace = obj.get("cwd")

            message = obj.get("message", {})
            content = message.get("content", [])
            timestamp = obj.get("timestamp")
            role = message.get("role", msg_type)

            entry: dict = {
                "source": "claude",
                "session_id": obj.get("sessionId", session_id),
                "workspace": workspace or "unknown",
                "timestamp": timestamp,
                "role": role,
            }

            if is_subagent:
                entry["subagent"] = True

            if role == "assistant":
                text = _claude_extract_text(content)
                tools = _claude_extract_tool_use(content)
                if text:
                    entry["text"] = text
                if tools:
                    entry["tool_calls"] = tools
                if not text and not tools:
                    continue

            elif role == "user":
                text = _claude_extract_text(content)
                tool_results = _claude_extract_tool_results(content)
                if text:
                    entry["text"] = text
                if tool_results:
                    entry["tool_results"] = tool_results
                if not text and not tool_results:
                    continue

            entries.append(entry)

    return entries


# ============================================================
# Copilot / VS Code extractor
# ============================================================

def _epoch_ms_to_iso(ms: int | float) -> str:
    """Convert epoch milliseconds to ISO timestamp."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _extract_copilot_response(response: list, session_id: str, workspace: str,
                               timestamp: str | None, source: str = "copilot") -> list[dict]:
    """Extract assistant entries from a Copilot/Cursor response array.

    Shared between JSONL (kind=0) and JSON (version=3) formats.
    """
    if not isinstance(response, list):
        return []

    assistant_text = None
    tool_calls: list[dict] = []
    thinking: str | None = None

    for r in response:
        if not isinstance(r, dict):
            continue

        kind = r.get("kind")

        # Text response (kind is None, has "value")
        if kind is None and "value" in r:
            val = r["value"] if isinstance(r["value"], str) else ""
            text = val.strip()
            if text and not _is_system_noise(text):
                assistant_text = text

        # Tool invocations
        elif kind == "toolInvocationSerialized":
            tool_name = r.get("toolId", "unknown")
            past_tense = r.get("pastTenseMessage", {})
            description = past_tense.get("value", "") if isinstance(past_tense, dict) else ""
            tool_calls.append({
                "tool_id": r.get("toolCallId"),
                "name": tool_name,
                "description": description,
            })

        # Thinking / reasoning
        elif kind == "thinking":
            val = r.get("value", "")
            if isinstance(val, str):
                val = val.strip()
                if val:
                    thinking = val

    entries: list[dict] = []
    if assistant_text or tool_calls:
        entry: dict = {
            "source": source,
            "session_id": session_id,
            "workspace": workspace,
            "timestamp": timestamp,
            "role": "assistant",
        }
        if assistant_text:
            entry["text"] = assistant_text
        if tool_calls:
            entry["tool_calls"] = tool_calls
        if thinking:
            entry["thinking"] = thinking[:1000]
        entries.append(entry)
    return entries


def process_copilot_file(jsonl_path: Path) -> list[dict]:
    """Process a VS Code / Copilot chat session JSONL file."""
    entries: list[dict] = []

    workspace_hash = jsonl_path.parent.parent.name
    session_id = jsonl_path.stem

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Copilot stores session data in kind=0 objects with requests array
            if obj.get("kind") != 0:
                continue

            v = obj.get("v", {})
            requests = v.get("requests", [])

            for req in requests:
                timestamp = req.get("timestamp")
                ts_iso = _epoch_ms_to_iso(timestamp) if timestamp else None

                message = req.get("message", {})
                user_text = message.get("text", "").strip()

                if user_text and not _is_system_noise(user_text):
                    entries.append({
                        "source": "copilot",
                        "session_id": session_id,
                        "workspace": workspace_hash,
                        "timestamp": ts_iso,
                        "role": "user",
                        "text": user_text,
                    })

                entries.extend(_extract_copilot_response(
                    req.get("response", []), session_id, workspace_hash, ts_iso,
                ))

    return entries


def process_copilot_json_file(json_path: Path) -> list[dict]:
    """Process a Copilot/Cursor chat session JSON file (version 3 format).

    Single JSON object with top-level requests[] array, used by VS Code
    Copilot Chat panel and Cursor. Files are .json, not .jsonl.
    """
    entries: list[dict] = []

    try:
        with open(json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return entries

    # Only handle version 3 format
    if not isinstance(data, dict) or data.get("version") not in (3, 2, 1):
        return entries

    session_id = data.get("sessionId", json_path.stem)
    creation_date = data.get("creationDate")
    session_ts = _epoch_ms_to_iso(creation_date) if creation_date else None

    # Extract workspace from variableData if available
    workspace = json_path.parent.parent.name  # fallback to hash
    requests = data.get("requests", [])

    for req in requests:
        if not isinstance(req, dict):
            continue

        # Try to get workspace from first request's variableData
        if workspace == json_path.parent.parent.name:
            for var in req.get("variableData", {}).get("variables", []):
                if var.get("kind") == "workspace":
                    # The "name" field has "owner/repo" format
                    workspace = var.get("name", workspace)
                    break

        # Per-request timestamp (not always present)
        req_ts = session_ts

        # User message
        message = req.get("message", {})
        user_text = ""
        if isinstance(message, dict):
            user_text = message.get("text", "").strip()

        if user_text and not _is_system_noise(user_text):
            entries.append({
                "source": "copilot",
                "session_id": session_id,
                "workspace": workspace,
                "timestamp": req_ts,
                "role": "user",
                "text": user_text,
            })

        # Assistant response
        entries.extend(_extract_copilot_response(
            req.get("response", []), session_id, workspace, req_ts,
        ))

    return entries


# ============================================================
# Codex extractor
# ============================================================

def process_codex_file(jsonl_path: Path) -> list[dict]:
    """Process a Codex JSONL session file."""
    entries: list[dict] = []
    session_id = jsonl_path.stem
    workspace: str | None = None

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            record_type = obj.get("type")
            timestamp = obj.get("timestamp")
            payload = obj.get("payload", {})

            # Session metadata — grab workspace
            if record_type == "session_meta":
                workspace = payload.get("cwd")
                session_id = payload.get("id", session_id)
                continue

            if record_type != "response_item":
                continue

            ptype = payload.get("type")
            role = payload.get("role", "")

            # User message
            if ptype == "message" and role == "user":
                content = payload.get("content", [])
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        if text and not _is_system_noise(text):
                            parts.append(text.strip())
                text = "\n".join(parts).strip()
                if text:
                    entries.append({
                        "source": "codex",
                        "session_id": session_id,
                        "workspace": workspace or "unknown",
                        "timestamp": timestamp,
                        "role": "user",
                        "text": text,
                    })

            # Assistant message
            elif ptype == "message" and role == "assistant":
                content = payload.get("content", [])
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        if text:
                            parts.append(text.strip())
                text = "\n".join(parts).strip()
                if text:
                    entries.append({
                        "source": "codex",
                        "session_id": session_id,
                        "workspace": workspace or "unknown",
                        "timestamp": timestamp,
                        "role": "assistant",
                        "text": text,
                    })

            # Function/tool call
            elif ptype == "function_call":
                tool_input = payload.get("arguments", "{}")
                try:
                    parsed_input = json.loads(tool_input) if isinstance(tool_input, str) else tool_input
                except json.JSONDecodeError:
                    parsed_input = tool_input
                entries.append({
                    "source": "codex",
                    "session_id": session_id,
                    "workspace": workspace or "unknown",
                    "timestamp": timestamp,
                    "role": "assistant",
                    "tool_calls": [{
                        "tool_id": payload.get("call_id"),
                        "name": payload.get("name"),
                        "input": parsed_input,
                    }],
                })

            # Function/tool result
            elif ptype == "function_call_output":
                output = payload.get("output", "")
                entries.append({
                    "source": "codex",
                    "session_id": session_id,
                    "workspace": workspace or "unknown",
                    "timestamp": timestamp,
                    "role": "user",
                    "tool_results": [{
                        "tool_id": payload.get("call_id"),
                        "output": output[:2000],
                    }],
                })

    return entries


# ============================================================
# Provider discovery
# ============================================================

def _discover_providers(extra_dirs: list[Path] | None = None) -> list[tuple[str, Path]]:
    """Auto-discover provider data directories.

    Checks standard locations on the current system, plus any extra directories
    provided (e.g. copied from another machine).
    """
    home = Path.home()
    candidates: list[tuple[str, Path]] = []

    # Claude Code
    candidates.append(("claude", home / ".claude" / "projects"))

    # VS Code / Copilot (platform-specific)
    system = platform.system()
    if system == "Darwin":
        candidates.append(("copilot", home / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage"))
    elif system == "Linux":
        candidates.append(("copilot", home / ".config" / "Code" / "User" / "workspaceStorage"))
    else:
        appdata = Path(sys.environ.get("APPDATA", ""))
        candidates.append(("copilot", appdata / "Code" / "User" / "workspaceStorage"))

    # Cursor (same format as Copilot)
    if system == "Darwin":
        candidates.append(("copilot", home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"))
    elif system == "Linux":
        candidates.append(("copilot", home / ".config" / "Cursor" / "User" / "workspaceStorage"))

    # Codex
    candidates.append(("codex", home / ".codex" / "sessions"))

    # Extra directories — detect provider by contents
    for extra in (extra_dirs or []):
        if not extra.exists():
            continue
        _detect_providers_in_dir(extra, candidates)

    # Filter to existing paths, deduplicate
    seen: set[str] = set()
    providers: list[tuple[str, Path]] = []
    for name, path in candidates:
        key = f"{name}:{path}"
        if path.exists() and key not in seen:
            seen.add(key)
            providers.append((name, path))

    return providers


def _detect_providers_in_dir(root: Path, candidates: list[tuple[str, Path]]) -> None:
    """Detect provider data in an arbitrary directory (e.g. copied from another machine)."""
    # Claude: look for .claude/projects/
    claude_dir = root / ".claude" / "projects"
    if claude_dir.exists():
        candidates.append(("claude", claude_dir))

    # Codex: look for .codex/sessions/
    codex_dir = root / ".codex" / "sessions"
    if codex_dir.exists():
        candidates.append(("codex", codex_dir))

    # Copilot/Cursor: look for User/workspaceStorage/*/chatSessions/
    user_ws = root / "User" / "workspaceStorage"
    if user_ws.exists():
        candidates.append(("copilot", user_ws))

    # Also check workspaceStorage directly (in case User/ is the root)
    ws_dir = root / "workspaceStorage"
    if ws_dir.exists():
        candidates.append(("copilot", ws_dir))

    # Cursor: .cursor marker at root, data in User/workspaceStorage/
    if (root / ".cursor").exists():
        cursor_ws = root / "User" / "workspaceStorage"
        if cursor_ws.exists():
            candidates.append(("copilot", cursor_ws))


# ============================================================
# Main
# ============================================================

def _find_copilot_files(provider_dir: Path) -> list[tuple[Path, callable]]:
    """Find both JSONL and JSON copilot/cursor chat files with their processors."""
    files: list[tuple[Path, callable]] = []
    for p in sorted(provider_dir.rglob("chatSessions/*.jsonl")):
        files.append((p, process_copilot_file))
    for p in sorted(provider_dir.rglob("chatSessions/*.json")):
        files.append((p, process_copilot_json_file))
    return files


PROVIDER_PROCESSORS = {
    "claude": (lambda d: sorted(d.rglob("*.jsonl")), process_claude_file),
    "copilot": (lambda d: _find_copilot_files(d), None),  # special: mixed formats
    "codex": (lambda d: sorted(d.rglob("*.jsonl")), process_codex_file),
}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Extract conversations from AI providers")
    parser.add_argument("-o", "--output", default="conversations.jsonl", help="Output JSONL file")
    parser.add_argument("dirs", nargs="*", help="Extra directories to scan (e.g. copied from another machine)")
    args = parser.parse_args()

    output_file = Path(args.output)
    extra_dirs = [Path(d) for d in args.dirs]

    providers = _discover_providers(extra_dirs)
    if not providers:
        print("No provider data found.", file=sys.stderr)
        sys.exit(1)

    print(f"Discovered providers: {', '.join(f'{name} ({path})' for name, path in providers)}")

    total_entries = 0
    total_sessions = 0

    with open(output_file, "w") as out:
        for provider_name, provider_dir in providers:
            spec = PROVIDER_PROCESSORS.get(provider_name)
            if not spec:
                print(f"[{provider_name}] Unknown provider, skipping")
                continue

            finder, default_processor = spec
            print(f"\n[{provider_name}] Scanning {provider_dir}")
            found = finder(provider_dir)
            print(f"[{provider_name}] Found {len(found)} files")

            provider_entries = 0
            provider_sessions = 0

            for i, item in enumerate(found):
                # Mixed-format providers return (path, processor) tuples
                if isinstance(item, tuple):
                    file_path, processor = item
                else:
                    file_path, processor = item, default_processor

                entries = processor(file_path)
                if entries:
                    provider_sessions += 1
                    for entry in entries:
                        out.write(json.dumps(entry) + "\n")
                        provider_entries += 1

                if (i + 1) % 100 == 0:
                    print(f"[{provider_name}]   Processed {i + 1}/{len(found)} files...")

            print(f"[{provider_name}] {provider_sessions} sessions, {provider_entries} entries")
            total_entries += provider_entries
            total_sessions += provider_sessions

    print("\nDone.")
    print(f"  Total sessions: {total_sessions}")
    print(f"  Total entries: {total_entries}")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
