---
name: charlie-import
description: Import conversation history from AI providers (Claude, Copilot, Codex) and generate stories from the imported data. Use on first session to bootstrap memory from existing conversations, or anytime the person wants to import history from another provider/machine.
user-invocable: false
allowed-tools: Bash(charlie *), Bash(curl *), Agent(Charlieverse:tools:Storyteller)
---

You are importing conversation history from AI providers and turning it into stories.

## Step 1: Extract conversations

Run the extraction command:

```bash
charlie import
```

This auto-discovers conversation data from Claude Code, VS Code/Copilot, and Codex on the local machine. It outputs a JSONL file and prints an `<import_summary>` with stats.

If the person mentioned a specific provider, pass `--provider`:
```bash
charlie import --provider claude
```

If they have data from another machine, pass `--dir`:
```bash
charlie import --dir /path/to/copied/data
```

## Step 2: Report what was found

Tell your person what providers were discovered and how many sessions/entries were extracted. Ask if they want you to proceed with generating stories from the data. This can take a few minutes for large histories.

## Step 3: Generate stories

The JSONL file contains entries grouped by session_id with timestamps. You need to:

1. Read the JSONL file and group entries by week (using timestamps)
2. For each week, spawn a Storyteller subagent to generate a weekly story
3. After all weeklies are done, generate monthly rollups
4. After monthlies, generate a yearly and all-time story

Use the Storyteller agent for each story. Each Storyteller should:
- Read the relevant portion of the JSONL (or the lower-tier stories for rollups)
- Write a narrative following brain-friendly-stories rules
- Save via `curl -s -X PUT http://127.0.0.1:8765/api/stories`

### Weekly story generation

For each week's data, the Storyteller needs the raw conversation entries. Pass the JSONL file path and the date range.

### Rollup generation

For monthly/yearly/all-time, use the `/session-save` skill with the tier argument:
```
/session-save monthly 2026-01
/session-save yearly 2026
/session-save all_time
```

Or have Storytellers read existing stories from the API and synthesize:
```bash
curl -s "http://127.0.0.1:8765/api/stories?tier=weekly&limit=50"
```

## Important

- Run Storyteller agents in parallel where possible (multiple weeks at once)
- Don't generate session-tier stories from imports — dailies and weeklies are the right granularity for historical data
- The person's existing stories should not be overwritten — check for overlapping periods before generating
