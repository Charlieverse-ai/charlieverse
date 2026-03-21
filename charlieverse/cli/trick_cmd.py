"""Trick commands — `charlie trick list|find|show`."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from charlieverse.config import config
from charlieverse.skills import _discover_skills, _find_skill, _parse_frontmatter, _skill_dirs, _source_label

console = Console()

app = typer.Typer(
    name="trick",
    help="Discover and inspect Charlie's tricks.",
    invoke_without_command=True,
)

@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    """List all available skills by default."""
    if ctx.invoked_subcommand is None:
        # Check if there's an unrecognized argument that might be a skill name
        # Typer doesn't support this natively, so we show help
        ctx.get_help()

def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4


@app.command("list")
def list_skills(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all available tricks and skills."""
    skills = _discover_skills()

    if json_output:
        console.print_json(json.dumps(skills))
        return

    if not skills:
        typer.echo("No tricks found.")
        return

    # Group by source
    groups: dict[str, list[dict]] = {}
    for skill in skills:
        source, _ = _source_label(skill["path"])
        groups.setdefault(source, []).append(skill)

    # Header
    count = len(skills)
    label = f"{count} Trick{'s' if count != 1 else ''}" if count else "No Tricks"
    console.print()
    console.print(f"[bold]{label}[/bold]")
    console.print()

    # Source labels for display
    source_labels = {
        "user": f"Charlie tricks ({config.path / 'tricks'})",
        "claude": "Claude skills (~/.claude/skills)",
        "copilot": "Copilot skills (~/.copilot/skills)",
        "cursor": "Cursor skills (~/.cursor/skills)",
        "codex": "Codex skills (~/.codex/skills)",
        "windsurf": "Windsurf skills",
        "gemini": "Gemini skills (~/.gemini/skills)",
        "shared": "Shared skills (~/.agents/skills)",
        "project": "Project tricks (.charlie/tricks)",
        "github": "Project skills (.github/skills)",
        "bundled": "Bundled tricks (Charlieverse)",
    }

    max_desc = 80

    for source, source_skills in groups.items():
        heading = source_labels.get(source, f"{source} skills")
        console.print(f"[bold]{heading}[/bold]")
        for skill in source_skills:
            desc = skill["description"][:max_desc].strip()
            if len(skill["description"]) > max_desc:
                desc += "…"

            console.print(f"  - [cyan]{skill['name']}[/cyan]: [dim]{desc or "None"}[/dim]")
        console.print()


def _source_label(path_str: str) -> tuple[str, str]:
    """Return (source, style) for a skill path."""
    if str(config.path) in path_str:
        return "user", "green"
    elif "/integrations/" in path_str:
        return "integration", "yellow"
    elif "/prompts/skills/" in path_str:
        return "bundled", "cyan"
    # Provider-specific paths
    elif "/.claude/" in path_str:
        return "claude", "magenta"
    elif "/.copilot/" in path_str:
        return "copilot", "blue"
    elif "/.cursor/" in path_str:
        return "cursor", "blue"
    elif "/.codex/" in path_str:
        return "codex", "blue"
    elif "/.codeium/" in path_str or "/windsurf/" in path_str:
        return "windsurf", "blue"
    elif "/.gemini/" in path_str:
        return "gemini", "blue"
    elif "/.agents/" in path_str:
        return "shared", "dim"
    elif "/.charlie/" in path_str:
        return "project", "green"
    elif "/.github/" in path_str:
        return "github", "dim"
    return "other", "dim"


@app.command("info")
def info_skill(
    name: str = typer.Argument(help="Skill name to inspect"),
) -> None:
    """Show metadata for a trick without printing the full contents."""
    from rich.markup import escape
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.tree import Tree

    path = _find_skill(name)
    if not path:
        typer.echo(f"Trick not found: {name}", err=True)
        raise typer.Exit(1)

    fm = _parse_frontmatter(path)
    skill_dir = path.parent
    source, source_style = _source_label(str(path))

    # Build info sections
    parts: list = []

    # Description
    desc = fm.get("description", "")
    if desc:
        parts.append(Text(desc, style="dim"))
        parts.append(Text(""))

    # Metadata grid
    meta = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    meta.add_column(style="bold dim", no_wrap=True)
    meta.add_column()

    meta.add_row("Source", f"[{source_style}]{source}[/{source_style}]")
    meta.add_row("Path", f"[dim]{skill_dir}[/dim]")
    if fm.get("argument-hint"):
        meta.add_row("Usage", f"/{fm.get('name', name)} {escape(fm['argument-hint'])}")
    if fm.get("allowed-tools"):
        tools = fm["allowed-tools"].split(", ")
        meta.add_row("Tools", "\n".join(f"[dim]•[/dim] {t}" for t in tools))

    parts.append(meta)

    # Files tree (skip if just SKILL.md)
    files = sorted(
        f.relative_to(skill_dir)
        for f in skill_dir.rglob("*")
        if f.is_file() and f.name != ".DS_Store"
    )
    if len(files) > 1:
        parts.append(Text(""))
        tree = Tree(f"[bold]{skill_dir.name}/[/bold]", guide_style="dim")
        dirs_added: dict = {}

        for f in files:
            parent = str(f.parent)
            if parent == ".":
                tree.add(f"[dim]{f.name}[/dim]" if f.name == "SKILL.md" else str(f.name))
            else:
                if parent not in dirs_added:
                    dirs_added[parent] = tree.add(f"[bold]{parent}/[/bold]")
                dirs_added[parent].add(str(f.name))

        parts.append(tree)

    # Wrap in a panel
    from rich.console import Group
    panel = Panel(
        Group(*parts),
        title=f"[bold cyan]{fm.get('name', name)}[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


@app.command("find")
def find_skill_cmd(
    name: str = typer.Argument(help="Skill name to find"),
    source: str | None = typer.Option(None, "--source", help="Provider Source")
) -> None:
    """Print the path to a skill's SKILL.md."""
    path = _find_skill(name)
    if not path:
        console.print(f"Trick not found [bold red]{name}[/bold red]")
        if not source:
            raise typer.Exit(1)
    typer.echo(str(path))


@app.command()
def read(
    name: str = typer.Argument(help="Skill name to display"), 
    source: str | None = typer.Option(None, "--source", help="Provider Source")
) -> None:
    """Print the contents of a skill's SKILL.md."""
    path = _find_skill(name)
    if not path:
        console.print(f"Trick not found [bold red]{name}[/bold red]")
        if not source:
            raise typer.Exit(1)
    else:
        console.print(path.read_text())
