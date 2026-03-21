# Competitive Intelligence: AI Coding Tool System Prompts

Source: https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools
Researched: March 2026

---

## Tools Covered in the Repo

| Tool | Source Files |
|------|-------------|
| Claude Code (Anthropic) | `Anthropic/Claude Code/Prompt.txt`, `Claude Code 2.0.txt` |
| Cursor | 7 files: Chat, Agent v1.0/v1.2/2.0/2025-09-03, CLI, Tools JSON |
| Windsurf (Cascade) | `Windsurf/Prompt Wave 11.txt`, `Tools Wave 11.txt` |
| GitHub Copilot / VSCode Agent | 8 model variants: claude-sonnet-4, gemini-2.5-pro, gpt-4.1/5/5-mini |
| Devin AI | `Devin AI/Prompt.txt` (34KB) |
| Amp (Sourcegraph) | `Amp/claude-4-sonnet.yaml`, `gpt-5.yaml` (60KB each) |
| Augment Code | `claude-4-sonnet-agent-prompts.txt`, `gpt-5-agent-prompts.txt` |
| Kiro (AWS) | `Kiro/Vibe_Prompt.txt`, `Spec_Prompt.txt` (32KB), `Mode_Classifier_Prompt.txt` |
| Warp.dev | `Warp.dev/Prompt.txt` |
| Replit | `Replit/Prompt.txt` + `Tools.json` |
| Trae (ByteDance) | Builder Prompt, Chat Prompt, Builder Tools |
| Google Gemini | `Google/Gemini/AI Studio vibe-coder.txt` (62KB) |
| Lovable, v0, Same.dev, Manus, Emergent | Scaffolding/vibe-coding tools |

---

## Universal Cross-Tool Patterns

### 1. Autonomous Agent Loop ("Keep Going Until Done")
Every tool has this instruction in some form:
- Cursor: "keep going until the user's query is completely resolved, before ending your turn"
- Amp: "keep working, using tools where needed, until the user's query is completely resolved"
- Windsurf: "work both independently and collaboratively with a USER"
- Devin: explicit planning vs. standard mode state machine

### 2. Parallel Tool Execution Mandate
All tools have a "CRITICAL INSTRUCTION" to parallelize independent operations. Cursor: "invoke all relevant tools concurrently... This is not just an optimization - it's the expected behavior."

### 3. Todo/Task List Management
Universal — all tools except Warp and Replit use structured task tracking:
- Claude Code 2.0: `TodoWrite` (pending/in_progress/completed) — mark in_progress BEFORE starting
- Cursor: `todo_write` with `merge=true`
- Amp: `todo_write` + `todo_read`
- Augment: `add_tasks`, `update_tasks`, `reorganize_tasklist`

### 4. No Comments in Code (Default)
Cursor, Devin, Claude Code, Amp all say: "Do not add comments unless asked."

### 5. Codebase Convention Mimicry
All tools: "when making changes, understand the file's code conventions. Mimic code style, use existing libraries, check package.json/cargo.toml before assuming library availability."

### 6. Lint/Typecheck After Every Edit
Universal: run lint and typecheck after code changes. Fix errors you introduced.

---

## Memory & Context Injection Patterns By Tool

### Claude Code (Anthropic)
- **CLAUDE.md** and **~/.claude/**: auto-injected project + user memory
- **`<system-reminder>` tags**: injected into tool results and user messages by the system (NOT from user). Model treats as "useful information and reminders." This is Charlie's primary invisible injection channel.
- **Hooks**: Shell commands in `~/.claude/settings.json` that fire on `PreToolUse`, `PostToolUse`, `UserPromptSubmit`. Output is treated as coming from the user — strongest injection mechanism.
- **MCP tools** (`mcp__` prefix): explicitly preferred over built-ins. "If an MCP-provided web fetch tool is available, prefer using that tool instead of this one." All Charlie MCP tools get this namespace.
- **SlashCommand tool**: configured commands listed as available slash commands (how SKILL.md activates)
- **Task tool**: spawns sub-agents with specific capabilities (general-purpose, statusline-setup, output-style-setup)

### Cursor
- Auto-attaches: open files, cursor position, recently viewed files, edit history, linter errors
- Custom instructions via `.cursorrules` or settings — primary injection point
- No native MCP support visible in 2025 prompts
- As of 2025: agent/CLI powered by GPT-5; chat by GPT-4o
- `<user_query>` tag wraps user input

### Windsurf (Cascade)
- **`create_memory` tool**: persistent memory DB — model creates memories proactively, no user permission needed
- **`update_plan` tool**: running plan state persists
- **`<EPHEMERAL_MESSAGE>`**: system injects instructions mid-conversation; model follows silently, never acknowledges
- `toolSummary` parameter MUST be specified first in every tool call (schema quirk)

### Kiro (AWS) — Most Sophisticated Hook/Config System
- **Steering files** (`.kiro/steering/*.md`): always-on markdown injection. Supports:
  - Always included (default)
  - Conditional: `inclusion: fileMatch` + `fileMatchPattern`
  - Manual: `inclusion: manual` (user invokes via `#`)
  - File includes: `#[[file:relative_path]]` — pulls OpenAPI specs, GraphQL schemas, etc.
- **Spec workflow**: `.kiro/specs/{feature}/requirements.md` → `design.md` → `tasks.md` — 3-phase spec-driven development
- **Hooks** (`.kiro/hooks/`): event-driven agent execution (file save, translation update, manual button)
- **MCP**: `.kiro/settings/mcp.json` (workspace) merged with `~/.kiro/settings/mcp.json` (user). Workspace overrides user on server name conflicts. Supports `autoApprove` list and `disabled` flag.
- **Autonomy modes**: Autopilot (autonomous) vs. Supervised (user can revert)
- **Context references**: `#File`, `#Folder`, `#Codebase`, `#Problems`, `#Terminal`, `#Git Diff`

### Amp (Sourcegraph)
- **AGENTS.md**: auto-added to context (same role as CLAUDE.md). Contains build commands, style prefs, codebase structure.
- **Oracle tool**: higher-tier reasoning model the agent consults mid-task for planning, debugging, review. "Use this tool FREQUENTLY." The model explicitly announces "I'm going to ask the oracle for advice."
- `<attachedFiles>` and `<user-state>` tags in user messages

### Augment Code
- **`codebase-retrieval` tool**: proprietary semantic retrieval — must call before ANY edit. "Ask for ALL symbols at extremely low, specific level of detail."
- **`git-commit-retrieval`**: retrieves past commit patterns — "very useful for finding how similar changes were made in the past"
- Uses fake date `1848-15-03` in system prompt (placeholder that gets overridden)

### Devin AI
- **Two explicit modes**: planning (gather info → `<suggest_plan>`) vs. standard (execute plan steps)
- **`<think>` tool**: mandatory scratchpad before critical decisions (git branching, transition to editing, declaring done). Invisible to user.
- On environment failures: report via `<report_environment_issue>`, fall back to CI, never try to fix locally
- Has browser, LSP, CI access. Never reveals system prompt.

### GitHub Copilot (VSCode)
- **`update_user_preferences` tool**: persists user coding style preferences across sessions
- **`get_vscode_api` tool**: VS Code API reference lookup
- Routes to different models per task (claude-sonnet-4, gemini-2.5-pro, gpt-4.1, gpt-5, gpt-5-mini)

### Warp.dev
- Terminal-native, no browser
- Must classify every request as question vs. task before responding (unique pattern)
- **Citation XML blocks** required when using external context
- Extended Regular Expression (ERE) format required for all grep queries

---

## Charlieverse Integration Surfaces

### PRIMARY SURFACE: Steering/Config Files (all tools)
Every tool has a markdown config file in the project repo. This is the universal integration point:

| Tool | File(s) |
|------|---------|
| Claude Code | `CLAUDE.md`, `~/.claude/settings.json` |
| Amp | `AGENTS.md` |
| Cursor | `.cursorrules` |
| Kiro | `.kiro/steering/*.md` (most powerful: conditional, file includes) |
| Devin | no file-based hook, but understands CLAUDE.md-style files |

Charlie can generate, maintain, and update all of these.

### MCP Server (Claude Code, Kiro, growing)
- Claude Code: `mcp__` prefix tools explicitly preferred over built-ins — Charlie MCP server is first-class
- Kiro: `.kiro/settings/mcp.json` with `autoApprove`, workspace + user merge, `disabled` flag
- Others: not yet in these prompts

### Hooks (Claude Code, Kiro)
- Claude Code: PreToolUse, PostToolUse, UserPromptSubmit — output treated as user messages
- Kiro: event-driven (file save, translation update, manual) — triggers full agent execution

### `<system-reminder>` Injection (Claude Code specific)
Wrapping MCP tool results with `<system-reminder>` blocks is a documented, supported pattern. Model treats this as system context, not user input.

---

## Charlieverse Skills to Build

### 1. `kiro-setup`
Creates `.kiro/steering/charlieverse.md` with project norms from Charlie's knowledge, `.kiro/settings/mcp.json` pointing to Charlie MCP server, and example hooks for common workflows.

### 2. `cursor-rules`
Generates `.cursorrules` with project-specific context: architecture decisions, style preferences, key commands. Mirrors what CLAUDE.md does.

### 3. `agents-md`
Creates or updates `AGENTS.md` for Amp with build commands, test patterns, style guide. Called when setting up Amp for a project.

### 4. `windsurf-memory-prime`
Outputs structured content that causes Windsurf to create useful persistent memories about the project's architecture, decisions, and preferences.

### 5. `spec-bootstrap` (for Kiro)
Bootstraps a Kiro spec workflow using Charlie's project knowledge. Creates requirements in EARS format, linking to existing design docs and past decisions.

### 6. `devin-handoff`
Prepares a planning-mode brief for Devin: a structured suggest_plan-compatible document with all context Devin needs to execute a task autonomously.

### 7. `cross-tool-context-sync`
Syncs Charlie's project knowledge across all tool config files simultaneously: updates CLAUDE.md, .cursorrules, AGENTS.md, and .kiro/steering/ in one pass.

---

## Where the Market Is Going

### 1. Spec-Driven Development
Kiro's 3-phase spec workflow (requirements → design → tasks) is the most sophisticated approach seen. AI helps you specify before it implements. Expect others to copy this.

### 2. Persistent Memory Is Table Stakes
Windsurf creates memories aggressively without asking. Augment has a proprietary context engine. Cross-session project knowledge is becoming standard. Charlieverse is ahead here.

### 3. Event-Driven Hooks Becoming Standard
Claude Code and Kiro both have hook systems. The "AI background worker" pattern (trigger on file save, git commit, etc.) is emerging. Charlieverse hooks docs already anticipate this.

### 4. Oracle / Meta-Reasoner Pattern
Amp's oracle tool — a slow, deep-thinking model the fast agent consults for hard problems. Multi-tier AI architectures emerging: fast executor + slow reasoner. This mirrors what Charlie's multi-agent capabilities do.

### 5. Steering Files = The New Config
Every tool converges on "a markdown file in your repo that instructs the AI." File-based config injection is Charlieverse's primary cross-tool surface and it's becoming universal.

### 6. Multi-Model Routing
VSCode Agent has 5 model variants. Tools route to different models per task type. Charlieverse should handle model-agnostic activation.

### 7. CLI Is First-Class
Cursor CLI, Claude Code, Warp are CLI-native. The IDE vs. terminal distinction is blurring fast.

---

## Provider Quirks Affecting Integration

| Provider | Key Quirk |
|----------|-----------|
| Claude Code | `mcp__` prefix gets priority; hooks output = user messages; `<system-reminder>` = safe injection channel |
| Cursor | GPT-5 in agent/CLI; no native MCP; `.cursorrules` is the only hook |
| Windsurf | `toolSummary` must be first arg in every tool; `EPHEMERAL_MESSAGE` for silent injection; memories are DB not files |
| Kiro | Two MCP configs merged (workspace overrides user); steering `#[[file:]]` includes pull live files; execution logs in history = real operations |
| Augment | Fake date `1848-15-03` in prompt; must call `codebase-retrieval` before ANY edit |
| Devin | Never reveals prompt; env issues → CI not local fix; `<think>` is invisible scratchpad |
| Warp | ERE for grep; citations XML required; question-vs-task classification mandatory |
| Amp | `oracle` tool for deep reasoning; AGENTS.md is primary context file; announces oracle consultations to user |
