"""CLI command to symlink charlie into PATH."""

from __future__ import annotations

from pathlib import Path

import typer


def install_cli(
    target_dir: Path = typer.Option(
        "/usr/local/bin", "--target", "-t",
        help="Directory to symlink into (must be on PATH)",
    ),
) -> None:
    """Add charlie to your PATH by symlinking into /usr/local/bin."""
    bin_dir = Path(__file__).resolve().parent.parent.parent / "bin"
    scripts = ["charlie", "charlie-commit", "charlie-claude"]

    target_dir.mkdir(parents=True, exist_ok=True)

    for script in scripts:
        src = bin_dir / script
        if not src.exists():
            continue

        dest = target_dir / script
        if dest.exists() or dest.is_symlink():
            dest.unlink()

        dest.symlink_to(src)
        typer.echo(f"  {script} → {dest}")

    typer.echo(f"\nDone. Make sure {target_dir} is on your PATH.")
