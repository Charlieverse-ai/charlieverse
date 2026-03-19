---
name: session-save
description: Save the current session and optionally generate story rollups.
allowed-tools: mcp(upsert_story, list_stories, get_story, delete_story, get_story_data, session_update), Agent(Charlieverse:tools:Storyteller)
---

## What this skill does

Saves the current session and optionally generates/updates story rollups (daily, weekly, monthly).

## Steps

### 1. Save the session

Call `session_update` with:
- `what_happened`: A concise summary of what happened this session
- `for_next_session`: What the next session should pick up on
- `tags`: Relevant tags
- `workspace`: The current workspace path if applicable

### 2. Check if a daily story needs updating

Call `get_story_data` with target `"daily"` to see if there are session-tier stories for today that could be rolled up into a daily.

If there are enough session stories (2+), or it's been a while since the last daily, spawn a **Storyteller** subagent with the data and have it generate a daily story. Save the result with `upsert_story`.

### 3. Cascade (optional)

If `$ARGUMENTS` contains "cascade" or "full", also generate weekly and monthly rollups:

- Call `get_story_data` with target `"weekly"` → spawn Storyteller → `upsert_story`
- Call `get_story_data` with target `"monthly"` → spawn Storyteller → `upsert_story`

Each tier depends on the one below it. If a tier returns no source stories, skip it and everything above.

### 4. Done

Report what was saved. No curl, no REST — everything goes through MCP tools.
