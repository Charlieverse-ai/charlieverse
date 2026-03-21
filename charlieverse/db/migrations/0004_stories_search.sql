-- Add FTS5 and vector search to stories

CREATE VIRTUAL TABLE IF NOT EXISTS stories_fts USING fts5(
    title,
    content,
    tags,
    content=stories,
    content_rowid=rowid,
    tokenize='porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS stories_vec USING vec0(
    embedding float[384]
);
