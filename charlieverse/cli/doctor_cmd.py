"""Doctor command — `charlie doctor`.

Runs a suite of independent health checks and reports pass/fail/warn for each.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from charlieverse.config import config
from charlieverse import paths

console = Console()


# ── Result types ─────────────────────────────────────────────────────────────


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str
    fix: str | None = None


def _pass(name: str, detail: str) -> CheckResult:
    return CheckResult(name=name, status=Status.PASS, detail=detail)


def _fail(name: str, detail: str, fix: str | None = None) -> CheckResult:
    return CheckResult(name=name, status=Status.FAIL, detail=detail, fix=fix)


def _warn(name: str, detail: str, fix: str | None = None) -> CheckResult:
    return CheckResult(name=name, status=Status.WARN, detail=detail, fix=fix)


# ── Individual checks ─────────────────────────────────────────────────────────


def check_python_version() -> CheckResult:
    """Python >= 3.12 required."""
    major, minor, micro = sys.version_info[:3]
    version_str = f"Python {major}.{minor}.{micro}"
    if (major, minor) >= (3, 12):
        return _pass("Python version", version_str)
    return _fail(
        "Python version",
        f"{version_str} (need >= 3.12)",
        fix="Install Python 3.12+ via pyenv or uv: uv python install 3.12",
    )


def check_dependencies() -> list[CheckResult]:
    """Verify key packages are importable."""
    packages = [
        ("fastmcp", "fastmcp"),
        ("aiosqlite", "aiosqlite"),
        ("sentence_transformers", "sentence-transformers"),
        ("spacy", "spacy"),
        ("typer", "typer"),
        ("rich", "rich"),
        ("yaml", "pyyaml"),
    ]
    results = []
    missing = []
    for module, pkg_name in packages:
        try:
            __import__(module)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        results.append(
            _fail(
                "Dependencies",
                f"Missing: {', '.join(missing)}",
                fix="uv sync",
            )
        )
    else:
        results.append(_pass("Dependencies", "All required packages importable"))
    return results


def check_spacy_model() -> CheckResult:
    """Verify en_core_web_sm is installed."""
    try:
        import spacy  # noqa: F401
        spacy.load("en_core_web_sm")
        return _pass("spaCy model", "en_core_web_sm loaded")
    except ImportError:
        return _fail(
            "spaCy model",
            "spacy not installed",
            fix="uv sync",
        )
    except OSError:
        return _fail(
            "spaCy model",
            "en_core_web_sm not found",
            fix="uv sync  (or: python -m spacy download en_core_web_sm)",
        )


def check_data_directory() -> list[CheckResult]:
    """Verify ~/.charlieverse exists with expected subdirectory structure."""
    results = []
    root = config.path

    if not root or str(root) == ".":
        results.append(
            _fail(
                "Data directory",
                "config.path not set — config.yaml may be missing",
                fix="charlie init",
            )
        )
        return results

    if not root.exists():
        results.append(
            _fail(
                "Data directory",
                f"{root} does not exist",
                fix="charlie init",
            )
        )
        return results

    results.append(_pass("Data directory", str(root)))

    expected_subdirs = ["backups", "hooks", "logs", "run"]
    missing_dirs = [d for d in expected_subdirs if not (root / d).exists()]
    if missing_dirs:
        results.append(
            _warn(
                "Data subdirectories",
                f"Missing: {', '.join(missing_dirs)}",
                fix="charlie init",
            )
        )
    else:
        results.append(_pass("Data subdirectories", "backups, hooks, logs, run"))

    # Hook event directories
    hook_events = ["session-start", "prompt-submit", "stop", "save-reminder"]
    hooks_dir = root / "hooks"
    if hooks_dir.exists():
        missing_hooks = [e for e in hook_events if not (hooks_dir / e).exists()]
        if missing_hooks:
            results.append(
                _warn(
                    "Hook directories",
                    f"Missing event dirs: {', '.join(missing_hooks)}",
                    fix="charlie init",
                )
            )
        else:
            results.append(_pass("Hook directories", f"{len(hook_events)} event dirs present"))

    return results


def check_database() -> list[CheckResult]:
    """Verify charlie.db exists, is readable, and responds to a basic query."""
    results = []
    db_path = config.database

    if not db_path or str(db_path) == ".":
        results.append(
            _fail(
                "Database path",
                "config.database not set",
                fix="charlie init",
            )
        )
        return results

    if not db_path.exists():
        results.append(
            _fail(
                "Database",
                f"{db_path} does not exist",
                fix="charlie server start  (the server creates the database on first run)",
            )
        )
        return results

    results.append(_pass("Database file", str(db_path)))

    # Try a simple read query
    try:
        conn = sqlite3.connect(str(db_path), timeout=3)
        cur = conn.execute("PRAGMA integrity_check")
        integrity = cur.fetchone()[0]
        schema_ver_row = conn.execute("PRAGMA user_version").fetchone()
        schema_ver = schema_ver_row[0] if schema_ver_row else 0
        conn.close()
        if integrity == "ok":
            results.append(_pass("Database integrity", f"ok (schema v{schema_ver})"))
        else:
            results.append(
                _fail(
                    "Database integrity",
                    f"integrity_check returned: {integrity}",
                    fix=f"Restore from backup in {config.path / 'backups'}",
                )
            )
    except sqlite3.Error as exc:
        results.append(
            _fail(
                "Database readable",
                str(exc),
                fix=f"Restore from backup in {config.path / 'backups'}",
            )
        )

    return results


def check_server() -> list[CheckResult]:
    """Check if the server is running via PID file and port, then hit health endpoint."""
    results = []
    pid_file = config.path / "run" / "charlie.pid"
    port = config.server.port
    host = config.server.host if config.server.host != "0.0.0.0" else "127.0.0.1"

    pid_running = False
    pid: int | None = None
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            pid_running = True
        except (ValueError, OSError):
            pid_running = False

    # Port check
    port_open = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        port_open = sock.connect_ex((host, port)) == 0
        sock.close()
    except OSError:
        pass

    if not pid_running and not port_open:
        results.append(
            _fail(
                "Server",
                "Not running",
                fix="charlie server start",
            )
        )
        return results

    if pid_running and port_open:
        results.append(_pass("Server process", f"Running (PID {pid})"))
        results.append(_pass("Server port", f":{port} open"))
    elif pid_running and not port_open:
        results.append(
            _warn(
                "Server",
                f"PID {pid} alive but port :{port} not reachable",
                fix="charlie server restart",
            )
        )
        return results
    else:
        results.append(
            _warn(
                "Server",
                f"Port :{port} is open but no PID file — may be an orphan process",
                fix="charlie server restart",
            )
        )

    # Health endpoint
    import urllib.request
    import urllib.error

    health_url = config.server.api_url("health")
    try:
        with urllib.request.urlopen(health_url, timeout=3) as resp:
            if resp.status == 200:
                results.append(_pass("Server health", f"{health_url} responded 200"))
            else:
                results.append(
                    _warn(
                        "Server health",
                        f"{health_url} returned HTTP {resp.status}",
                        fix="charlie server restart",
                    )
                )
    except urllib.error.URLError as exc:
        results.append(
            _warn(
                "Server health",
                f"Health endpoint unreachable: {exc.reason}",
                fix="charlie server restart",
            )
        )
    except Exception as exc:
        results.append(
            _warn(
                "Server health",
                f"Unexpected error: {exc}",
                fix="charlie server restart",
            )
        )

    return results


def _claude_integration_path() -> Path | None:
    """Return the path where the Claude plugin is installed (from config path)."""
    if not config.path or str(config.path) == ".":
        return None
    return config.path / "integrations" / "claude"


def _copilot_plugin_path() -> Path | None:
    """Find the copilot plugin integration directory."""
    copilot = paths.integration("copilot")
    if copilot:
        return copilot / "plugin"
    return None


def check_providers() -> list[CheckResult]:
    """Detect installed providers and verify their Charlie configs."""
    results = []

    # ── Claude Code ──────────────────────────────────────────────────────────
    claude_bin = shutil.which("claude")
    if not claude_bin:
        results.append(
            _warn(
                "Provider: Claude Code",
                "claude CLI not found in PATH",
                fix="Install Claude Code from https://claude.ai/code",
            )
        )
    else:
        results.append(_pass("Provider: Claude Code", f"claude CLI found at {claude_bin}"))

        # Check ~/.claude/settings.json for Charlie settings
        claude_settings = Path.home() / ".claude" / "settings.json"
        if not claude_settings.exists():
            results.append(
                _warn(
                    "Claude Code config",
                    "~/.claude/settings.json not found",
                    fix="Run: ./integrations/claude/install.sh",
                )
            )
        else:
            try:
                settings = json.loads(claude_settings.read_text())
                enabled_plugins = settings.get("enabledPlugins", {})
                charlie_enabled = any(
                    "charlieverse" in k.lower() or "Charlie" in k
                    for k in enabled_plugins
                )
                if charlie_enabled:
                    results.append(_pass("Claude Code config", "Charlieverse plugin enabled in settings.json"))
                else:
                    results.append(
                        _warn(
                            "Claude Code config",
                            "Charlieverse plugin not found in ~/.claude/settings.json enabledPlugins",
                            fix="Run: ./integrations/claude/install.sh",
                        )
                    )
            except (json.JSONDecodeError, OSError) as exc:
                results.append(
                    _warn(
                        "Claude Code config",
                        f"Could not read ~/.claude/settings.json: {exc}",
                        fix="Run: ./integrations/claude/install.sh",
                    )
                )

        # Check installed plugin directory
        charlie_integration = _claude_integration_path()
        if charlie_integration and (charlie_integration / ".claude-plugin" / "plugin.json").exists():
            results.append(_pass("Claude Code plugin", f"Plugin installed at {charlie_integration}"))
        else:
            results.append(
                _warn(
                    "Claude Code plugin",
                    "Plugin not found in charlieverse data directory",
                    fix="Run: ./integrations/claude/install.sh",
                )
            )

        # Check hooks.json is present in the plugin dir
        if charlie_integration:
            hooks_json = charlie_integration / "hooks" / "hooks.json"
            if hooks_json.exists():
                results.append(_pass("Claude Code hooks", f"hooks.json present"))
            else:
                results.append(
                    _warn(
                        "Claude Code hooks",
                        "hooks/hooks.json missing from plugin directory",
                        fix="Run: ./integrations/claude/install.sh",
                    )
                )

    # ── VS Code / Copilot ────────────────────────────────────────────────────
    code_bin = shutil.which("code")
    if not code_bin:
        results.append(
            _warn(
                "Provider: VS Code / Copilot",
                "code CLI not found in PATH",
                fix="Install VS Code and run: Shell Command: Install 'code' command in PATH",
            )
        )
    else:
        results.append(_pass("Provider: VS Code / Copilot", f"code CLI found at {code_bin}"))

        copilot_plugin = _copilot_plugin_path()
        vscode_settings_candidates = [
            Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json",
            Path.home() / ".config" / "Code" / "User" / "settings.json",
        ]
        vscode_settings: Path | None = next(
            (p for p in vscode_settings_candidates if p.exists()), None
        )

        if vscode_settings is None:
            results.append(
                _warn(
                    "VS Code config",
                    "VS Code settings.json not found",
                    fix="Run: ./integrations/copilot/install.sh",
                )
            )
        else:
            raw = vscode_settings.read_text(errors="replace")
            if copilot_plugin:
                plugin_dir_str = str(copilot_plugin.resolve())
                if plugin_dir_str in raw or "charlieverse" in raw.lower():
                    results.append(_pass("VS Code config", "Charlieverse plugin registered in VS Code settings"))
                else:
                    results.append(
                        _warn(
                            "VS Code config",
                            "Charlieverse plugin not found in VS Code settings.json",
                            fix="Run: charlie init to set up Copilot integration",
                        )
                    )
            elif "charlieverse" in raw.lower():
                results.append(_pass("VS Code config", "Charlieverse found in VS Code settings"))
            else:
                results.append(
                    _warn(
                        "VS Code config",
                        "Charlieverse plugin not found in VS Code settings.json",
                        fix="Run: charlie init to set up Copilot integration",
                    )
                )

        # Check copilot plugin hooks.json
        if copilot_plugin:
            copilot_hooks = copilot_plugin / "hooks" / "hooks.json"
            if copilot_hooks.exists():
                results.append(_pass("VS Code / Copilot hooks", "hooks.json present"))
            else:
                results.append(
                    _warn(
                        "VS Code / Copilot hooks",
                        "hooks/hooks.json missing from copilot plugin directory",
                        fix="Run: charlie init to set up Copilot integration",
                    )
                )

    # ── Cursor ───────────────────────────────────────────────────────────────
    cursor_bin = shutil.which("cursor")
    cursor_dir = Path.home() / ".cursor"
    if cursor_bin or cursor_dir.exists():
        location = cursor_bin or str(cursor_dir)
        results.append(
            _warn(
                "Provider: Cursor",
                f"Cursor detected ({location}) — no Charlieverse integration available yet",
            )
        )
    # No result = not detected, which is fine — don't clutter output for uninstalled tools.

    # ── Codex CLI ────────────────────────────────────────────────────────────
    codex_bin = shutil.which("codex")
    codex_dir = Path.home() / ".codex"
    if codex_bin or codex_dir.exists():
        location = codex_bin or str(codex_dir)
        results.append(
            _warn(
                "Provider: Codex",
                f"Codex detected ({location}) — no Charlieverse integration available yet",
            )
        )

    return results


def check_hooks() -> list[CheckResult]:
    """Verify hooks are registered for detected providers by inspecting hooks.json files."""
    results = []
    expected_hooks = {"SessionStart", "UserPromptSubmit", "Stop"}

    # Claude hooks
    charlie_integration = _claude_integration_path()
    if charlie_integration:
        hooks_json_path = charlie_integration / "hooks" / "hooks.json"
        if hooks_json_path.exists():
            try:
                data = json.loads(hooks_json_path.read_text())
                registered = set(data.get("hooks", {}).keys())
                missing = expected_hooks - registered
                if missing:
                    results.append(
                        _warn(
                            "Claude Code hooks registration",
                            f"Missing hook events: {', '.join(sorted(missing))}",
                            fix="Run: ./integrations/claude/install.sh",
                        )
                    )
                else:
                    results.append(_pass("Claude Code hooks registration", f"SessionStart, UserPromptSubmit, Stop registered"))
            except (json.JSONDecodeError, OSError) as exc:
                results.append(
                    _warn(
                        "Claude Code hooks registration",
                        f"Could not read hooks.json: {exc}",
                    )
                )

    # Copilot hooks
    copilot_plugin_dir = _copilot_plugin_path()
    copilot_hooks_path = copilot_plugin_dir / "hooks" / "hooks.json" if copilot_plugin_dir else None
    if copilot_hooks_path and copilot_hooks_path.exists():
        try:
            data = json.loads(copilot_hooks_path.read_text())
            registered = set(data.get("hooks", {}).keys())
            missing = expected_hooks - registered
            if missing:
                results.append(
                    _warn(
                        "VS Code / Copilot hooks registration",
                        f"Missing hook events: {', '.join(sorted(missing))}",
                        fix="Run: ./integrations/copilot/install.sh",
                    )
                )
            else:
                results.append(_pass("VS Code / Copilot hooks registration", "SessionStart, UserPromptSubmit, Stop registered"))
        except (json.JSONDecodeError, OSError) as exc:
            results.append(
                _warn(
                    "VS Code / Copilot hooks registration",
                    f"Could not read hooks.json: {exc}",
                )
            )

    if not results:
        results.append(
            _warn(
                "Hooks registration",
                "No provider hooks.json files found to inspect — run a provider install first",
                fix="./integrations/claude/install.sh  or  ./integrations/copilot/install.sh",
            )
        )

    return results


def check_web_dashboard() -> CheckResult:
    """Verify web dashboard assets exist."""
    dist_dir = paths.web_dist()

    if not dist_dir:
        return _warn(
            "Web dashboard",
            "Web dashboard assets not found — dashboard won't be available",
            fix="Reinstall charlieverse or build from source: cd web && npm run build",
        )

    index_html = dist_dir / "index.html"
    if not index_html.exists():
        return _fail(
            "Web dashboard",
            f"web/dist incomplete — index.html missing in {dist_dir}",
            fix="Reinstall charlieverse or rebuild: cd web && npm run build",
        )

    # Count assets as a basic sanity check
    assets = list((dist_dir / "assets").glob("*")) if (dist_dir / "assets").exists() else []
    return _pass("Web dashboard", f"web/dist built ({len(assets)} asset(s))")


# ── Runner ────────────────────────────────────────────────────────────────────


def _run_check(fn: Callable[[], CheckResult | list[CheckResult]]) -> list[CheckResult]:
    """Run a check function and always return a list, catching unexpected exceptions."""
    try:
        result = fn()
        checks: list[CheckResult] = result if isinstance(result, list) else [result]  # type: ignore[assignment]
        return checks
    except Exception as exc:
        name = getattr(fn, "__name__", "unknown")
        return [_fail(name, f"Unexpected error: {exc}")]


def _status_icon(status: Status) -> str:
    return {
        Status.PASS: "[green]✓[/green]",
        Status.FAIL: "[red]✗[/red]",
        Status.WARN: "[yellow]![/yellow]",
    }[status]


def _status_label(status: Status) -> str:
    return {
        Status.PASS: "[green]pass[/green]",
        Status.FAIL: "[red]FAIL[/red]",
        Status.WARN: "[yellow]warn[/yellow]",
    }[status]


# ── Command ───────────────────────────────────────────────────────────────────


def doctor(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all results, including passes"),
) -> None:
    """Verify the Charlieverse environment — checks Python, dependencies, database, server, providers, and more."""
    console.print()
    console.print("[bold]charlie doctor[/bold]  —  Charlieverse environment check")
    console.print()

    all_results: list[CheckResult] = []

    checks: list[tuple[str, Callable]] = [
        ("Python version", check_python_version),
        ("Dependencies", lambda: check_dependencies()),
        ("spaCy model", check_spacy_model),
        ("Data directory", check_data_directory),
        ("Database", check_database),
        ("Server", check_server),
        ("Providers", check_providers),
        ("Hooks", check_hooks),
        ("Web dashboard", check_web_dashboard),
    ]

    for section_name, fn in checks:
        results = _run_check(fn)
        all_results.extend(results)

        for r in results:
            if r.status == Status.PASS and not verbose:
                # Print passes inline without a table row — they are low noise
                console.print(f"  {_status_icon(r.status)} {r.name}: {r.detail}")
            elif r.status == Status.WARN:
                console.print(f"  {_status_icon(r.status)} [yellow]{r.name}[/yellow]: {r.detail}")
                if r.fix:
                    console.print(f"     [dim]fix:[/dim] {r.fix}")
            elif r.status == Status.FAIL:
                console.print(f"  {_status_icon(r.status)} [red bold]{r.name}[/red bold]: {r.detail}")
                if r.fix:
                    console.print(f"     [dim]fix:[/dim] [cyan]{r.fix}[/cyan]")

    # ── Summary ───────────────────────────────────────────────────────────────
    passed = sum(1 for r in all_results if r.status == Status.PASS)
    failed = sum(1 for r in all_results if r.status == Status.FAIL)
    warned = sum(1 for r in all_results if r.status == Status.WARN)

    console.print()
    console.rule()

    summary_parts = []
    if passed:
        summary_parts.append(f"[green]{passed} passed[/green]")
    if warned:
        summary_parts.append(f"[yellow]{warned} warnings[/yellow]")
    if failed:
        summary_parts.append(f"[red]{failed} failed[/red]")

    console.print("  " + "  ·  ".join(summary_parts))

    # Critical failures get a prominent fix block
    critical_fixes = [r for r in all_results if r.status == Status.FAIL and r.fix]
    if critical_fixes:
        console.print()
        console.print("[red bold]Required fixes:[/red bold]")
        for r in critical_fixes:
            console.print(f"  [dim]#[/dim] {r.name}")
            console.print(f"  [cyan]{r.fix}[/cyan]")
            console.print()

    console.print()

    if failed:
        raise typer.Exit(1)
