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


def _wait_for_port_free(port: int, timeout: float = 15) -> None:
    """Block until nothing is listening on the given port."""
    import socket
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(0.5)
            sock.connect(("127.0.0.1", port))
            sock.close()
            # Connection succeeded — port still in use
            time.sleep(0.3)
        except (ConnectionRefusedError, OSError):
            # Connection refused — port is free
            return
    # Timeout — proceed anyway and let start() fail with a clear error


def _wait_for_health(timeout: float = 30, interval: float = 0.3) -> bool:
    """Poll the health endpoint until the server responds or timeout."""
    import time
    import urllib.request
    import urllib.error

    url = config.server.api_url("health")
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        # Check process is still alive first
        if not _is_running():
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        time.sleep(interval)
    return False


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


def _kill_port_holder(port: int) -> bool:
    """Kill a Charlieverse process holding the port. Returns True if something was killed.

    Only kills processes whose command line contains 'charlieverse' to avoid
    terminating unrelated services that happen to use the same port.
    """
    import subprocess
    try:
        # Get PIDs and their command names for the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5,
        )
        pids = [int(p.strip()) for p in result.stdout.strip().split("\n") if p.strip()]
        killed = False
        for pid in pids:
            try:
                # Verify the process belongs to us before killing
                cmd_result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "command="],
                    capture_output=True, text=True, timeout=5,
                )
                cmdline = cmd_result.stdout.strip().lower()
                if "charlieverse" not in cmdline and "charlie" not in cmdline:
                    continue
                os.kill(pid, signal.SIGTERM)
                killed = True
            except OSError:
                pass
        return killed
    except Exception:
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

    # Kill any orphan process holding the port (stale PID file scenarios)
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
        sock.close()
        # Port is occupied by something we don't know about — kill it
        if _kill_port_holder(port):
            typer.echo(f"Killed orphan process on port {port}")
            _wait_for_port_free(port)
    except (ConnectionRefusedError, OSError):
        pass  # Port is free

    if not foreground and transport != "stdio":
        # Fork to background
        pid = os.fork()
        if pid > 0:
            # Parent — wait for child to write PID, then poll health
            import time
            for _ in range(20):
                child_pid = _read_pid()
                if child_pid and child_pid != pid:
                    break
                time.sleep(0.2)

            if _wait_for_health():
                typer.echo(f"Charlieverse started (PID {_read_pid()})")
                typer.echo(f"Listening on {config.server.base_url()}")
            else:
                typer.echo("Failed to start Charlieverse", err=True)
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
    pid = _read_pid()
    stop()
    # Wait for the port to be free (not just the process to die)
    _wait_for_port_free(port)
    start(host=host, port=port, foreground=False, transport=transport)

@app.command("url")
def url(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, help="Port to listen on")
) -> None:
    """Print the server URL."""
    typer.echo(f"http://{host}:{port}")
