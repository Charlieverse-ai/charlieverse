---
name: charlie-import
description: Import conversation history from AI providers (Claude, Copilot, Codex) and generate stories from the imported data. Use on first session to bootstrap memory from existing conversations, or anytime the person wants to import history from another provider/machine.
user-invocable: false
allowed-tools: Bash(charlie *), Bash(curl *), Agent(Charlieverse:tools:Storyteller)
---

You are importing conversation history from AI providers and turning it into stories.

## Step 1: Extract, import messages, and detect gaps

Run the full import command:

```bash
charlie import --messages --stories
```

This does three things in one pass:
1. Auto-discovers and extracts conversations from Claude, Copilot, and Codex into JSONL
2. Bulk-imports messages into the database for search_messages (deterministic dedup, safe to re-run)
3. Splits into weekly files, checks the DB for story gaps at all tiers, and reports what's missing

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

Parse the `weeks_needing_stories` from the summary. For each week, spawn a Storyteller subagent with the weekly JSONL file path from the summary. Run them in parallel — batch small files (< 10 entries) together, give larger files their own agent.

Each Storyteller should:
- Read the weekly JSONL file
- Write a narrative following brain-friendly-stories rules
- Save via `curl -s -X PUT http://127.0.0.1:8765/api/stories` with `"tier": "weekly"`

## Step 4: Fill monthly gaps

After all weeklies land, parse `months_needing_stories` from the summary. For each month, spawn a Storyteller that:
- Fetches the weekly stories for that month: `curl -s "http://127.0.0.1:8765/api/stories?tier=weekly"`
- Synthesizes them into a monthly chapter
- Saves with `"tier": "monthly"`

Run monthly agents in parallel.

## Step 5: Regenerate all-time

If `alltime_stale` is set in the summary, spawn one Storyteller that:
- Fetches all monthly stories: `curl -s "http://127.0.0.1:8765/api/stories?tier=monthly"`
- Writes the full arc narrative
- Saves with `"tier": "all-time"`

Also regenerate the yearly story if needed.

## Important

- Run Storyteller agents in parallel where possible (multiple weeks at once, multiple months at once)
- Don't generate session-tier stories from imports — weeklies are the right granularity for historical data
- The CLI handles dedup detection — if a week/month already has a story, it won't appear in the gap list
- Steps 3→4→5 must run in sequence (monthlies need weeklies, all-time needs monthlies)
