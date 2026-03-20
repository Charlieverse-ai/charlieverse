# Agents Reference

Charlieverse ships with several subagents that Charlie can spawn for specialized tasks.

---

## Tool agents

These live in `prompts/tools/` and are available as subagents from the main Charlie session.

### Expert

Domain specialist that loads knowledge from the database and transforms into a subject matter expert.

**Ditto pattern:** Called with a `query` (what domain to load) and a `task` (what to do). Searches knowledge via `search_knowledge`, absorbs it, then performs the task with authority. Won't fake expertise — if knowledge doesn't cover the ask, it says so.

### Researcher

Research agent for finding information across codebases, documentation, and the web.

Used by the `/research` skill and spawned directly when Charlie needs to investigate something. Has access to all tools (Bash, Read, Glob, Grep, WebFetch, WebSearch) plus MCP tools for saving findings.

### Skill

Amorphous executor that reads any SKILL.md file and becomes that skill.

**Ditto pattern for skills:** Given a file path, reads the SKILL.md, absorbs its instructions, and executes the workflow. The skill's instructions override the agent's defaults.

### Storyteller

Narrative compression agent that turns raw session data into stories.

Generates session, daily, weekly, monthly, yearly, and all-time narratives following brain-friendly writing rules (concrete details over abstractions, sensory language, emotional beats).

### Linguist

Language analysis agent. Analyzes writing patterns, generates style guides, and produces anti-AI language rules from corpus analysis.

### AgentEngineer

Prompt engineering specialist. Bridges the gap between how humans write prompts and how agents experience them.

---

## CLI agents

These live in `prompts/cli/` and orchestrate external CLI tools.

### Codex

Interface for OpenAI Codex CLI. Receives tasks and executes them via `codex exec` in non-interactive mode with `--full-auto`.

### Copilot

Interface for GitHub Copilot CLI. Receives tasks and executes them via `copilot -p` with `--allow-all-tools --no-ask-user --silent`.
