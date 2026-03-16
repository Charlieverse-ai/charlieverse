#!/usr/bin/env python3
"""Migrate data from old Charlieverse (Swift/GRDB) database to new Python database.

Usage:
    uv run python tools/migrate.py --old ~/.charlie/profiles/default/db/charlie.db
    uv run python tools/migrate.py --old /path/to/old.db --new ~/.charlieverse/charlie.db

Migrates: sessions, entities, knowledge
Skips: conversations, messages, personas, projects, tasks, proposals, embeddings
Embeddings will be regenerated automatically as tools are used.
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


async def migrate(old_path: str, new_path: str, dry_run: bool = False) -> None:

    from charlieverse.db import database

    old_db = sqlite3.connect(old_path)
    old_db.row_factory = sqlite3.Row
    print(f"Connected to old database: {old_path}")

    # Count records
    sessions_count = old_db.execute("SELECT COUNT(*) FROM sessions WHERE deleted_at IS NULL").fetchone()[0]
    entities_count = old_db.execute("SELECT COUNT(*) FROM entities WHERE deleted_at IS NULL").fetchone()[0]
    knowledge_count = old_db.execute("SELECT COUNT(*) FROM knowledge WHERE deleted_at IS NULL").fetchone()[0]

    print("\nFound:")
    print(f"  Sessions:  {sessions_count}")
    print(f"  Entities:  {entities_count}")
    print(f"  Knowledge: {knowledge_count}")
    print(f"  Total:     {sessions_count + entities_count + knowledge_count}")

    if dry_run:
        print("\n[DRY RUN] No changes made.")
        old_db.close()
        return

    # Connect to new database (creates it + runs migrations)
    new_db = await database.connect(new_path)
    print(f"\nConnected to new database: {new_path}")

    # --- Migrate sessions ---
    print("\nMigrating sessions...")
    old_sessions = old_db.execute(
        "SELECT * FROM sessions ORDER BY started_at ASC"
    ).fetchall()

    migrated_sessions = 0
    for row in old_sessions:
        old_id = _blob_to_uuid(row["id"])
        await new_db.execute(
            """INSERT OR IGNORE INTO sessions
               (id, what_happened, for_next_session, tags, workspace, created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                old_id,
                row["what_happened"],
                row["for_next_session"],
                row["tags"],  # already JSON
                None,  # no workspace in old schema
                _normalize_date(row["started_at"]),
                _normalize_date(row["updated_at"]),
                _normalize_date(row["deleted_at"]) if row["deleted_at"] else None,
            ),
        )
        migrated_sessions += 1

    await new_db.commit()
    print(f"  Migrated {migrated_sessions} sessions")

    # --- Migrate entities ---
    print("Migrating entities...")
    old_entities = old_db.execute(
        "SELECT * FROM entities ORDER BY created_at ASC"
    ).fetchall()

    migrated_entities = 0
    for row in old_entities:
        old_id = _blob_to_uuid(row["id"])
        session_id = _blob_to_uuid(row["created_session_id"])
        updated_session_id = _blob_to_uuid(row["updated_session_id"]) if row["updated_session_id"] else None

        await new_db.execute(
            """INSERT OR IGNORE INTO entities
               (id, type, content, tags, pinned, created_session_id, updated_session_id,
                created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                old_id,
                row["type"],
                row["content"],
                row["tags"],  # already JSON
                int(row["pinned"]),
                session_id,
                updated_session_id,
                _normalize_date(row["created_at"]),
                _normalize_date(row["updated_at"]),
                _normalize_date(row["deleted_at"]) if row["deleted_at"] else None,
            ),
        )
        migrated_entities += 1

    await new_db.commit()
    print(f"  Migrated {migrated_entities} entities")

    # --- Migrate knowledge ---
    print("Migrating knowledge...")
    old_knowledge = old_db.execute(
        "SELECT * FROM knowledge ORDER BY created_at ASC"
    ).fetchall()

    migrated_knowledge = 0
    for row in old_knowledge:
        old_id = _blob_to_uuid(row["id"])
        session_id = _blob_to_uuid(row["created_session_id"])
        updated_session_id = _blob_to_uuid(row["updated_session_id"]) if row["updated_session_id"] else None

        await new_db.execute(
            """INSERT OR IGNORE INTO knowledge
               (id, topic, content, tags, pinned, created_session_id, updated_session_id,
                created_at, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                old_id,
                row["topic"],
                row["content"],
                row["tags"],  # already JSON
                int(row["pinned"]),
                session_id,
                updated_session_id,
                _normalize_date(row["created_at"]),
                _normalize_date(row["updated_at"]),
                _normalize_date(row["deleted_at"]) if row["deleted_at"] else None,
            ),
        )
        migrated_knowledge += 1

    await new_db.commit()
    print(f"  Migrated {migrated_knowledge} knowledge articles")

    # Rebuild FTS indexes
    print("\nRebuilding FTS indexes...")
    await new_db.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    await new_db.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
    await new_db.commit()
    print("  FTS indexes rebuilt")

    # Summary
    print(f"\n{'='*50}")
    print("Migration complete!")
    print(f"  Sessions:  {migrated_sessions}")
    print(f"  Entities:  {migrated_entities}")
    print(f"  Knowledge: {migrated_knowledge}")
    print("\nSkipped (not in v1 scope):")
    print("  - Conversations & messages")
    print("  - Personas & prompt sections")
    print("  - Projects & tasks")
    print("  - Knowledge proposals")
    print(f"\nNew database: {new_path}")

    old_db.close()
    await new_db.close()

    # Backfill embeddings
    print("\n" + "=" * 50)
    print("Backfilling embeddings...")
    await backfill_embeddings(new_path)


def _blob_to_uuid(blob: bytes | None) -> str | None:
    """Convert a GRDB UUID blob to a string UUID."""
    if blob is None:
        return None
    if isinstance(blob, bytes) and len(blob) == 16:
        return str(uuid.UUID(bytes=blob))
    # Already a string somehow
    return str(blob)


def _normalize_date(value: str | None) -> str | None:
    """Normalize date strings from old format to ISO 8601."""
    if value is None:
        return None
    # GRDB stores dates as "YYYY-MM-DD HH:MM:SS.SSS" or ISO format
    # Our new schema uses ISO 8601
    try:
        dt = datetime.fromisoformat(value)
        return dt.isoformat()
    except ValueError:
        # Try parsing GRDB's default format
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
            return dt.isoformat()
        except ValueError:
            return value  # pass through as-is


def main():
    parser = argparse.ArgumentParser(description="Migrate old Charlieverse database to new format")
    parser.add_argument(
        "--old",
        required=True,
        help="Path to old Charlieverse database (e.g., ~/.charlie/profiles/default/db/charlie.db)",
    )
    parser.add_argument(
        "--new",
        default=str(Path.home() / ".charlieverse" / "charlie.db"),
        help="Path to new database (default: ~/.charlieverse/charlie.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    if not Path(args.old).exists():
        print(f"Error: Old database not found at {args.old}")
        return

    asyncio.run(migrate(args.old, args.new, args.dry_run))


async def backfill_embeddings(db_path: str) -> None:
    """Generate embeddings for all entities and knowledge that don't have them."""
    from charlieverse.db import database
    from charlieverse.db.stores import KnowledgeStore, MemoryStore
    from charlieverse.embeddings import encode, prepare_entity_text, prepare_knowledge_text

    db = await database.connect(db_path)
    memories = MemoryStore(db)
    knowledge_store = KnowledgeStore(db)

    # Get all active entities
    entities = await memories.list(limit=10000)
    print(f"Generating embeddings for {len(entities)} entities...")

    # Batch encode for efficiency
    if entities:
        texts = [prepare_entity_text(e.content, e.tags) for e in entities]
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_entities = entities[i : i + batch_size]
            embeddings = await encode(batch_texts)

            for entity, embedding in zip(batch_entities, embeddings):
                await memories.upsert_embedding(entity.id, embedding)

            done = min(i + batch_size, len(entities))
            print(f"  Entities: {done}/{len(entities)}")

    # Get all active knowledge
    articles = await knowledge_store.list(limit=10000)
    print(f"Generating embeddings for {len(articles)} knowledge articles...")

    if articles:
        texts = [prepare_knowledge_text(k.topic, k.content, k.tags) for k in articles]
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_articles = articles[i : i + batch_size]
            embeddings = await encode(batch_texts)

            for article, embedding in zip(batch_articles, embeddings):
                await knowledge_store.upsert_embedding(article.id, embedding)

            done = min(i + batch_size, len(articles))
            print(f"  Knowledge: {done}/{len(articles)}")

    await db.close()
    print("\nEmbedding backfill complete!")


if __name__ == "__main__":
    main()
