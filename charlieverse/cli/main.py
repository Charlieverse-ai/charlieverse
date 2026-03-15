"""Root CLI app — `charlie` command."""

import typer

from charlieverse.cli import hooks, init_cmd, server_cmd, events_cmd

app = typer.Typer(
    name="charlie",
    help="Charlieverse — persistent AI companion layer.",
    no_args_is_help=True,
)

app.add_typer(server_cmd.app, name="server")
app.add_typer(hooks.app, name="hooks")
app.command("init")(init_cmd.init)
app.command("events")(events_cmd.events)
