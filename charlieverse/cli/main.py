"""Root CLI app — `charlie` command."""

from importlib.metadata import version

import typer

from charlieverse.cli import (
    config_cmd,
    context_cmd,
    doctor_cmd,
    hooks_cmd,
    import_cmd,
    init_cmd,
    server_cmd,
    story_data_cmd,
    trick_cmd,
    update_cmd,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"charlieverse {version('charlieverse')}")
        raise typer.Exit()


app = typer.Typer(
    name="charlie",
    help="Charlieverse — persistent AI companion layer.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """Charlieverse — persistent AI companion layer."""


app.add_typer(server_cmd.app)
app.add_typer(hooks_cmd.app)
app.add_typer(config_cmd.app)
app.add_typer(trick_cmd.app)

app.command("init")(init_cmd.init)
app.command("story-data")(story_data_cmd.story_data)
app.command("context")(context_cmd.context)
app.command("import")(import_cmd.import_conversations)
app.command("doctor")(doctor_cmd.doctor)
app.command("update")(update_cmd.update)
