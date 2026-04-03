"""Update command — `charlie update`."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer

from charlieverse import paths

_PKG_DIR = Path(__file__).resolve().parent.parent
_REPO_DIR = _PKG_DIR.parent


def _is_dev_install() -> bool:
    """Detect if running from a git repo checkout (editable install) vs pip/uv tool install."""
    return (_REPO_DIR / ".git").is_dir()


def _installed_providers() -> list[str]:
    """Detect which providers have been integrated by checking for installed artifacts."""
    import json

    providers = []

    # Claude: check for plugin in installed_plugins.json OR output style
    plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if plugins_file.exists():
        try:
            data = json.loads(plugins_file.read_text())
            plugin_ids = list(data.get("plugins", {}).keys())
            if any("Charlieverse" in pid or "charlieverse" in pid for pid in plugin_ids):
                providers.append("claude")
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: check output style directly
    if "claude" not in providers:
        for name in ("charlieverse-Charlie.md", "Charlie.md"):
            style = Path.home() / ".claude" / "output-styles" / name
            if style.exists() or style.is_symlink():
                providers.append("claude")
                break

    # Copilot: check for agent file
    copilot_agent = Path.home() / "Library" / "Application Support" / "Code" / "User" / "prompts" / "charlieverse-Charlie.agent.md"
    if copilot_agent.exists():
        providers.append("copilot")

    return providers


def _run(cmd: list[str], label: str) -> bool:
    """Run a command, print status, return success."""
    typer.echo(f"  {label}...", nl=False)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        typer.echo(" ✓")
        return True
    else:
        typer.echo(" ✗")
        if result.stderr:
            typer.echo(f"    {result.stderr.strip()}")
        return False


def update() -> None:
    """Update Charlieverse to the latest version, reinstall integrations, and restart."""
    typer.echo("Updating Charlieverse...\n")
    _run(["uv", "run", "charlie", "server", "stop"], "Stopping Server")

    # Step 1: Pull latest
    if _is_dev_install():
        typer.echo(f"→ Dev install detected at {_REPO_DIR}")
        # _run(["git", "-C", str(_REPO_DIR), "pull", "--ff-only"], "Pulling latest")
        _run(["uv", "tool", "install", str(_REPO_DIR), "-e"], "Reinstalling package")
    else:
        typer.echo("→ Package install detected")
        _run(["uv", "tool", "install", "-U", "charlieverse"], "Upgrading via uv")

    # # Step 2: Reinstall provider integrations
    providers = _installed_providers()
    if providers:
        typer.echo(f"\n→ Reinstalling integrations: {', '.join(providers)}")
        for provider in providers:
            integration_dir = paths.integration(provider)
            if integration_dir:
                install_script = integration_dir / "install.sh"
                if install_script.exists():
                    _run(["bash", str(install_script)], f"  {provider}")
                else:
                    typer.echo(f"    {provider}: no install.sh found, skipping")
            else:
                typer.echo(f"    {provider}: integration dir not found, skipping")
    else:
        typer.echo("\n→ No provider integrations detected, skipping")

    # Step 3: Restart server
    _run(["uv", "run", "charlie", "server", "start"], "Restarting Server")

    # Step 4: Remind about MCP reconnect
    typer.echo("\n✓ Update complete!")
    if "claude" in providers:
        typer.echo("\nTo finish, reconnect your MCP in Claude Code:")
        typer.echo("  /mcp reconnect plugin:Charlieverse:charlie-tools")
        typer.echo("\nOr start a new session.")
