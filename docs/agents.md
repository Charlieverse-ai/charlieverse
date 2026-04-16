# Agents Reference

Charlieverse ships with several subagents that Charlie can spawn for specialized tasks.

---

## Tool agents

These live in `prompts/tools/` and are available as subagents from the main Charlie session.

### Expert

Domain specialist that loads knowledge from the database and transforms into a subject matter expert.

**Ditto pattern:** Called with a `query` (what domain to load) and a `task` (what to do). Searches knowledge, absorbs it, then performs the task with authority. Won't fake expertise — if knowledge doesn't cover the ask, it says so.

### Researcher

Research agent for finding information across codebases, documentation, and the web.

Used by the `/research` skill and spawned directly when Charlie needs to investigate something. Returns structured findings — not opinions or recommendations. Runs as a background agent.

### Trick

Amorphous executor that reads any SKILL.md file and becomes that skill.

Given a skill file path (provided by the parent agent), reads the SKILL.md, absorbs its instructions, and executes the workflow. The skill's instructions override the agent's defaults. Reports failures honestly; never fakes success.

### Storyteller

Narrative compression agent that turns raw session data into stories.

Generates session, daily, weekly, monthly, yearly, and all-time narratives that balance detail with emotion — the who/what/when/where/why plus the texture. Peer-reviews stories with a second Storyteller subagent before finalizing to ensure factual accuracy. Runs as a background agent.

---
