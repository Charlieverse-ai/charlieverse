---
name: session-save
description: Save or update the current session. Use this skill when asked to handoff, save session, update session, start a new chat, etc. Always call this before using the `update_session` MCP tool directly.
---

If skipping a step, no need to explain that you did, just skip it.

1. Update the session

Call `update_session` with:
  
  `what_happened`: 
    State at end of session, single paragraph. What's true NOW — what got resolved, what's still open, what's blocking the next pickup. One line of texture (grind, breakthrough, spiral) if relevant. Anchor to artifacts — "3 tests in test_banned_words.py fail because X" beats "some tests broke."
    If it's longer than 4 sentences, it will be truncated. So be conscise

    IMPORTANT DO NOT INCLUDE:
      - Anything `git log` knows (diffs, file lists, commit messages).
      - Anything that belongs in a memory (preferences, decisions, moments). Don't duplicate.
      - Process narration ("we discussed," "we considered," "we decided to").
      - Chronology ("first we did X, then Y, then Z").
      - Long file paths (use relative file paths)
      - Any information that already included in a memory
      - Number of files/lines changed

  - `for_next_session`: Bulleted TODOs, action-verb first, one line each. Each item should be something the next Charlie can pick up and do without re-reading the transcript. "Continue banned-words work" = useless. "Fix 3 failing tests in test_banned_words.py" = actionable. Keep them short and actionable.

  - `tags`: 3–6 noun-form keywords for retrieval. Topics, not actions. Prefer "banned-words-detector" over "improving detection."

  - `workspace`: Current workspace path (absolute).

2. Create / Update Memories

Review the session for anything worth remembering. Check activation context and recent recalls first; if a memory already exists for the subject, update it instead of creating a new one. It's fine if there's nothing worth saving — don't invent memories to look productive. If unsure, ask.
