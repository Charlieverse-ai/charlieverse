---
title: Hybrid search with FTS5 + sqlite-vec
date: 2026-03-14
status: accepted
tags: [search, database, embeddings, foundational]
---

# Hybrid search with FTS5 + sqlite-vec

## Context

Memory retrieval needs to handle two kinds of queries: exact keyword matches ("what was the decision about FastMCP") and semantic similarity ("times Emily was frustrated"). A single search strategy can't serve both well. The server needs to run locally on consumer hardware without external services.

## Decision

Use SQLite's FTS5 extension for full-text search and sqlite-vec for vector similarity search, both running in the same SQLite database. Embeddings are generated locally via sentence-transformers (all-MiniLM-L6-v2). External content FTS5 tables mirror the main tables and stay synchronized on write operations.

## Alternatives Considered

- **PostgreSQL + pgvector**: Better scaling characteristics but requires a separate database server. Overkill for a local memory store and adds deployment complexity.
- **Chroma/Pinecone/Weaviate**: Purpose-built vector databases but add external dependencies. The data should live in a single portable file.
- **FTS5 only**: Keyword search misses semantic relationships. "Tell me about burnout" wouldn't find entries about "hitting the wall" or "spiraling."
- **Vector only**: Semantic search is fuzzy by nature. When someone searches for a specific term, FTS5's exact matching is faster and more precise.

## Consequences

- Single SQLite file contains all data, full-text indexes, and vector indexes. Portable and backupable.
- No external services required — everything runs locally.
- FTS5 tables must be kept in sync with source tables on every write (external content tables rebuild via triggers or explicit sync).
- Embedding model loads into memory on server start (~90MB). CPU-only mode forced to avoid GPU framework issues on macOS.
- sqlite-vec requires loading a native extension, which means thread-safe connection management.
- Search queries need FTS5 syntax sanitization to prevent crashes on special characters.
