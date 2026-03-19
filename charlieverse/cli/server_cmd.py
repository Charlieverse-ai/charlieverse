"""Server commands — `charlie server start|stop|status|restart`."""

from __future__ import annotations
from typing import cast

import os
import signal
import sys
import typer

from charlieverse.config import config

app = typer.Typer(
    name="server",
    help="Manage the Charlieverse MCP server.",
    no_args_is_help=True,
)

DEFAULT_HOST = config.server.host
DEFAULT_PORT = config.server.port
PID_FILE = config.path / "run" / "charlie.pid"
LOG_FILE = config.logs / "charlie.log"


def _ensure_dirs() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _write_pid() -> None:
    _ensure_dirs()
    PID_FILE.write_text(str(os.getpid()))


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, FileNotFoundError):
        return None


def _clear_pid() -> None:
    if PID_FILE.exists():
        PID_FILE.unlink()


def _is_running() -> bool:
    pid = _read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        _clear_pid()
        return False


@app.command("start")
def start(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to listen on"),
    foreground: bool = typer.Option(False, "-f", "--foreground", help="Run in foreground"),
    transport: str = typer.Option("http", help="Transport: http, sse, or stdio"),
) -> None:
    """Start the Charlieverse server."""
    if _is_running():
        typer.echo(f"Charlieverse is already running (PID {_read_pid()})")
        return

    if not foreground and transport != "stdio":
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent — wait and check
            import time

            time.sleep(2)
            if _is_running():
                typer.echo(f"Charlieverse started (PID {_read_pid()})")
                typer.echo(f"Listening on {config.server.base_url()}")
            else:
                typer.echo("Failed to start Charlieverse", err=True)
                # Show the last few lines of the log so the error is visible
                if LOG_FILE.exists():
                    lines = LOG_FILE.read_text().strip().splitlines()
                    tail = lines[-15:] if len(lines) > 15 else lines
                    if tail:
                        typer.echo("\nServer log:", err=True)
                        for line in tail:
                            typer.echo(f"  {line}", err=True)
                raise typer.Exit(1)
            return

        # Child — detach and redirect output
        os.setsid()
        _ensure_dirs()
        log_fd = os.open(str(LOG_FILE), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        os.dup2(log_fd, sys.stdout.fileno())
        os.dup2(log_fd, sys.stderr.fileno())

    _write_pid()

    def handle_signal(signum, frame):
        _clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    from charlieverse.server import mcp, McpTransport

    if foreground:
        typer.echo(f"Starting Charlieverse on {config.server.mcp_url})")

    mcp.run(transport=cast(McpTransport, transport), host=host, port=port)


@app.command("stop")
def stop() -> None:
    """Stop the Charlieverse server."""
    pid = _read_pid()
    if pid is None:
        typer.echo("Charlieverse is not running")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        typer.echo(f"Stopped Charlieverse (PID {pid})")
        _clear_pid()
    except OSError as e:
        typer.echo(f"Failed to stop: {e}")
        _clear_pid()


@app.command("status")
def status() -> None:
    """Check if the server is running."""
    if _is_running():
        typer.echo(f"Charlieverse is running (PID {_read_pid()})")
    else:
        typer.echo("Charlieverse is not running")


@app.command("restart")
def restart(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to listen on"),
    transport: str = typer.Option("http", help="Transport: http, sse, or stdio"),
) -> None:
    """Restart the Charlieverse server."""
    stop()
    import time

    time.sleep(1)
    start(host=host, port=port, foreground=False, transport=transport)

@app.command("url")
def url(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to listen on")
) -> None:
    """Print the server URL."""
    typer.echo(f"http://{host}:{port}")
