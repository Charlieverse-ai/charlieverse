---
name: charlie-import
description: Import conversation history from AI providers (Claude, Copilot, Codex, Cursor) and generate stories from the imported data. Use on first session to bootstrap memory from existing conversations, or anytime the person wants to import history from another provider/machine.
user-invocable: false
allowed-tools: Bash(charlie *), Bash(curl *), Agent(Charlieverse:tools:Storyteller)
---

You are importing conversation history from AI providers and turning it into stories.

## Step 0: Check for existing import

The setup script may have already extracted and imported recent messages. Check for `~/.charlieverse/import/conversations.jsonl` first:

```bash
ls -la ~/.charlieverse/import/conversations.jsonl
```

If it exists, skip extraction and jump to gap detection:

```bash
charlie import --from-file ~/.charlieverse/import/conversations.jsonl --stories
```

If the file doesn't exist, proceed with full extraction below.

## Step 1: Extract, import messages, and detect gaps

Run the import command with `--recent-days 30` so recent history loads immediately and older messages import in the background:

```bash
charlie import --messages --recent-days 30
```

This does:
1. Auto-discovers and extracts conversations from Claude, Copilot, Cursor, and Codex into JSONL (sorted newest-first)
2. Bulk-imports the last 30 days of messages into the database immediately
3. Kicks off a background process for older messages
4. Splits into weekly files, checks the DB for story gaps at all tiers, and reports what's missing

For a full foreground import (no background split), omit `--recent-days`:

```bash
charlie import --messages
```

The command prints an `<import_summary>` JSON with:
- `weeks_needing_stories` — weekly files with no matching story in the DB
- `months_needing_stories` — months that have weeklies but no monthly rollup
- `alltime_stale` — whether the all-time story needs regeneration

Optional flags:
- `--provider claude|copilot|codex` — filter to one provider
- `--dir /path` — scan additional directories (data copied from another machine)

## Step 2: Report what was found

Tell your person what providers were discovered, how many sessions/entries extracted, how many messages imported, and what story gaps exist. Ask if they want you to proceed with generating stories. This can take a few minutes for large histories.

## Step 3: Fill weekly gaps

Parse the `weeks_needing_stories` from the summary. For each week, spawn a Storyteller subagent with the weekly JSONL file path.

**CRITICAL: The Storyteller subagent returns a JSON object. YOU (the parent) must save it via curl. Do NOT tell the Storyteller to run curl — shell escaping of nested JSON in subagents is unreliable and produces garbage stories.**

For each Storyteller result, extract the JSON fields and save:

```bash
curl -s -X PUT http://127.0.0.1:8765/api/stories \
  -H "Content-Type: application/json" \
  -d '<the JSON object the Storyteller returned>'
```

Make sure the JSON has these fields: `title`, `summary`, `content`, `tier` (set to "weekly"), `period_start`, `period_end`.

Run Storyteller agents in parallel — batch small files (< 10 entries) together, give larger files their own agent.

## Step 4: Fill monthly gaps

After all weeklies land, parse `months_needing_stories` from the summary. For each month:
1. Fetch the weekly stories: `curl -s "http://127.0.0.1:8765/api/stories?tier=weekly"`
2. Filter to the relevant month
3. Spawn a Storyteller with those stories as input
4. Save the returned JSON via curl with `"tier": "monthly"`

Run monthly agents in parallel.

## Step 5: Regenerate all-time

If `alltime_stale` is set in the summary:
1. Fetch all monthly stories: `curl -s "http://127.0.0.1:8765/api/stories?tier=monthly"`
2. Spawn one Storyteller to write the full arc narrative
3. Save with `"tier": "all-time"`

Also regenerate the yearly story if needed.

## Important

- **The parent (you) always saves stories via curl, never the Storyteller subagent**
- Run Storyteller agents in parallel where possible (multiple weeks at once, multiple months at once)
- Don't generate session-tier stories from imports — weeklies are the right granularity for historical data
- The CLI handles dedup detection — if a week/month already has a story, it won't appear in the gap list
- Steps 3→4→5 must run in sequence (monthlies need weeklies, all-time needs monthlies)
