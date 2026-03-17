"""Root CLI app — `charlie` command."""

import typer

from charlieverse.cli import hooks, init_cmd, server_cmd, log_cmd, story_data_cmd, context_cmd, import_cmd, install_cli_cmd

app = typer.Typer(
    name="charlie",
    help="Charlieverse — persistent AI companion layer.",
    no_args_is_help=True,
)

app.add_typer(server_cmd.app, name="server")
app.add_typer(hooks.app, name="hooks")
app.command("init")(init_cmd.init)
app.command("story-data")(story_data_cmd.story_data)
app.command("log")(log_cmd.log)
app.command("context")(context_cmd.context)
app.command("import")(import_cmd.import_conversations)
app.command("install-cli")(install_cli_cmd.install_cli)
