-- Convert story period and timestamp columns from TEXT to DATETIME.
-- SQLite treats both the same under the hood, but DATETIME signals intent
-- and matches the rest of the schema's timestamp conventions.

-- Recreate with proper column types (SQLite has no ALTER COLUMN).
CREATE TABLE stories_new (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN ('session', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'all-time')),
    period_start DATETIME,
    period_end DATETIME,
    workspace TEXT,
    session_id TEXT,
    tags TEXT,
    created_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at DATETIME
);

INSERT INTO stories_new SELECT * FROM stories;

DROP TABLE stories;
ALTER TABLE stories_new RENAME TO stories;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_stories_tier ON stories(tier);
CREATE INDEX IF NOT EXISTS idx_stories_period ON stories(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_stories_deleted ON stories(deleted_at);
CREATE INDEX IF NOT EXISTS idx_stories_session ON stories(session_id);

-- Recreate FTS (rowids changed with table swap)
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

-- Rebuild FTS index from the new table
INSERT INTO stories_fts(stories_fts) VALUES('rebuild');

-- Recreate vector table (embeddings need rebuild after migration)
DROP TABLE IF EXISTS stories_vec;
CREATE VIRTUAL TABLE IF NOT EXISTS stories_vec USING vec0(
    embedding float[384]
);

PRAGMA user_version = 6;
