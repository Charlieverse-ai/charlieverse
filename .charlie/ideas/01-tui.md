# 01 — Charlie TUI: Terminal Command Center

## What It Is

A terminal-based command center that wraps AI providers (Claude Code, Copilot, Codex, etc.) into a unified workspace with Charlie's memory layer and configurable dashboard widgets.

**Charlie wraps providers, doesn't replace them.** Each provider stays in its own pane doing its own thing. Charlie adds: shared memory across all panes, unified session tracking, and a customizable dashboard alongside.

## What It Is NOT

- Not another chat UI competing with provider frontends
- Not a reimplementation of Claude Code or Copilot's features
- Not the Mac app in a terminal

## Core Pieces

### 1. Provider Pane Management
Spawn, arrange, and switch between provider sessions. Each pane is an embedded terminal running the provider's own CLI. Charlie orchestrates — providers execute.

- `charlie` (no args) → launch TUI
- Multiple provider panes visible simultaneously
- Tab/split navigation between panes
- Provider sessions share Charlie's memory via the MCP server

### 2. Charlie Layer
The persistent memory/personality that lives across all providers. Already built — MCP server, memory tools, knowledge, stories, skills. The TUI is just another client.

### 3. Dashboard Widgets
Configurable panels alongside provider panes. Config-driven placement (work profile ≠ personal profile).

Potential widgets:
- GitHub PR/CI status
- Slack unread messages
- Linear/Jira backlog
- Charlie memory browser
- Session history
- Story timeline
- Skill manager

### 4. Profile System
Work Emily and personal Emily have different needs. Same `charlie` binary, different config = different experience.

- Work profile: GitHub PRs, Slack, Linear, Claude Code + Copilot panes
- Personal profile: Memory management, story timeline, multiple provider panes
- Config stored in `config.local.yaml` or profile-specific TOML

## Architecture

```
charlie TUI (Textual)
├── Provider Panes (embedded terminal sessions)
│   ├── Claude Code (claude CLI)
│   ├── Copilot (gh copilot / VS Code)
│   ├── Codex (codex CLI)
│   └── Local models (ollama, etc.)
├── Dashboard Widgets (async polling / WebSocket)
│   ├── GitHub (gh CLI / API)
│   ├── Slack (SDK / API)
│   └── Custom widgets
├── Charlie Panel (MCP client)
│   ├── Memory browser
│   ├── Session manager
│   └── Skill runner
└── Config (TOML profiles)
```

The MCP server we already built IS the backend. The TUI is a view layer.

## Key Design Decisions

- **Providers own their UX.** We don't render chat bubbles or tool timelines. The provider CLI does that in its own pane.
- **Charlie owns the cross-cutting concerns.** Memory, personality, context — shared via MCP across all provider panes.
- **Widgets are plugins.** Config defines what's visible and where. Adding a new integration = writing a widget class + polling function.
- **Textual framework.** Modes for top-level screens (chat/dashboard/settings), TabbedContent for panes, grid layout for widgets, workers for async updates.

## Research

Detailed research saved in Charlieverse knowledge under:
- "TUI Command Center Architecture"
- "Python Rich and Textual Formatting APIs"
- "AI Agent Platform Skill Discovery Paths"

Key references: Elia (LiteLLM + Textual), GPTUI (CVM architecture), wtfutil (config-driven widgets), Toad (wire protocol between TUI and backend).

## Status

Idea stage. Not v1 scope. The MCP server, memory system, skills, and CLI are the foundation this builds on.
