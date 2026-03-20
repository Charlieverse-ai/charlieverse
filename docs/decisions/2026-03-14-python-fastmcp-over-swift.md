---
title: Python + FastMCP over Swift
date: 2026-03-14
status: accepted
tags: [platform, language, framework, foundational]
---

# Python + FastMCP over Swift

## Context

Charlieverse started as a Swift server with a native Mac app. The Swift implementation had a working MCP daemon, 18 tools, database layer, and UI — but it was Mac-only, difficult to distribute, and fighting the language on async patterns. The codebase had gone through multiple identity shifts (openclaw → MCP tools → same conversation anywhere → server+portal) and accumulated significant tech debt. Meanwhile, Emily's Work Charlie had been running on a Python MCP server for almost a year with zero issues.

FastMCP (23.7k stars) had emerged as a full MCP spec-compliant framework with OAuth 2.1, middleware, auto schema generation, and transport handling — everything the Swift server had to build by hand.

## Decision

Rebuild the entire MCP server in Python using FastMCP 3.1.0 as the framework. Ship as a pip-installable package. Drop the native Mac app and Swift codebase entirely.

## Alternatives Considered

- **Continue with Swift**: Had a working implementation but was Mac-only, no pip equivalent for distribution, and the async patterns were fighting the language. The codebase needed a major cleanup anyway.
- **Node.js/TypeScript**: Cross-platform and good MCP support, but Emily's strongest backend language is Python and the ML ecosystem (embeddings, NLP) is Python-native.
- **Rust**: Performance benefits unnecessary for a local memory server. Distribution story is good but development velocity would suffer.

## Consequences

- Cross-platform by default — Windows and Linux supported without extra work.
- Distribution via `pip install` instead of `.pkg` downloads.
- Access to the full Python ML ecosystem (sentence-transformers, spaCy, sqlite-vec) without FFI bridges.
- FastMCP handles transport, auth, and schema generation for free.
- Lost native Mac app UI — replaced by web UI (React) and provider plugin integration.
- Python version constraints become a concern (spaCy requires <3.14 currently).
- The entire server was rebuilt in a single afternoon, validating the decision.
