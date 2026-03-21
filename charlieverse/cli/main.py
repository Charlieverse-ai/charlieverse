"""Root CLI app — `charlie` command."""

import typer

from charlieverse.cli import hooks_cmd, init_cmd, server_cmd
from charlieverse.cli import log_cmd, story_data_cmd, context_cmd, import_cmd
from charlieverse.cli import config_cmd, trick_cmd, events_cmd

app = typer.Typer(
    name="charlie",
    help="Charlieverse — persistent AI companion layer.",
    no_args_is_help=True,
)

app.add_typer(server_cmd.app)
app.add_typer(hooks_cmd.app)
app.add_typer(config_cmd.app)
app.add_typer(trick_cmd.app)

app.command("init")(init_cmd.init)
app.command("story-data")(story_data_cmd.story_data)
app.command("log")(log_cmd.log)
app.command("context")(context_cmd.context)
app.command("import")(import_cmd.import_conversations)
app.command("events")(events_cmd.events)
