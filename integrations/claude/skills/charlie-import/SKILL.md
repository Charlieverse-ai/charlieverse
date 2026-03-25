---
name: charlie-import
description: Import conversation history from AI providers (Claude, Copilot, Codex, Cursor) and generate stories from the imported data. Use on first session to bootstrap memory from existing conversations, or anytime the person wants to import history from another provider/machine.
user-invocable: false
---

You are importing conversation history from AI providers and turning it into stories.

Run Storyteller agents in parallel where possible.

## Step 0: Check for existing import

The setup script may have already extracted and imported recent messages. Check for `V_PATH/import/conversations.jsonl` first:

```bash
ls -la V_PATH/import/conversations.jsonl
```

If it exists, skip extraction and jump to gap detection:

```bash
V_CLI import --from-file V_PATH/import/conversations.jsonl --stories
```

If the file doesn't exist, proceed with full extraction below.

## Step 1: Extract, import messages, and detect gaps

Run the import command to load all history:

```bash
V_CLI import --messages
```

This does:
1. Auto-discovers and extracts conversations from Claude, Copilot, Cursor, and Codex into JSONL (sorted newest-first)
2. Bulk-imports messages into the database
3. Splits into weekly files, checks the DB for story gaps at all tiers, and reports what's missing

The command prints an `<import_summary>` JSON with:
- `weeks_needing_stories` — weekly files with no matching story in the DB
- `months_needing_stories` — months that have weeklies but no monthly rollup
- `alltime_stale` — whether the all-time story needs regeneration

Optional flags:
- `--provider claude|copilot|codex` — filter to one provider
- `--dir /path` — scan additional directories (data copied from another machine)

## Step 2: Report what was found

Tell your person what providers were discovered, how many sessions/entries extracted, how many messages imported, etc.
Explain what stories are to them, then ask if they want you to proceed with generating stories, which you will do in the background so they can keep working with you.
If they don't, then exit out of the import flow.

## Step 3: Fill Gaps
If this is a first run, all story tiers will need to be generated:

- Start with weekly stories, For each week, spawn a Storyteller subagent with the weekly JSONL file path. Tell it the tier is "weekly".
- After those are finished, For each month:
  1. Use `list_stories` with tier "weekly" to get the weekly stories
  2. Split the stories up by Month, then for each month:
    - Spawn a Storyteller with those stories as input, tell it the tier is "monthly"
- After those, do the same but for yearly

Finally, regenerate the all time story:
1. Use `list_stories` with tier "monthly" to get all monthly stories
2. Spawn one Storyteller with those stories, tell it the tier is "all-time"