---
name: session-save
description: Save the current session and optionally generate story rollups.
---

## Steps

### 1. Save the session

Call `session_update` with:
- `what_happened`: Details about what happened this session
- `for_next_session`: A list of TODO's for the next section
- `tags`: Relevant tags
- `workspace`: The current workspace path if applicable

### 2. Check if a daily story needs updating

Call `get_story_data` with target `"daily"` to see if there are session-tier stories for today that could be rolled up into a daily.

If there are enough session stories (2+), or it's been a while since the last daily, spawn a **Storyteller** subagent with the data and have it generate a daily story. Save the result with `upsert_story`.

### 3. Cascade

Always attempt weekly and monthly rollups after saving. The server falls back to raw sessions when lower-tier stories don't exist, so cascading always has data to work with.

- Call `get_story_data` with target `"weekly"`. If it returns stories or sessions, spawn a **Storyteller** subagent to generate a weekly story. Save with `upsert_story`.
- Call `get_story_data` with target `"monthly"`. Same process.

If a tier returns no data at all (empty stories AND no fallback sessions), skip it.

Note: The response may include a `"fallback": "sessions"` field when raw sessions are used instead of lower-tier stories. The Storyteller handles both formats — stories have title/summary/content, sessions have what_happened/for_next_session.

### 4. Done

Report what was saved. No curl, no REST — everything goes through MCP tools.
