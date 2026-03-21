-- Stories table — tiered narrative arcs (weekly, monthly, quarterly, yearly, all-time)

CREATE TABLE IF NOT EXISTS stories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN ('weekly', 'monthly', 'quarterly', 'yearly', 'all-time')),
    period_start TEXT,
    period_end TEXT,
    tags TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_stories_tier ON stories(tier);
CREATE INDEX IF NOT EXISTS idx_stories_period ON stories(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_stories_deleted ON stories(deleted_at);
