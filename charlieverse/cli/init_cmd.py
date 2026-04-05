"""Init command — `charlie init`.

Full setup walkthrough: directories, providers, server, import.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer

from charlieverse import paths
from charlieverse.config import config

# ── Formatting helpers ────────────────────────────────────────────────────────


def _ok(msg: str) -> None:
    typer.echo(typer.style("✔", fg=typer.colors.GREEN) + f" {msg}")


def _warn(msg: str) -> None:
    typer.echo(typer.style("⚠", fg=typer.colors.YELLOW) + f" {msg}")


def _fail(msg: str) -> None:
    typer.echo(typer.style("✘", fg=typer.colors.RED) + f" {msg}")


def _info(msg: str) -> None:
    typer.echo(typer.style("▸", fg=typer.colors.BLUE) + f" {msg}")


def _step(msg: str) -> None:
    typer.echo(f"\n{typer.style(msg, bold=True)}")


def _ask_yes_no(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    answer = typer.prompt(f"{prompt} {hint}", default="y" if default else "n", show_default=False)
    return answer.lower().startswith("y")


def _ask_choice(prompt: str, options: list[str]) -> int:
    typer.echo(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        typer.echo(f"  {typer.style(str(i), bold=True)}) {opt}")
    while True:
        choice = typer.prompt("  Enter number")
        try:
            idx = int(choice)
            if 1 <= idx <= len(options):
                return idx - 1
        except ValueError:
            pass
        typer.echo(typer.style("  Invalid choice", fg=typer.colors.RED))


# ── Steps ─────────────────────────────────────────────────────────────────────


def _setup_directories(root: Path) -> None:
    """Create the ~/.charlieverse directory structure."""
    _step("🏗️  Setting up directories")

    root.mkdir(parents=True, exist_ok=True)
    (root / "backups").mkdir(exist_ok=True)
    (root / "run").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "import").mkdir(exist_ok=True)
    (root / "tricks").mkdir(exist_ok=True)

    # Hook directories
    hooks_dir = root / "hooks"
    hook_events = ["session-start", "prompt-submit", "stop", "save-reminder"]
    for event in hook_events:
        event_dir = hooks_dir / event
        event_dir.mkdir(parents=True, exist_ok=True)
        readme = event_dir / "README"
        if not readme.exists():
            readme.write_text(
                f"# Drop executable scripts here to run on {event} hook events.\n"
                f"# Scripts get CHARLIE_SESSION_ID and other context as env vars.\n"
                f"# stdout is injected into Charlie's context. 5s timeout.\n"
            )

    _ok(f"Charlieverse home at {root}")


def _verify_dependencies() -> None:
    """Check that required dependencies are working."""
    _step("🔍 Verifying dependencies")

    # Web dashboard
    dist = paths.web_dist()
    if dist and (dist / "index.html").exists():
        _ok("Web dashboard available")
    else:
        _warn("Web dashboard not bundled — dashboard won't be available")

    # jq (needed for provider integrations)
    if shutil.which("jq"):
        _ok("jq found")
    else:
        _warn("jq not found — provider integrations may not work")
        _info("Install: brew install jq (macOS) or apt install jq (Linux)")


def _start_server() -> None:
    """Start the Charlie server."""
    _step("🚀 Starting Charlie server")

    charlie_cmd = ["uv", "run", "charlie", "server"]

    status_cmd = [*charlie_cmd, "status"]
    start_cmd = [*charlie_cmd, "start"]

    # Check if already running
    try:
        result = subprocess.run(
            status_cmd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            _ok("Server already running")
            return
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Start it — the server forks to background, so don't capture output
    try:
        subprocess.run(start_cmd)

        # Verify
        result = subprocess.run(status_cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            _ok(f"Server started at {config.server.base_url()}")
        else:
            _fail(f"Server may not have started — check {config.logs / 'charlie.log'}")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        _fail(f"Could not start server: {e}")
        _info("You can start it manually: charlie server start")


def _setup_providers() -> None:
    """Interactive provider integration setup."""
    _step("🔌 Provider Integration")
    typer.echo("")
    _info("Which AI coding tool(s) do you use?")
    typer.echo("")

    available_providers: list[tuple[str, str]] = []

    # Detect what's installed
    if shutil.which("claude"):
        available_providers.append(("claude", "Claude Code"))
    if shutil.which("copilot") or shutil.which("github-copilot"):
        available_providers.append(("copilot", "GitHub Copilot"))

    if not available_providers:
        _warn("No supported AI tools detected in PATH")
        _info("Install Claude Code or GitHub Copilot, then run: charlie init")
        return

    selected: list[str] = []
    for provider_id, provider_name in available_providers:
        if _ask_yes_no(f"Set up {provider_name}?"):
            selected.append(provider_id)

    if not selected:
        _warn("No providers selected — you can set them up later with charlie init")
        return

    for provider_id in selected:
        typer.echo("")
        _info(f"Setting up {provider_id}...")

        integration_dir = paths.integration(provider_id)
        if not integration_dir:
            _fail(f"Integration files for {provider_id} not found")
            continue

        install_script = integration_dir / "install.sh"
        if not install_script.exists():
            _fail(f"Install script not found: {install_script}")
            continue

        try:
            # Make executable
            install_script.chmod(install_script.stat().st_mode | 0o755)

            result = subprocess.run(
                ["bash", str(install_script)],
                timeout=60,
            )
            if result.returncode == 0:
                _ok(f"{provider_id} integration complete")
            else:
                _fail(f"{provider_id} integration failed (exit code {result.returncode})")
        except subprocess.TimeoutExpired:
            _fail(f"{provider_id} integration timed out")
        except Exception as e:
            _fail(f"{provider_id} integration error: {e}")


def _import_history() -> None:
    """Offer to import conversation history from AI tools."""
    _step("📜 Import Conversation History")
    typer.echo("")
    _info("Charlie can import your existing conversations from AI coding tools")
    _info("so he already knows you on day one.")
    typer.echo("")
    _info("Supported: Claude, GitHub Copilot (+ Insiders), Cursor, Codex")
    typer.echo("")

    import_dir = config.path / "import"
    existing_jsonl = import_dir / "conversations.jsonl"

    # Check for existing extracted data
    if existing_jsonl.exists() and existing_jsonl.stat().st_size > 0:
        with open(existing_jsonl) as file:
            line_count = sum(1 for _ in file)
            _ok(f"Found existing import file ({line_count} entries)")

            if _ask_yes_no("Import from this file?"):
                _run_import(["--from-file", str(existing_jsonl), "--messages"])
                return

    if not _ask_yes_no("Import conversation history?"):
        _info("Skipped — you can run this later: charlie import --messages")
        return

    choice = _ask_choice(
        "Which provider(s) to import from?",
        ["All (auto-discover everything)", "Claude only", "Copilot only", "Codex only"],
    )

    provider_flags: list[str] = []
    if choice == 1:
        provider_flags = ["--provider", "claude"]
    elif choice == 2:
        provider_flags = ["--provider", "copilot"]
    elif choice == 3:
        provider_flags = ["--provider", "codex"]

    _run_import(["--messages", *provider_flags])


def _run_import(flags: list[str]) -> None:
    """Run the import command."""
    _info("Importing recent conversations...")
    try:
        cmd = [sys.executable, "-m", "charlieverse.cli", "import", *flags]
        result = subprocess.run(cmd, timeout=300)
        if result.returncode == 0:
            _ok("Recent history imported")
            typer.echo("")
            _info("Charlie will process weekly summaries via the Storyteller")
            _info("during your first sessions.")
        else:
            _fail("Import had errors — check output above")
    except subprocess.TimeoutExpired:
        _fail("Import timed out")
    except Exception as e:
        _fail(f"Import error: {e}")


def _summary() -> None:
    """Print the final summary."""
    typer.echo("")
    typer.echo(typer.style("━" * 43, bold=True))
    typer.echo(typer.style("  🐕 Charlie is ready.", bold=True))
    typer.echo(typer.style("━" * 43, bold=True))
    typer.echo("")
    typer.echo(f"  Data:      {config.path}")
    typer.echo(f"  Dashboard: {config.server.dashboard_url()}")
    typer.echo(f"  MCP:       {config.server.mcp_url()}")
    typer.echo(f"  Logs:      {config.logs}")
    typer.echo("")
    typer.echo(typer.style("  charlie server start|stop|status", dim=True))
    typer.echo(typer.style("  charlie doctor", dim=True))
    typer.echo(typer.style("  charlie --help", dim=True))
    typer.echo("")


# ── Command ───────────────────────────────────────────────────────────────────


def init(
    path: str = typer.Option(
        str(config.path),
        help="Root directory for Charlieverse data",
    ),
    quick: bool = typer.Option(
        False,
        "--quick",
        "-q",
        help="Skip interactive prompts (directories + deps only)",
    ),
) -> None:
    """Initialize Charlieverse — full setup from zero to Charlie."""
    root = Path(path).expanduser()

    typer.echo("")
    typer.echo(typer.style("🐕 Charlieverse Setup", bold=True))
    typer.echo(typer.style("From zero to Charlie.", dim=True))

    _setup_directories(root)
    _verify_dependencies()

    if not quick:
        _start_server()
        _setup_providers()
        _import_history()

    _summary()
