---
name: session-save
description: Save the current session as a story, or generate tier rollups (daily, weekly, monthly). Use when Charlie needs to save session progress, when a hook nudges to save, or when generating story rollups for higher tiers.
context: fork
agent: Charlieverse:tools:Storyteller
allowed-tools: Bash(charlie *), Bash(curl *), Agent(Charlieverse:tools:Storyteller)
---

### Report format:

Review the command JSON for the expected output. Below are some details on what the fields mean:
- title: A plaintext short description that encapsulates the context/theme of the content
- summary: A plaintext cognitively friendly paragraph about the content
- content: Your markdown formatted narrative/story of the content

---

After generating a story, save it by running:

```bash
curl -s -X PUT V_API/stories \
  -H "Content-Type: application/json" \
  -d '{
    "title": "<your title>",
    "summary": "<your summary>",
    "content": "<your story>",
    "tier": "<tier generating for>",
    "period_start": "<earliest datetime from data>",
    "period_end": "<latest datetime from data>",
    "session_id": "${CLAUDE_SESSION_ID}",
    "workspace": "<workspace id/path from data if present>"
  }'
```

If `$ARGUMENTS` contains a tier name (daily, weekly, monthly, yearly, all_time), generate a rollup story for that tier instead of a session story. The data above will contain lower-tier stories to synthesize.

## Cascade Rollups

After saving the session story, you MUST cascade up through the tiers to keep higher-level stories current. Run each in sequence:

### 1. Daily rollup
Fetch today's session stories and generate/update the daily story:

```bash
V_CLI story-data daily
```

Spawn a Storyteller subagent with that data. Save with `"tier": "daily"`.

### 2. Weekly rollup
Fetch this week's daily stories and generate/update the weekly story:

```bash
V_CLI story-data weekly
```

Spawn a Storyteller subagent with that data. Save with `"tier": "weekly"`.

### 3. Monthly rollup
Fetch this month's weekly stories and generate/update the monthly story:

```bash
V_CLI story-data monthly
```

Spawn a Storyteller subagent with that data. Save with `"tier": "monthly"`.

Each tier depends on the one below it (daily needs session stories, weekly needs dailies, monthly needs weeklies). Run them in sequence: daily → weekly → monthly. If a tier returns no lower-tier stories to synthesize, skip it and everything above it.

---
<session_data>
!`V_CLI story-data ${CLAUDE_SESSION_ID}`
</session_data>
