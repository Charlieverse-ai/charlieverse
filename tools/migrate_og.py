#!/usr/bin/env python3
"""Migrate data from OG Charlie (emily.mcp.tools) database to new Python Charlieverse.

Usage:
    uv run python tools/migrate_og.py --old ~/Downloads/Charlie.dog/charlie/tools/emily.mcp.tools/data/memory.db

Migrates: entity_data → entities + knowledge, contexts → sessions
Deduplicates by name (keeps newest).
Maps freeform types to our 6 entity types + knowledge articles.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# --- Type mapping ---
# OG Charlie had 90+ freeform types. We map them to our 6 entity types
# or to knowledge articles.

PERSON_TYPES = {
    "person", "person_detail", "person_interaction", "person_update",
    "ai_colleague", "relationship", "mentorship",
}

DECISION_TYPES = {
    "decision", "technical_decision", "architecture_decision",
    "strategic_insight", "strategy", "migration_strategy",
}

SOLUTION_TYPES = {
    "solution", "final_solution", "problem", "learning", "correction",
    "technical_learning", "technical_discovery", "technical_research",
    "technical_investigation", "technical_insight", "critical_bug_analysis",
    "security_issue_resolved", "incident",
}

PREFERENCE_TYPES = {
    "preference", "communication_preference", "communication_rule",
    "communication_template", "workflow", "process", "code_practice",
    "vocabulary", "protocol_update", "assessment_pattern",
    "interview_pattern", "interview_philosophy", "interview_technique",
}

MILESTONE_TYPES = {
    "milestone", "project_milestone", "technical_milestone",
    "product_milestone", "technical_achievement", "performance_achievement",
    "brag_doc", "career",
}

MOMENT_TYPES = {
    "emotional_context", "emotional_insight", "emotional_event",
    "personal", "coaching_insight",
}

# Everything else becomes knowledge articles
KNOWLEDGE_TYPES = {
    "note", "meeting", "meeting_notes", "project", "project_update",
    "project_collaboration", "project_context", "project_learning",
    "concept", "area", "technical_context", "technical_design",
    "technical", "technical_reference", "technical_work",
    "architectural_pattern", "architectural_improvement", "pattern",
    "implementation", "investigation", "code_review_session",
    "feedback", "feature_enhancement", "improvement", "reference",
    "session_note", "task", "work_context", "business_context",
    "company_event", "workplace_event", "event", "historical_context",
    "channel_reference", "team_process", "interview",
    "strategic_insight", "lesson",
}


def _map_type(og_type: str) -> tuple[str, bool]:
    """Map OG type to (our_type, is_knowledge).

    Returns (entity_type, False) for entities, or (topic_prefix, True) for knowledge.
    """
    og_lower = og_type.lower().strip()

    if og_lower in PERSON_TYPES:
        return "person", False
    if og_lower in DECISION_TYPES:
        return "decision", False
    if og_lower in SOLUTION_TYPES:
        return "solution", False
    if og_lower in PREFERENCE_TYPES:
        return "preference", False
    if og_lower in MILESTONE_TYPES:
        return "milestone", False
    if og_lower in MOMENT_TYPES:
        return "moment", False
    if og_lower in KNOWLEDGE_TYPES:
        return og_lower, True

    # Unknown type — default to knowledge
    return og_lower, True


def _normalize_date(value: str | None) -> str:
    """Normalize date to ISO 8601."""
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(value)
        return dt.isoformat()
    except ValueError:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return dt.isoformat()
        except ValueError:
            return datetime.now(timezone.utc).isoformat()


def _build_content(name: str, content: str | None, metadata: str | None) -> str:
    """Build entity content from OG fields."""
    parts = []
    if name:
        parts.append(name)
    if content:
        parts.append(content)
    if metadata:
        try:
            meta = json.loads(metadata)
            if isinstance(meta, dict):
                for k, v in meta.items():
                    if v and k not in ("created_at", "updated_at", "id", "type"):
                        parts.append(f"{k}: {v}")
        except (json.JSONDecodeError, TypeError):
            pass
    return "\n".join(parts) if parts else name or "Unknown"


def _parse_tags(tags_str: str | None) -> list[str] | None:
    """Parse tags from OG format."""
    if not tags_str:
        return None
    try:
        parsed = json.loads(tags_str)
        if isinstance(parsed, list) and parsed:
            return [str(t) for t in parsed if t]
    except (json.JSONDecodeError, TypeError):
        # Try comma-separated
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if tags:
            return tags
    return None


async def migrate_og(old_path: str, new_path: str, dry_run: bool = False) -> None:
    from charlieverse.db import database

    old_db = sqlite3.connect(old_path)
    old_db.row_factory = sqlite3.Row
    print(f"Connected to OG Charlie: {old_path}")

    # Counts
    entity_count = old_db.execute("SELECT COUNT(*) FROM entity_data").fetchone()[0]
    context_count = old_db.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
    print("\nFound:")
    print(f"  Entities:  {entity_count}")
    print(f"  Contexts:  {context_count} (handoff sessions)")

    if dry_run:
        # Show type mapping preview
        rows = old_db.execute("SELECT type, COUNT(*) as cnt FROM entity_data GROUP BY type ORDER BY cnt DESC").fetchall()
        print("\nType mapping preview:")
        for row in rows:
            mapped, is_knowledge = _map_type(row["type"])
            dest = f"knowledge ({mapped})" if is_knowledge else f"entity ({mapped})"
            print(f"  {row['type']:40s} ({row['cnt']:3d}) → {dest}")
        print("\n[DRY RUN] No changes made.")
        old_db.close()
        return

    # Connect to new database
    new_db = await database.connect(new_path)
    print(f"Connected to new database: {new_path}")

    # --- Create a system session for OG imports ---
    system_session_id = str(uuid4())
    await new_db.execute(
        """INSERT OR IGNORE INTO sessions (id, what_happened, for_next_session, tags, workspace, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            system_session_id,
            "Migrated from OG Charlie (emily.mcp.tools)",
            "OG Charlie memories now available in new system",
            json.dumps(["migration", "og-charlie"]),
            None,
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    await new_db.commit()

    # --- Migrate contexts → sessions ---
    print("\nMigrating contexts → sessions...")
    old_contexts = old_db.execute("SELECT * FROM contexts ORDER BY created_at ASC").fetchall()
    migrated_sessions = 0

    for row in old_contexts:
        await new_db.execute(
            """INSERT OR IGNORE INTO sessions (id, what_happened, for_next_session, tags, workspace, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["content"],
                row["summary"],
                row["topics"],  # already JSON-ish
                None,
                _normalize_date(row["created_at"]),
                _normalize_date(row["created_at"]),
            ),
        )
        migrated_sessions += 1

    await new_db.commit()
    print(f"  Migrated {migrated_sessions} sessions")

    # --- Deduplicate entities by name ---
    print("\nDeduplicating entities by name...")
    all_entities = old_db.execute(
        "SELECT * FROM entity_data ORDER BY updated_at DESC"
    ).fetchall()

    seen_names: dict[str, sqlite3.Row] = {}
    duplicates = 0
    for row in all_entities:
        name = row["name"].strip().lower()
        if name in seen_names:
            duplicates += 1
        else:
            seen_names[name] = row
    unique_entities = list(seen_names.values())
    print(f"  {len(all_entities)} total → {len(unique_entities)} unique ({duplicates} duplicates removed)")

    # --- Migrate entity_data → entities + knowledge ---
    print("\nMigrating entities...")
    migrated_entities = 0
    migrated_knowledge = 0
    type_stats: dict[str, int] = {}

    for row in unique_entities:
        mapped_type, is_knowledge = _map_type(row["type"])
        content = _build_content(row["name"], row["content"], row["metadata"])
        tags = _parse_tags(row["tags"])

        # Add OG type as a tag for provenance
        if tags:
            tags.append(f"og:{row['type']}")
        else:
            tags = [f"og:{row['type']}"]

        type_stats[mapped_type] = type_stats.get(mapped_type, 0) + 1

        if is_knowledge:
            # Insert as knowledge article
            await new_db.execute(
                """INSERT OR IGNORE INTO knowledge
                   (id, topic, content, tags, pinned, created_session_id, updated_session_id,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    row["name"],
                    content,
                    json.dumps(tags),
                    0,
                    system_session_id,
                    None,
                    _normalize_date(row["created_at"]),
                    _normalize_date(row["updated_at"]),
                ),
            )
            migrated_knowledge += 1
        else:
            # Insert as entity
            await new_db.execute(
                """INSERT OR IGNORE INTO entities
                   (id, type, content, tags, pinned, created_session_id, updated_session_id,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["id"],
                    mapped_type,
                    content,
                    json.dumps(tags),
                    0,
                    system_session_id,
                    None,
                    _normalize_date(row["created_at"]),
                    _normalize_date(row["updated_at"]),
                ),
            )
            migrated_entities += 1

    await new_db.commit()

    # Rebuild FTS
    print("\nRebuilding FTS indexes...")
    await new_db.execute("INSERT INTO entities_fts(entities_fts) VALUES('rebuild')")
    await new_db.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")
    await new_db.commit()

    # Summary
    print(f"\n{'='*50}")
    print("Migration complete!")
    print(f"  Sessions:  {migrated_sessions}")
    print(f"  Entities:  {migrated_entities}")
    print(f"  Knowledge: {migrated_knowledge}")
    print(f"  Duplicates removed: {duplicates}")
    print("\nType breakdown:")
    for t, count in sorted(type_stats.items(), key=lambda x: -x[1]):
        _, is_k = _map_type(t) if t not in ("person", "decision", "solution", "preference", "milestone", "moment") else (t, False)
        dest = "knowledge" if t in KNOWLEDGE_TYPES or t not in ("person", "decision", "solution", "preference", "milestone", "moment") else "entity"
        print(f"  {t:30s} → {dest:10s} ({count})")

    old_db.close()
    await new_db.close()

    # Backfill embeddings
    print(f"\n{'='*50}")
    print("Backfilling embeddings...")
    from tools.migrate import backfill_embeddings
    await backfill_embeddings(new_path)


def main():
    parser = argparse.ArgumentParser(description="Migrate OG Charlie (emily.mcp.tools) database")
    parser.add_argument(
        "--old",
        required=True,
        help="Path to OG Charlie memory.db",
    )
    parser.add_argument(
        "--new",
        default=str(Path.home() / ".charlieverse" / "charlie.db"),
        help="Path to new database (default: ~/.charlieverse/charlie.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show type mapping without making changes",
    )

    args = parser.parse_args()

    if not Path(args.old).exists():
        print(f"Error: Database not found at {args.old}")
        return

    asyncio.run(migrate_og(args.old, args.new, args.dry_run))


if __name__ == "__main__":
    main()
