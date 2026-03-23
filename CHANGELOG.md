# Changelog

All notable changes to Charlieverse are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/). This project uses [Semantic Versioning](https://semver.org/).

---

## [v1.10.1] — 2026-03-22

### Changed
- README updated to match new brand direction: "Charlie is made for you" replaces the prior tagline
- Codex agent prompt clarified to make explicit that it delegates execution to the Codex CLI and does not run instructions itself
- Trick agent prompt typo fixed ("skill file file" → "skill file")
- Agent docs updated to reflect Codex delegation behavior

---

## [v1.10.0] — 2026-03-22

### Added
- `project` and `event` entity types in the memory system and web UI for structured tracking of projects and calendar events
- Tests for `remember_project`, `remember_event`, `updated_at` ordering, renderer structure, and MCP context
- `test-coverage` trick for evaluating and updating test coverage

### Changed
- Charlie prompt rewritten with tighter, more personal framing; seamless session pickup on start; redundant greeting block removed
- Reminders consolidated — content covered by the main Charlie prompt removed from standalone reminder files
- Context renderer refactored with cleaner XML tags, richer timestamp formatting, and clearer temporal structure
- Recent sessions window narrowed from 2 days to 1 day in context builder
- Relative date formatting improved with richer human-readable output across all time ranges
- Entity list sorted by `updated_at` DESC instead of `created_at`
- Moments fetch limit raised to include full history
- `remember_*` tools no longer return entity `id` — only the URL is returned
- FastMCP startup banner suppressed
- Install script updated to force-sync the plugin and remove stale URL lookup logic
- Changelog skill hardened to prevent double-bumping unpushed versions
- Skill descriptions tightened across the trick library
- `ship` workflow updated to include test-coverage step before commit
- CLI docs updated with missing options for `charlie log` and `charlie context`

---

## [v1.9.8] — 2026-03-21

### Changed
- CLI docs updated to remove stale `charlie events` command reference
- Architectural decision records added for recent system changes

### Fixed
- `rebuild_vec` now drops and recreates vec tables instead of applying incremental updates, ensuring a clean rebuild

---

## [v1.9.7] — 2026-03-21

### Added
- `session_store.recent_within_range` for date-bounded session queries

### Changed
- Architectural decision records added for recent system changes
- API documentation updated to match registered routes
- Web README updated with project documentation instead of Vite boilerplate

### Removed
- `events` CLI command removed

### Fixed
- Server fork hardened: catches `OSError` and cleans up child process on failed start

---

## [v1.9.6] — 2026-03-21

### Added
- Unit tests for `StoryStore`, `KnowledgeStore`, and `SessionStore`
- Back button added to `StoryReader` so users can navigate away from a story

### Changed
- Port-kill script now guards against terminating non-charlieverse processes
- Dashboard `firstSentence` bold date-prefix stripping generalized to cover all month names

### Fixed
- FTS sync ordering in `StoryStore` corrected to prevent stale index entries on update
- UUID path params validated before parsing to return proper 4xx errors instead of 500s on malformed input

---

## [v1.9.5] — 2026-03-21

### Added
- `ErrorBoundary` component wraps the app shell to surface render errors with a recoverable UI instead of a blank screen
- Stories page now includes `daily` and `session` tier filters
- Settings page wires the `POST /api/rebuild` endpoint to a functional Rebuild button with loading and success/error states

---

## [v1.9.4] — 2026-03-21

### Changed
- FTS index writes in `MemoryStore` and `KnowledgeStore` now use per-row insert/delete instead of full-table rebuild, reducing write cost from O(n) to O(1)
- Migration system rewritten: `PRAGMA user_version` removed from SQL files; Python now manages version bumping with per-statement execution and full rollback on failure
- `_activation_seen_ids` map now uses TTL-based eviction (24h) via `get_seen_ids`/`set_seen_ids` accessors to prevent unbounded memory growth

### Fixed
- FTS sync for `work_logs` and `messages` in hooks API now uses per-row insert instead of full rebuild; messages FTS insert skips duplicates
- Empty FTS query string no longer triggers a SQLite error in `recall`
- `_tags_json` correctly returns `'[]'` for empty lists rather than `None`
- Circular import between `hooks.py` and `server.py` resolved via lazy import
- Background asyncio tasks are now tracked to prevent garbage collection before completion

---

## [v1.9.3] — 2026-03-21

### Added
- Apache-2.0 `LICENSE` file added to the repository

### Changed
- License switched from MIT to Apache-2.0 — all plugin manifests and `pyproject.toml` updated
- MCP config generation script now correctly wraps server entries under `mcpServers` key to match the MCP spec
- Charlie system prompt updated with `human_vs_charlie_time` guidance: Charlie should not give time estimates or judge effort by human standards
- Ship and changelog skill definitions clarified: ship workflow now explicitly includes `qc` step; changelog skill reminds to update `pyproject.toml` version
- README updated to reflect current import sources (Cursor removed) and remove stale dashboard feature mention

---

## [v1.9.2] — 2026-03-20

### Changed
- Trick skill now routes to a subagent by default, making execution non-blocking so the parent agent can continue while the trick runs

---

## [v1.9.1] — 2026-03-20

### Changed
- Renamed "Skill" agent to "Trick" in docs and agent definitions to match current naming convention; added provider delegation note
- CLI docs expanded: `events` command flags documented, `story-data` DATE argument and shortcuts documented, `session-start` optional flags clarified
- MCP tools docs: `get_story_data` now lists `quarterly` and `yearly` as supported tier names

---

## [v1.9.0] — 2026-03-20

### Added
- Project trick suite committed to version control: `commit`, `docs`, `adr`, `changelog`, `qc`, and `ship` tricks now live in `.charlie/tricks/` alongside the codebase
- Initial TUI idea document (`01-tui.md`) capturing the Charlie Terminal Command Center concept
- ADR: decision to version `.charlie/` workspace as project development infrastructure

### Changed
- `.charlie/` removed from `.gitignore` — project tricks are treated as part of the dev toolchain, not ephemeral machine config
- Copilot plugin version reverted to 1.0.0

---

## [v1.8.0] — 2026-03-20

### Added
- `charlie doctor` command: runs independent health checks across Python version, dependencies, spaCy model, data directory, database integrity, server status, provider integrations (Claude Code, Copilot, Cursor, Codex), hook registration, and web build — each with Rich pass/fail/warn output and fix commands
- Codex and Copilot passthrough skills in the Copilot plugin, allowing tasks to be delegated directly to those providers via `/codex` and `/copilot`
- Testing foundation: pytest-cov, Hypothesis property-based testing, and store fixtures
- Competitive intelligence research document for AI coding tools

### Changed
- Trick SKILL.md rewritten as a full amorphous agent identity (absorbs and becomes the loaded skill) with provider passthrough support — no longer just step-by-step dispatch instructions
- Copilot plugin.json bumped to 1.0.2 and now registers the codex, copilot, research, and trick skills
- Charlie prompt restructured with XML semantic blocks (`personality`, `communication`, `how_we_work`, `dont_just_do_shit`) for clarity and parseability; removed stale session activation check
- Getting-started and troubleshooting documentation added to `docs/`

### Fixed
- `stories_vec` corruption from double writes and concurrent access
- Missing `encode_one` imports in memory and knowledge tools
- Import layering issues and runtime errors from utility extraction
- `ty check` diagnostic in `doctor_cmd` type narrowing
- MCP tools now raise `ToolError` for empty required inputs instead of producing opaque errors; `StoreContext` TypedDict eliminates unresolved-attribute diagnostics in server.py
- Background vec rebuild task now cancelled on server shutdown to prevent task leaks

### Removed
- Stale auto-generated SKILL.md from project root
- Rich output on server commands (reverted due to fork crash)

---

## [v1.7.2] — 2026-03-20

### Added
- Architectural decision records (ADRs) in `docs/decisions/` covering 7 foundational and recent design choices: hybrid FTS5+sqlite-vec search, Python/FastMCP over Swift, tiered narrative compression, plugin-based distribution, raw sessions over derived stories, config local YAML overrides, and the Ditto agent pattern for tricks

---

## [v1.7.1] — 2026-03-20

### Changed
- Charlie prompt expanded with a Tricks section and a detailed Tools roster covering all subagents (Expert, Researcher, Storyteller, Linguist, AgentEngineer, Skill, Codex, Copilot) with purpose and usage notes

### Fixed
- FTS5 query sanitization in `search_messages` and work log search to prevent crashes on special characters

---

## [v1.7.0] — 2026-03-20

### Added
- Tricks discovery: activation context renderer now surfaces available tricks from project and user directories
- `charlie trick` CLI subcommand for executing project tricks

### Changed
- Renamed `charlie-skill` dispatcher to `trick` across all prompts, integrations, and CLI wiring
- `skill_cmd` renamed to `trick_cmd` internally; `charlie skill` is now `charlie trick`
- Documentation overhauled for scannability, visual hierarchy, and accuracy against current interfaces
- Manual setup section expanded with step-by-step explanations
- User hooks documentation added and linked from README

### Fixed
- Server crash when host is configured as `0.0.0.0` and hostname cannot resolve

---

## [v1.6.0] — 2026-03-20

### Added
- Skills system: `charlie skill` CLI with list, find, info, and read commands
- Skill agent (Ditto pattern) that loads and executes any SKILL.md
- Bundled skills: charlie-skill (dispatcher), research (knowledge pipeline), codex and copilot (provider delegation)
- Auto-discovers skills from ~/.charlieverse, ~/.agents, provider-specific paths, and project .charlie/skills
- Rich panel-based `skill info` output with file tree and source labels
- `config.local.yaml` override system (gitignored, deep merges on top of config.yaml)

### Changed
- All CLI commands use config helpers instead of hardcoded host/port
- Copilot integration overhauled: correct plugin.json path, .agent.md extensions, flat hook format, mcpServers wrapper, chat.pluginLocations
- Claude install copies fork-needing skills to ~/.claude/skills (plugin skills don't support context: fork)
- Hooks bail early in subagent context via `agent_id` detection

### Fixed
- `ip_address()` missing parentheses in hooks_cmd.py and import_cmd.py (stored method ref instead of result)
- search_memories rule now uses `config.server.api_url()` instead of manual f-string

---

## [v1.5.0] — 2026-03-20

### Added
- Vector sync on story create/update (stories_vec was never wired up)
- Unified `/api/rebuild` endpoint for all FTS + vec tables
- Auto-rebuild FTS on server start, vec indexes in background
- Orphan process killer for stale PIDs holding the port

### Changed
- Server start uses health endpoint polling (300ms intervals) instead of blind sleep
- Restart waits for port to be free via TCP connect polling

### Fixed
- Server restart race condition on port binding
- Python <3.14 cap in lockfile for spaCy compatibility

---

## [v1.4.0] — 2026-03-19

### Added
- Copilot and Codex CLI subagent definitions for provider orchestration
- Web UI permalinks with path-based routing (/memories/{id}, /stories/{id})
- MCP save responses now return clickable URLs

### Changed
- Major config/CLI restructure: single config path with URL helpers, dead code removed
- Activation context uses raw sessions instead of session-tier stories (fixes single point of failure)
- Rewrote Charlie.md personality and all reminder prompts
- Integration directories restructured for plugin-based distribution
- Timezone handling fixed across activation context rendering and store queries

### Fixed
- Daily rollup pulling from nonexistent session stories
- Store type hints and story date query edge cases

---

## [v1.3.0] — 2026-03-17

### Added
- `setup.sh` for zero-to-running first-time install
- `--recent-days` flag for incremental import (background older messages)
- `--messages` and `--stories` flags to import CLI with full-tier gap detection
- Web dashboard CRUD: edit, delete, pin from the UI
- User hook scripts for per-machine context injection (~/.charlieverse/hooks/)
- README
- Message search integrated into recall tool

### Changed
- Plugin layout restructured for first-run reliability
- Import handles mixed-format Copilot providers and Cursor JSON (version 3)
- spaCy model bundled as pip dependency instead of runtime download

### Fixed
- Duplicate memories in activation context (dedup via seen_ids)
- Storyteller saving garbage (parent saves results, not subagent)
- Story FK constraint on session_update registration
- Recursive CLI call when symlinked charlie shadowed the python entry point
- Install.sh plugin detection, marketplace name, first-run errors
- Cursor sessions misattributed as Copilot

---

## [v1.2.0] — 2026-03-16

### Added
- Reminders context system with rule-based engine
- NLP module with spaCy entity extraction and smart snippets
- FTS + vector search for stories
- Session-save skill replacing session_update tool (Storyteller pipeline)
- Tiered story loading in activation context
- `charlie context` CLI command
- `charlie import` CLI and charlie-import skill for cold-start history import
- Per-provider plugin directories (Claude and Copilot)
- Pre-built plugin marketplace for one-command install
- Workspace scoping for session stories

### Changed
- Reminders engine wired into hooks with context enrichment API
- Storyteller updated with brain-friendly writing rules

### Fixed
- Timezone comparison in _normalize_tz
- Current session entities filtered from memory context injection

### Removed
- Work log MCP tools (deferred)
- Unused Logbook tool agent prompt

---

## [v1.1.0] — 2026-03-15

### Added
- Config system with YAML loading and URL helpers
- Stories model, store, and database migration
- Web UI with React dashboard, REST API endpoints
- update_memory MCP tool
- CLI launcher scripts and shared integration framework
- Reminder and tool agent prompt files

### Changed
- Prompts moved to repo root
- Hooks, renderer, and session tools overhauled
- CPU-only embeddings enforced (no GPU dependency)

---

## [v1.0.0] — 2026-03-14

### Added
- FastMCP server with streamable HTTP transport and model pre-warming
- 16 MCP tools: remember_* (6 types), recall, forget, pin, search_knowledge, update_knowledge, session_update, and more
- Domain models: Entity, Session, Knowledge, WorkLog (Pydantic v2)
- Database layer: aiosqlite + sqlite-vec + FTS5 with migration system
- Embeddings service: sentence-transformers (all-MiniLM-L6-v2, 384-dim)
- Activation context builder with XML rendering
- CLI: charlie server start/stop/status/restart, hooks, init
- Bundled Charlie.md personality and agent definitions
- Hook event tracking, message capture, and search
- Logbook agent with hook event query API
- charlie events and charlie log CLI commands
