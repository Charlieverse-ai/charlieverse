# Charlieverse Backlog

Bugs, follow-ups, and known-broken behavior that should get fixed but isn't blocking ship. Newer items at the top.

---

## Cannot connect to a remote Charlieverse instance without modifying the source

**Symptom:** Em wanted to point a Charlie running on one machine at a Charlieverse server running on another. Currently requires editing source to override the server URL — no config knob exists.

**Context:** Surfaced April 24 when Em moved from desktop → MBP via iCloud-synced Fi folder. The terminal-restart fix was for a separate connection issue; the remote-instance question stayed open.

**Fix direction:** environment variable or config-file knob (`CHARLIEVERSE_SERVER_URL` or similar) that the MCP client reads on startup.

**Why it matters:** unblocks multi-device usage and any future hosted-server setup.

---
