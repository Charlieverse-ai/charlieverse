---
title: Process identity guard before port-kill on server startup
date: 2026-03-21
status: accepted
tags: [server, cli, safety, startup]
---

# Process identity guard before port-kill on server startup

## Context

The `charlieverse server start` command uses `_kill_port_holder(port)` to clear the configured port before launching a new server process. The original implementation found all PIDs listening on the port via `lsof -ti :{port}` and sent `SIGTERM` to each one unconditionally. This works correctly when only a Charlieverse process holds the port, but is dangerous when another unrelated service happens to be bound to the same port — for example, during development when a local web server or database occupies the default port.

## Decision

Before sending `SIGTERM`, verify process identity using `ps -p {pid} -o command=` and check that the command line contains `"charlieverse"` or `"charlie"`. If neither substring is present, skip the PID. The function now returns `True` only if at least one matching process was killed, rather than returning `True` whenever any PID was found on the port.

## Alternatives Considered

- **Unconditional kill (status quo)**: Simple but could terminate unrelated services. Unacceptable in shared development environments.
- **Check the PID file only**: The existing `_is_running()` function checks a PID file. Using only the PID file to target the kill would miss orphaned processes whose PID file was deleted. Combining port-scan with identity check handles both cases.
- **Skip the kill entirely, fail if port is busy**: Would require the user to manually free the port. Worse developer experience with no safety benefit.

## Consequences

- The startup sequence will not kill processes it does not own, even if they share the configured port.
- If a non-Charlieverse process holds the port, `_kill_port_holder` returns `False` and the subsequent server bind will fail with a normal "address already in use" error — the user gets a clear signal rather than silent misbehavior.
- The identity check adds two `subprocess.run` calls per PID on startup (typically one PID or zero). The latency cost is negligible.
- Future changes to the process name or entry point must ensure the command line still contains `"charlieverse"` or `"charlie"` for the guard to recognize its own processes.
