-- Storyteller session-save: new story fields, session transcript, drop hook_events

-- Sessions: add transcript_path
ALTER TABLE sessions ADD COLUMN transcript_path TEXT;

-- Drop hook_events (noisy, big, unused — storyteller works from messages)
DROP TABLE IF EXISTS hook_events;

-- Recreate stories table with new fields + expanded tier enum
-- SQLite can't ALTER CHECK constraints, so we rebuild the table.
CREATE TABLE IF NOT EXISTS stories_new (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN ('session', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'all-time')),
    period_start TEXT,
    period_end TEXT,
    workspace TEXT,
    session_id TEXT REFERENCES sessions(id),
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT
);

-- Copy existing data
INSERT INTO stories_new (id, title, content, tier, period_start, period_end, tags, created_at, updated_at, deleted_at)
SELECT id, title, content, tier, period_start, period_end, tags, created_at, updated_at, deleted_at
FROM stories;

-- Swap tables
DROP TABLE stories;
ALTER TABLE stories_new RENAME TO stories;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_stories_tier ON stories(tier);
CREATE INDEX IF NOT EXISTS idx_stories_period ON stories(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_stories_deleted ON stories(deleted_at);
CREATE INDEX IF NOT EXISTS idx_stories_session_id ON stories(session_id);
CREATE INDEX IF NOT EXISTS idx_stories_workspace ON stories(workspace);

-- Recreate FTS with summary field
DROP TABLE IF EXISTS stories_fts;
CREATE VIRTUAL TABLE IF NOT EXISTS stories_fts USING fts5(
    title,
    summary,
    content,
    tags,
    content=stories,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

-- Recreate vector table (embeddings need rebuild after migration)
DROP TABLE IF EXISTS stories_vec;
CREATE VIRTUAL TABLE IF NOT EXISTS stories_vec USING vec0(
    embedding float[384]
);

PRAGMA user_version = 5;
