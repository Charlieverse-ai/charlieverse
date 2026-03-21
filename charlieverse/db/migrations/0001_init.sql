-- Charlieverse initial schema
-- Sessions, entities, knowledge, work_logs with FTS5 and vector support
-- FTS5 uses external content tables — stores manage FTS sync explicitly.

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    what_happened   TEXT,
    for_next_session TEXT,
    tags            TEXT,  -- JSON array
    workspace       TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    deleted_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_deleted_at ON sessions(deleted_at);

-- Entities (memories)
CREATE TABLE IF NOT EXISTS entities (
    id                  TEXT PRIMARY KEY,
    type                TEXT NOT NULL,
    content             TEXT NOT NULL,
    tags                TEXT,  -- JSON array
    pinned              INTEGER NOT NULL DEFAULT 0,
    created_session_id  TEXT NOT NULL,
    updated_session_id  TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    deleted_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_pinned ON entities(pinned);
CREATE INDEX IF NOT EXISTS idx_entities_created_session_id ON entities(created_session_id);
CREATE INDEX IF NOT EXISTS idx_entities_deleted_at ON entities(deleted_at);

-- Entities FTS5 (external content — stores manage sync)
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    content,
    tags,
    content=entities,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Entities embeddings (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS entities_vec USING vec0(
    embedding float[384]
);

-- Knowledge
CREATE TABLE IF NOT EXISTS knowledge (
    id                  TEXT PRIMARY KEY,
    topic               TEXT NOT NULL,
    content             TEXT NOT NULL,
    tags                TEXT,  -- JSON array
    pinned              INTEGER NOT NULL DEFAULT 0,
    created_session_id  TEXT NOT NULL,
    updated_session_id  TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    deleted_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_knowledge_pinned ON knowledge(pinned);
CREATE INDEX IF NOT EXISTS idx_knowledge_created_session_id ON knowledge(created_session_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_deleted_at ON knowledge(deleted_at);

-- Knowledge FTS5 (external content — stores manage sync)
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    topic,
    content,
    tags,
    content=knowledge,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Knowledge embeddings (sqlite-vec)
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vec USING vec0(
    embedding float[384]
);

-- Work logs
CREATE TABLE IF NOT EXISTS work_logs (
    id                  TEXT PRIMARY KEY,
    content             TEXT NOT NULL,
    tags                TEXT,  -- JSON array
    created_session_id  TEXT NOT NULL,
    updated_session_id  TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    deleted_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_work_logs_created_session_id ON work_logs(created_session_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_created_at ON work_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_work_logs_deleted_at ON work_logs(deleted_at);

-- Work logs FTS5 (external content — stores manage sync)
CREATE VIRTUAL TABLE IF NOT EXISTS work_logs_fts USING fts5(
    content,
    tags,
    content=work_logs,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Messages (captured from hooks — user prompts + assistant responses)
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    session_id      TEXT,
    role            TEXT NOT NULL,  -- 'user' or 'assistant'
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Messages FTS5 (external content)
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content=messages,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Hook events (auto-populated logbook from provider hooks)
CREATE TABLE IF NOT EXISTS hook_events (
    id              TEXT PRIMARY KEY,
    session_id      TEXT,
    event_type      TEXT NOT NULL,  -- 'tool_use', 'tool_result', 'prompt', 'response', 'compact', 'subagent', etc
    tool_name       TEXT,
    content         TEXT,
    metadata        TEXT,  -- JSON
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_hook_events_session_id ON hook_events(session_id);
CREATE INDEX IF NOT EXISTS idx_hook_events_event_type ON hook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_hook_events_created_at ON hook_events(created_at);
