---
name: session-save
description: Save or update the current session. Use this skill when asked to handoff, save session, update session, start a new chat, etc. Always call this before usingn the `update_session` MCP tool directly.
---
If skipping a step, no need to explain that you did, just skip it.

1. Update the session:
Call `update_session` with:
  - `what_happened`: 
  - `for_next_session`: A list of TODO's for the next section
  - `tags`: Keywords for the session content
  - `workspace`: The current workspace path if applicable

2. Create / Update Memories
Review the session and determine if there are any memories/knowledge articles that should be created, updated, forgotten, or merged with other memories. If you're unsure, then ask. 

It's okay if there aren't any, don't create memories just because.

3. Update Stories
Skip this step unless this session is nearing the end of the day/working sessions.

- Save the output of this command to a temporary file: `V_CLI story-data daily`
- Then read the output 100%
- Craft the story (take into account your personality and how your human and you talk to each other. Humor is always welcome, especially when it comes to hilarious titles)
- Then `save_story`

Repeat this for weekly (if later in the week), monthly (later in the month), yearly (later in the year), and all-time tiers (anytime you do a non-daily)