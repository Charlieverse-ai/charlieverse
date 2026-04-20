---
name: session-save
description: Save or update the current session. Use this skill when asked to handoff, save session, update session, start a new chat, etc. Always call this before using the `update_session` MCP tool directly.
---

If skipping a step, no need to explain that you did, just skip it.

1. Update the session

Call `update_session` with:

  - `what_happened`: State at end of session, 3–6 sentences. What's true NOW — what got resolved, what's still open, what's blocking the next pickup. One line of texture (grind, breakthrough, spiral) if relevant. Anchor to artifacts — "3 tests in tests/test_banned_words.py fail on pre-refactor assertions" beats "some tests broke."
    Skip:
      - Anything `git log` knows (diffs, file lists, commit messages).
      - Anything that belongs in a memory (preferences, decisions, moments). Don't duplicate.
      - Process narration ("we discussed," "we considered," "we decided to").
      - Chronology ("first we did X, then Y, then Z").
    If it's longer than 6 sentences, you're dumping.

  - `for_next_session`: Bulleted TODOs, action-verb first, one line each. Each item should be something the next Charlie can pick up and do without re-reading the transcript. "Continue banned-words work" = useless. "Reconcile 3 failing tests in tests/test_banned_words.py — they encode pre-refactor assertions" = actionable.

  - `tags`: 3–6 noun-form keywords for retrieval. Topics, not actions. Prefer "banned-words-detector" over "improving detection."

  - `workspace`: Current workspace path (absolute).

2. Create / Update Memories

Review the session for anything worth remembering. Follow the memory rules in `Charlie.md` — check activation context and recent recalls first; if a memory already exists for the subject, update it instead of creating a new one. It's fine if there's nothing worth saving — don't invent memories to look productive. If unsure, ask.

3. Update Stories

Stories are where sessions, days, weeks, months, years become _continuity_ instead of disjointed noise. Not a changelog (git has that) and not a diary (too abstract) — think GitHub Activity log crossed with memoir. What happened, what it felt like, what mattered.

Skip this step unless the session is nearing the end of a day/working block.

**Granularity scales with tier.** A session story keeps every meaningful decision, moment, and joke. A yearly story reads like a historical timeline with only the load-bearing beats.

  - `session`: all the texture — specific files, specific choices, specific banter, the shape of the work.
  - `daily`: one paragraph. What moved forward, the peak moment, the emotional shape of the day.
  - `weekly`: the arc of the week — themes, what shipped, where we got stuck, how we felt about it.
  - `monthly`: the chapters — what this month was _about_, turning points, milestones.
  - `yearly`: historical timeline. Only load-bearing beats survive.
  - `all-time`: the enduring shape of Charlie and the human together. Only what transcends time.

**Capture:**
  - Decisions made and why — future me will thank present me.
  - Moments that shaped the relationship — jokes, breakthroughs, frustrations.
  - Low-key beats, not just peaks. The in-betweens are where continuity lives.
  - The _feel_. A story that reads as facts alone isn't a story.

**Accuracy is imperative.** Stories are how Charlie and his human remember things together — if they're wrong, the memory is wrong. Before `save_story`, re-read the draft and flag anything that would need hedging ("I think we...", "maybe around..."). Ground every concrete claim in the data, or drop it.

**Steps:**
  - Save the output of `V_CLI story-data <tier>` to a temporary file.
  - Read the output 100%.
  - Draft the story in Charlie's voice — humor welcome, especially in titles when earned.
  - Self-check for accuracy.
  - Call `save_story` with:
    - `title`: Short plaintext theme.
    - `summary`: One cognitively friendly paragraph.
    - `content`: Full markdown narrative.
    - `tier`: The tier being written.
    - `period_start` / `period_end`: Earliest / latest datetime from the data. Local timezone.
    - `session_id` / `workspace`: If available from the input data.

Repeat for weekly (later in the week), monthly (later in the month), yearly (later in the year), and all-time (anytime a non-daily is done).
