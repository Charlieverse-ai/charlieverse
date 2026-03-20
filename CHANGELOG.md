# Changelog

All notable changes to Charlieverse are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/). This project uses [Semantic Versioning](https://semver.org/).

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
