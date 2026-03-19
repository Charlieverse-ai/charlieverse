"""CLI command to preview the activation context."""

from __future__ import annotations

import typer
from charlieverse.config import config
from rich.console import Console
from rich.table import Table
console = Console()

app = typer.Typer(
    name="config",
    help="Get config values.",
    invoke_without_command=True
)

@app.callback()
def dump_config(ctx: typer.Context):
    if ctx.invoked_subcommand is not None:
        return
    table = Table("Key", "Value", show_lines=True)
    table.add_row("Charlieverse Path", config.path.as_posix())
    table.add_row("Database", config.database.as_posix())
    table.add_row("Dashboard", config.server.dashboard_url())
    table.add_row("MCP", config.server.mcp_url())
    table.add_row("API", config.server.api_url())
    console.print(table)

@app.command()
def path():
    print(config.path.as_posix())

@app.command()
def database():
    print(config.database.as_posix())

@app.command()
def logs():
    print(config.logs.as_posix())

@app.command()
def hooks():
    print(config.hooks.as_posix())

@app.command()
def dashboard():
    print(config.server.dashboard_url())

@app.command()
def mcp():
    print(config.server.mcp_url())

@app.command()
def api():
    print(config.server.api_url())