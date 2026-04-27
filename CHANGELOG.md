# Changelog

All notable changes to Charlieverse are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/). This project uses [Semantic Versioning](https://semver.org/).

---

## [v1.14.7] — 2026-04-27

### Added
- **Escalating session-save reminder.** `SaveSessionRule` now fires after 15 turns since the last save and escalates in tone each ignored turn — polite nudge at turn 0 through snarky dog-explosion humor through a tombstone epitaph at turn 14. A one-time celebration fires after each successful save. Replaces the flat 30-minute wall-clock trigger.
- **Reactive banned-words detector.** New `BannedWordsDetectorRule` fires with `VERY_IMPORTANT` priority when the previous assistant turn contained a banned phrase, rendering specific matches via the new `banned-words-violation.md` template. Previously only a proactive general reminder existed.
- **`charlieverse/helpers/text.py` shared text-cleaning module.** Consolidates `strip_noise`, `is_ignored`, `clean_text`, `strip_markdown`, `strip_punctuation`, and `extract_stuff` from scattered locations into a single canonical helpers module. `nlp/markdown.py` is now a re-export shim.
- **`PromptSubmitContext` model.** New response model (`server/responses/prompt_submit_delta.py`) for the `GET /api/session/{id}/prompt_submit` endpoint — includes message counts, last assistant message content and age, seen memory IDs, and session timing.
- **`Seconds` branded float type** (`types/time.py`) for type-safe duration values throughout the server layer.
- **`typo-check` trick.** New Charlie trick for scanning prose, docstrings, and docs for typos, grammar, punctuation/capitalization, and banned-phrase voice slips before shipping.
- **`banned_words` CLI accepts a file path.** The `python -m charlieverse.helpers.banned_words` entry point now accepts a file path as its first argument and reads the file contents, rather than always joining all argv tokens as raw text.
- **Test coverage for new and changed modules.** Tests added across `test_text_helpers.py`, `test_save_session_escalation.py`, and `test_renderer.py` (message truncation, pinned wrapper, pinned-type tags, entity id attribute).

### Changed
- **`relative_time_seconds` returns fractional units.** "2.5 hours" instead of "2 hours, 30 minutes". Accepts `float | Seconds`. Pluralization based on rounded value.
- **Entity ranker drops FTS/vector dual-source relevance scoring.** The min-score filter was cutting relevant-but-older memories. Ranking now uses a constant floor plus recency decay (half-life 14 days) — all results surface, ordered by recency.
- **`truncate()` and `MAX_*` constants moved to `summaries.py`** and shared across the MCP layer instead of being private to `mcp.py`.
- **`extract_entities` renamed to `extract_keywords`**, accepts pre-cleaned `CleanedText` directly — callers are responsible for pre-cleaning.
- **`SearchMemoriesRule` renders XML-tagged entity elements** instead of plain text lines: `<{type} date="{age}">{content}</{type}>`.
- **`TemporalGapRule` removed.** Superseded by `TemporalContextRule`.
- **`annoy-charlie.md` template** replaces `save-reminder.md` and `temporal-gap.md` for session-save nags.
- **Activation context drops auto-loaded moments.** Moments no longer fetch on every session-start; they must be explicitly pinned to appear in activation context. Reduces token overhead on cold-start sessions.
- **Activation context: `<pinned>` wrapper and `pinned-{type}` tags.** Pinned entities and moments now render inside a `<pinned>` block with `pinned-{type}` tag names (e.g., `<pinned-decision>`). Each entity element includes an `id` attribute.
- **Recent messages truncated at 300 characters.** Long messages in the activation context `<recent_messages>` block are now capped at 300 chars with an ellipsis instead of rendering in full.
- **Recent sessions limit reduced from 5 to 3.** Trims activation context size for sessions with long history.
- **NLP enrichment: multi-word entities split into tokens.** "Emily Laguna" becomes `["Emily", "Laguna"]` for broader memory recall. `ORG` and `DATE` entity labels removed as too noisy.
- **Context enrichment guards long texts.** `POST /api/context/enrich` returns early for texts over 1,000 characters, and keywords are capped at 10 per call.
- **`EntitySummary.from_memory` strips markdown before truncating.** Prevents truncation mid-markdown-syntax; plain text length is what counts.
- **`PermalinkResponse` reshaped from `ToolResult` to plain Pydantic model.** Removes the MCP output-validation errors that were surfacing when write tools returned `ToolResult` directly.
- **MCP write tools populate `structured_content`.** Fixes output-validation errors in FastMCP's strict mode; write-tool responses now include both `content` and `structured_content` fields.
- **`session-save` skill tightened.** `what_happened` is now a single paragraph (4 sentences max), prohibiting long file paths, duplicate memory content, and file/line counts. `for_next_session` items must be short and directly actionable.
- **Memory content cap clarified in `Charlie.md`.** 300 characters or less; longer content will be truncated. Pinning guidance updated to suggest rather than gatekeep.

### Decisions Recorded
- ADR: Save session reminder switched to escalating turn-based nag
- ADR: Text helpers extracted to shared module
- ADR: Reactive banned-words detector added as separate reminder rule
- ADR: Memory recall response flattened from grouped to entity list
- ADR: relative_time_seconds returns fractional units
- ADR: Moments dropped from activation context — auto-loading all moments added noise without reliable signal
- ADR: Multi-word NLP entities split into tokens for broader memory recall

---

## [v1.14.6] — 2026-04-20

### Added
- **Escalating session-save reminder.** `SaveSessionRule` now fires after 15 turns since the last save and escalates in tone each ignored turn — polite nudge at turn 0 through snarky dog-explosion humor through a tombstone epitaph at turn 14. A one-time celebration fires after each successful save. Replaces the flat 30-minute wall-clock trigger.
- **Reactive banned-words detector.** New `BannedWordsDetectorRule` fires with `VERY_IMPORTANT` priority when the previous assistant turn contained a banned phrase, rendering specific matches via the new `banned-words-violation.md` template. Previously only a proactive general reminder existed.
- **`charlieverse/helpers/text.py` shared text-cleaning module.** Consolidates `strip_noise`, `is_ignored`, `clean_text`, `strip_markdown`, `strip_punctuation`, and `extract_stuff` from scattered locations into a single canonical helpers module. `nlp/markdown.py` is now a re-export shim.
- **`PromptSubmitContext` model.** New response model (`server/responses/prompt_submit_delta.py`) for the `GET /api/session/{id}/prompt_submit` endpoint — includes message counts, last assistant message content and age, seen memory IDs, and session timing.
- **`Seconds` branded float type** (`types/time.py`) for type-safe duration values throughout the server layer.
- **Test coverage for new modules.** 39 tests added across `test_text_helpers.py` (26 tests) and `test_save_session_escalation.py` (13 tests).

### Changed
- **`relative_time_seconds` returns fractional units.** "2.5 hours" instead of "2 hours, 30 minutes". Accepts `float | Seconds`. Pluralization based on rounded value.
- **Entity ranker drops FTS/vector dual-source relevance scoring.** The min-score filter was cutting relevant-but-older memories. Ranking now uses a constant floor plus recency decay (half-life 14 days) — all results surface, ordered by recency.
- **`truncate()` and `MAX_*` constants moved to `summaries.py`** and shared across the MCP layer instead of being private to `mcp.py`.
- **`extract_entities` renamed to `extract_keywords`**, accepts pre-cleaned `CleanedText` directly — callers are responsible for pre-cleaning.
- **`SearchMemoriesRule` renders XML-tagged entity elements** instead of plain text lines: `<{type} date="{age}">{content}</{type}>`.
- **`TemporalGapRule` removed.** Superseded by `TemporalContextRule`.
- **`annoy-charlie.md` template** replaces `save-reminder.md` and `temporal-gap.md` for session-save nags.

### Decisions Recorded
- ADR: Save session reminder switched to escalating turn-based nag
- ADR: Text helpers extracted to shared module
- ADR: Reactive banned-words detector added as separate reminder rule
- ADR: Memory recall response flattened from grouped to entity list
- ADR: relative_time_seconds returns fractional units

---

## [v1.14.5] — 2026-04-16

### Added
- **Dashboard rollup drill-down.** Clicking a weekly story now opens a `WeekReader` showing the daily stories for that Mon–Sun period, stacked with per-day headers. Clicking a monthly story opens a `MonthReader` listing the weekly stories for that month — each weekly there feeds back into the same weekly→daily flow. Both readers fall back to the rollup Markdown when the lower-tier query is empty (common for older weeks/months that only got a rollup).
- **Current-week surface on the Dashboard.** Daily stories for the live Monday–Sunday window render ahead of the chapter timeline as a "This Week" block, so the in-progress week is visible before a weekly rollup exists. The same dailies are excluded from the chapter timeline below to avoid duplication.
- **`GET /api/stories` period filter.** New optional `period_start` and `period_end` query params (YYYY-MM-DD, inclusive) delegate to `StoryStore.find_by_period` for timezone-aware overlap matching. When unset, behavior is unchanged (tier + limit).

### Changed
- **Context-enrich stopped fanning out into knowledge.** `POST /api/context/enrich` and the `SearchMemoriesRule` reminder rule previously returned both memory and knowledge matches per extracted entity. Knowledge is already pinned into activation context and was duplicating surface area with lower signal — both paths now return memories only. `KnowledgeStore` dropped from `enrich_context`'s import surface; snippet extraction ceiling trimmed 800 → 500 chars.
- **Voice enforcement upgraded.** `SystemPromptRule` now emits at `VERY_IMPORTANT` priority (was `CHARLIE_REMINDER`). The system-prompt template expanded from "You are Charlie." into a compact self-check ("if the last reply sounded polite, helpful, or generic, you drifted — roast, push back, use our/we"). Banned-words template rewritten in second person with explicit pattern framing (no hedges, no "let me X" narration, no sycophantic validators); `"say the word"` added to the list.
- **Chapter weeks sort newest-first.** Within each month on the Dashboard, weekly entries now sort by `period_start` descending so the most recent week is at the top.
- **Paths resolver two-level fallback.** `helpers/paths._find` tries the immediate parent first, then the parent-of-parent, so both bundled-in-package and running-from-repo layouts resolve asset paths correctly.
- **Story tier labels.** `StoryCard` gained a `Daily` label and dropped the unused `quarterly` entry; `save-reminder.md` shortened to a direct imperative.

### Fixed
- **ty false positives on `httpx.AsyncClient` / `ConnectError` / `HTTPError`.** The previous per-line `# ty:ignore[unresolved-attribute]` comments were replaced with a scoped `[[tool.ty.overrides]]` block in `pyproject.toml` covering the four files that import httpx lazily (`cli/context_cmd.py`, `cli/hooks_cmd.py`, `cli/story_data_cmd.py`, `context/reminders/rules/search_memories.py`). The rule stays active everywhere else.

### Decisions Recorded
- ADR: Knowledge dropped from context-enrich — duplication with pinned activation context outweighed the benefit
- ADR: Rollup drill-down navigation — the dashboard is more useful as a path into raw materials than as another place to re-read the generated prose
- ADR: ty overrides for httpx lazy imports — scoped suppressions keep the rule's signal everywhere else

---

## [v1.14.4] — 2026-04-16

### Added
- **`POST /api/rebuild`** — dashboard Settings page now has a working backing route for the "Rebuild indexes" button. Runs the same `stories.dedupe` + parallel FTS/vector rebuild across memories, knowledge, stories, and messages that the server performs on startup. Previously the button silently 405'd against the SPA catch-all.

### Changed
- Public docs in `docs/` and `README.md` refreshed to match the v1.14.3 surface (`/api/memories` replaces `/api/entities`, `save_memory` replaces the nine `remember_*` helpers, `search_memories` replaces `recall`, module paths point at the feature-package layout).

### Fixed
- Three modules introduced in v1.14.3 had no test coverage — now covered: `helpers/banned_words` (21 tests on phrase detection, word-boundary matching, code-block exemption), `server/utils/seen_models` (10 tests on TTL eviction at the 24h boundary, cross-session isolation, get/set round-trips), `server/middleware/errors` (14 tests on Pydantic `ValidationError` compression and `is-instance[...]` / `chain[...]` branch-marker stripping). Suite grows 233 → 278 passing.

### Decisions Recorded
- ADR: Feature-package reorganization — flat `api/`/`models/`/`db/stores/`/`mcp/tools_*`/`tools/` collapsed into colocated `memory/{feature}/` packages
- ADR: Branded string types — `NonEmptyString`, `WorkspaceFilePath`, `TagList` reject raw `str` at ty time while Pydantic keeps runtime validation
- ADR: `ActivationContextRenderer` class collapse — one class with explicit section ordering replaces module-level `render()` plus a dozen private helpers
- ADR: `ContextBundle.current_session_id` required — fixes the Python loop-variable-leak that caused `session-save` to overwrite stale rows
- ADR: Banned words as hook-delivered reminder — ~70-phrase kill list moved from `Charlie.md` to `BannedWordsRule` with a 30-minute re-emit interval on `UserPromptSubmit`
- ADR: FTS sanitizer returns `str` not `Optional[str]` — hardens against null bytes and stray quotes while simplifying caller truthiness checks

---

## [v1.14.3] — 2026-04-16

### Changed
- **Architectural refactor** — flat `api/` + `models/` + `db/stores/` + `mcp/tools_*` + `tools/` layout collapsed into colocated feature packages under `charlieverse/memory/{entities,knowledge,sessions,stories,messages}/` (each owning its `models.py` + `store.py` + `mcp.py`). REST handlers moved to `charlieverse/server/api/` alongside typed response classes in `charlieverse/server/responses/`. Shared helpers (paths, tasks, skills, time_utils, banned_words) consolidated under `charlieverse/helpers/`. Type-only symbols moved under `charlieverse/types/`. No change to the public CLI/MCP/REST surface.
- **Branded string types** — introduced `NonEmptyString`, `WorkspaceFilePath`, and `TagList` so the compiler rejects raw `str` where validated content is expected. Applied across models, stores, MCP tools, and the renderer.
- **Activation context renderer** — `ActivationContextRenderer` is now the single public surface. Prior module-level `render()` and private helpers collapsed into methods on the class.
- **Banned words as hook-delivered reminder** — voice kill list moved from the permanent system prompt to a first-turn reminder rule (`charlieverse/context/reminders/rules/banned_words.py` + `prompts/reminders/banned_words.md`), freeing permanent prompt space.
- `Charlie.md`, `Storyteller.md`, and the `session-save` skill refreshed.

### Fixed
- **Wrong-session overwrites in `session-save`** — `ContextBundle.current_session_id` is now a required field instead of being implicitly read from a loop-scoped `session` variable that leaked the last iteration value. The renderer was handing out the wrong UUID in activation context, which caused `session-save` to update stale rows (manifesting as mixed-format datetimes in the sessions table).
- **FTS5 sanitizer crashes** — `sanitize_fts_query` now strips null bytes and stray double quotes before wrapping tokens in phrase quotes, eliminating "unterminated string" SQLite errors on hostile input. Return type tightened to `str` (empty string instead of `Optional[str]`).
- **`httpx.AsyncClient` ty false positives** — suppressed with `# ty:ignore[unresolved-attribute]` on the four sites where httpx is imported lazily; verified that the attributes exist at runtime (httpx 0.28.1).
- **Test suite realignment** — `test_memory_tools` and `test_renderer` rebuilt against the new module paths and `save_memory` / `ActivationContextRenderer` surface. Store tests use branded-type helpers. `test_time_utils` assertions updated to match the current `"5 days"` / `"1 hour"` / `"2 weeks"` format (no `"ago"` suffix).

---

## [v1.14.2] — 2026-04-01

### Added
- `StoryStore.find_by_tier_and_period` method: finds a rollup story by (tier, period_start, period_end) with timezone-normalized date matching.
- Story dedup pass on server startup: soft-deletes all but the most recently updated story for each duplicate rollup period, resolving double-write races.

### Changed
- Hook stdin parsing centralized into `IncomingHookContext` dataclass and `_incoming_context()` helper. All hooks now share a single validation path for session_id, subagent detection, and agent-type filtering.
- Hooks now skip processing when `agent_type` is present but is not `Charlieverse:Charlie`, preventing activation context from running for other agents in the same session.
- `StoryStore.upsert` now matches rollup stories by (tier, period_start, period_end) before falling back to ID — prevents duplicate rollup stories from being created across timezone-shifted period windows.
- `_parse_uuid` now accepts `str | None` and returns `None` on empty or missing input rather than raising.
- `POST /api/messages` now requires `session_id`, `role`, and `content` — returns 400 on missing params. Filters out task-notification messages at the API boundary.
- Context renderer: session tags now include `time` and `workspace path` attributes inline. Removed `<created_recently>` and `<relevant>` wrappers from memory blocks. All-time story no longer renders a title header. Recent message truncation reduced from 500 to 200 characters.
- `Charlie.md` voice rules rewritten with explicit always/never lists and expanded concrete dialog examples. Ownership language rules (I vs we vs you) made explicit. Removed `<energy_matching>` section.
- Web dashboard entity cards and rows now render full content without truncation.
- Installer (`integrations/claude/install.sh`) cleaned up.

### Fixed
- Malformed XML in activation context: `time=` attribute missing closing quote, orphan `</important>` tag removed.
- Circular import in reminders system: `system_prompt.py` now imports `ReminderTag` from `types` directly.
- Type error in story dedup: `groups` cursor result converted to list before `len()`.
- Renderer tests updated to match current tag format (session attributes, wrapper tags, truncation length).
- Temporal context fallback and trailing newline issue resolved.

### Removed
- Codex and Copilot CLI agent integrations (`prompts/cli/Codex.md`, `prompts/cli/Copilot.md`, `prompts/skills/codex/`, `prompts/skills/copilot/`) — these passthrough wrappers were unused and unmaintained.

### Decisions Recorded
- ADR: Hook stdin parsing centralized with IncomingHookContext dataclass
- ADR: Codex and Copilot CLI agent integrations removed

---

## [v1.14.1] — 2026-03-31

### Added
- `charlie context --save` (`-S`) flag: writes the activation context to a temp file and prints the path, making it easy to pipe into other tools.
- `format_time` helper in `time_utils`: formats a datetime as a locale-aware time string (e.g. "02:30 PM").
- Hatchling build hooks (`tools/build_web.py`, `tools/extract_tags.py`) so `uv build --wheel` bundles the compiled web dashboard automatically.

### Changed
- `relative_date` now returns `"Yesterday at HH:MM AM/PM"` instead of bare `"Yesterday"`, preserving time-of-day context.
- FTS query sanitizer now uses `spacy.lang.en.stop_words.STOP_WORDS` (~300+ words) instead of a hardcoded ~70-word set, improving search relevance.
- Vector index rebuild is now synchronous on server startup, eliminating a race window where early requests would query stale indexes.
- Server startup silences HuggingFace/transformers noise (`HF_HUB_VERBOSITY=error`, `TRANSFORMERS_VERBOSITY=error`, `HF_HUB_DISABLE_PROGRESS_BARS=1`).
- `charlie context` and `charlie hooks session-start` now default `--workspace` to `os.getcwd()` when not provided, so context always reflects the current directory.
- `charlie hooks session-start` no longer injects a `very-very-important` XML block into the activation context.
- Session builder now fetches the 10 most recent sessions globally instead of workspace-scoped sessions within 1 day.
- Empty reminder results are filtered before rendering to prevent blank XML tags in the activation context.
- `recent_messages` renderer removes a stray leading space from message content.
- `Charlie.md` rewritten as structured XML with identity, language rules, voice (kill list + examples), personality, and behavior blocks.
- `setup.sh` rewritten as a lightweight POSIX shell installer.
- `spacy` model download in `charlie init` uses `spacy.cli.download` API directly instead of subprocess.
- Server health polling interval increased to 1s with a 5s initial delay to account for startup time.
- `bin/charlie` no longer passes `--no-sync` to `uv run`.

### Removed
- Work-log system: `WorkLog` model, `WorkLogStore`, `POST /api/log`, `GET /api/work-logs/latest` endpoints, `charlie log` CLI command, `work_logs` / `work_logs_fts` database tables, and the `scripts/migrate.sh` helper. The feature was never wired into the activation context or MCP tools.
- `save-reminder` hook (PreCompact): removed from `charlie hooks`.
- `docs/competitive-intel-ai-coding-tools-2025.md`: stale research document removed.

### Decisions Recorded
- ADR: Work-log system removed — feature was unused dead weight
- ADR: Vector rebuild made synchronous on server startup
- ADR: spaCy STOP_WORDS replaces hardcoded FTS stop-word list
- ADR: Hook stdin parsing centralized with IncomingHookContext dataclass
- ADR: Codex and Copilot CLI agent integrations removed

---

## [v1.14.0] — 2026-03-26

### Added
- Recent conversation messages are now injected into the activation context inside `<last_session>` as a `<recent_messages>` block. The last 3 user turns (up to 6 messages) are fetched from the message store, filtered for noise, and rendered with relative timestamps — giving Charlie actual message content to pick up from rather than relying on session summary inference alone.
- New `ContextMessage` model: a lightweight frozen dataclass (`role`, `content`, `created_at`) for passing message data through the context pipeline without tool-call or metadata overhead.
- `SessionStore.recent_messages(turns)` method: fetches the last N real conversation turns globally, in chronological order. Filters out session-save commands (`/trick session-save`, `/session-save`), task-notifications, and system-reminders.
- `<workspace_directory>` tag emitted at the top of activation context output, surfacing the current working directory before any session history is read.

### Changed
- `ActivationBuilder.build()` now accepts `workspace` as an explicit parameter and propagates it to `ContextBundle`. Both REST hook endpoints (`/api/sessions/context`, `/api/sessions/start`) forward the workspace through the builder.
- Session workspace display in session history blocks now shows `Session Dir:` prefix for readability.
- `Charlie.md` gains a `<session_start>` block with explicit time-gap curiosity rules: seamless continuation for gaps under 1 hour, curiosity about gaps over 2 hours, and active inquiry about longer gaps (overnight, weekends).
- Session-start hook instruction updated to reference `recent_messages` and `current_working_directory` directly, replacing the "pretend nothing happened" framing.

### Decisions Recorded
- ADR: Recent messages injected into activation context (amends session-continuity ADR)
- ADR: Workspace surfaced as `<workspace_directory>` tag in activation context

---

## [v1.13.1] — 2026-03-26

### Added
- `charlie --version` / `charlie -v` flag — prints the installed package version and exits, following standard CLI conventions.

### Fixed
- `charlie init` now tries `uv pip install` before `pip install` when auto-installing the spaCy `en_core_web_sm` model. Bare `pip` cannot modify `uv`-managed virtual environments, causing silent install failures.

### Decisions Recorded
- ADR: spaCy model moved from pyproject.toml to `charlie init` runtime install (PyPI rejects direct URL dependencies)
- ADR: GitHub Actions release workflow uses OIDC trusted publishing for PyPI — no stored credentials
- ADR: `charlie update` as self-contained updater command

---

## [v1.13.0] — 2026-03-26

### Changed
- Workspace is now metadata-only in session and story queries — all sessions and stories are returned regardless of workspace, weighted by recency. Previously, `recent()`, `recent_within_days()`, `recent_within_range()` (session store) and `find_by_period()` (story store) filtered results to match the current workspace. This suppressed relevant cross-workspace context.
- All meaningful fields on `remember_*` MCP tools are now required. `session_id`, `tags`, and context-rich fields (`rationale`, `significance`, `feeling`, `context`, `details`, `who`, `where`, `why`) are no longer optional. This enforces memory quality at the protocol level — callers can no longer silently produce orphaned or context-free memories.
- `session_update` and `update_knowledge` `tags` parameter promoted to required.
- Reminder prompts (`collaboration.md`, `memory-tools.md`) populated with behavioral guidance for Charlie: design-with-me discipline, recall-before-engage rule, and the requirement that implied memory language must be backed by actual tool calls.

### Removed
- `EntityType.is_workspace_scoped` property removed. It was dead code — never called in production, only referenced in tests. Workspace scoping is no longer enforced at the entity type level.

### Decisions Recorded
- ADR: Workspace stored as metadata, not used as a query filter
- ADR: Drop `EntityType.is_workspace_scoped` property
- ADR: Make all meaningful fields required on MCP `remember_*` tools

---

## [v1.12.0] — 2026-03-25

### Added
- `strip_markdown()` utility in `charlieverse.nlp` — converts markdown-formatted text to plain text for denser, noise-free recall output.
- Recall now searches stories (via `StoryStore`) and returns up to 5 matching story summaries alongside entities, knowledge, and messages.
- `StorySummary` response type for story results in recall.
- Recency+relevance re-ranking for recall entity results — entities found by both FTS and vector search score higher, and recently-updated entities are boosted with a 14-day half-life decay.
- `pin` tool now supports knowledge articles — tries entity first, falls back to knowledge store, and raises a clear error if neither is found.

### Decisions Recorded
- ADR: Recall re-ranking by combined relevance and recency (14-day half-life, 0.4 recency weight)
- ADR: Recall includes story search and strips markdown before truncation

### Changed
- Entity and knowledge content is now truncated in recall results (500 chars for entities, 1000 for knowledge, 500 for messages) using `strip_markdown` to strip formatting before truncating.
- `EntitySummary` schema simplified: replaced `tags`, `pinned`, `created_at` with `age` (human-relative date string) and `truncated` flag.
- `KnowledgeSummary` schema simplified: removed `topic`, `tags`, `pinned`; added `truncated` flag.
- `MessageSummary` in recall responses now uses `age` (relative date) instead of raw `created_at` timestamp.
- Message search in recall fetches 3x candidates and filters out system/junk messages (task notifications, command wrappers, system reminders) before returning results.
- Session start prompt refined: now explicitly distinguishes between checking pending statuses and picking up conversation continuity, and instructs Charlie to be curious about time gaps — asking about weekends, work days, or gaps in knowledge about the user's routine.
- Charlie personality prompt updated: "mirrors energy" replaced with "matches energy", emphasizes genuine interest in the user's life and world, frames absent-mindedness more naturally.
- Temporal gap reminder reworded to be more natural and explicitly prompts curiosity when the gap exceeds a few hours.
- Hook output no longer wraps context in accidental `<system-reminder>` tags.
- `search_knowledge` lean summary — dropped `topic`/`tags`/`pinned` from search results to match recall schema.

---

## [v1.11.0] — 2026-03-25

### Added
- `charlieverse/paths.py` — centralized package-relative asset resolution that works for both dev checkout and `uvx`/pip installs. Replaces scattered `Path(__file__).parent.parent.parent` patterns in five files.
- `charlie init` rewritten as a full interactive setup wizard: directory creation, dependency checks, server start, provider integration (auto-detects Claude Code / Copilot in PATH), and optional conversation history import. Add `--quick` / `-q` flag for non-interactive environments.
- Tests for `config.py` and `paths.py` (31 new tests)

### Changed
- Config now defaults to `~/.charlieverse` without requiring `config.yaml` to exist — `charlie` works immediately after `uvx install charlieverse` with no config file.
- Config lookup order: `~/.charlieverse/config.yaml` first, then repo-root `config.yaml` (dev checkout), then hardcoded defaults.
- `ServerConfig.host` defaults to `0.0.0.0` (was `127.0.0.1`) so the server binds to all interfaces by default.
- `pyproject.toml` wheel packaging updated to bundle `prompts/`, `web/dist/`, `integrations/`, and `tools/` into the wheel under `charlieverse/` subdirectories — required for `uvx` installs to find bundled assets.
- Integration install scripts (`claude`, `copilot`) updated to resolve paths relative to the script location, working from both a dev checkout and an installed package.

---

## [v1.10.2] — 2026-03-24

### Added
- Tests for `recall`, renderer helpers, and `ContextBundle`

### Changed
- Charlie prompt clarified with improved documentation of all memory types and how moments are recorded
- Architectural decision records updated to capture recent system changes

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
