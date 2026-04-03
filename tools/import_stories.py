"""Import story .md files from import/stories/ into the database."""

import asyncio
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from charlieverse.config import config

STORIES_DIR = config.path / "import" / "stories"
DB_PATH = config.database


def derive_metadata(filepath: Path) -> dict | None:
    """Derive title, tier, period_start, period_end from file path."""
    rel = filepath.relative_to(STORIES_DIR)
    parts = rel.parts
    name = filepath.stem.replace(".story", "")  # strip both .story and .md

    # all-time.story.md
    if name == "all-time" and len(parts) == 1:
        return {
            "title": "All Time",
            "tier": "all-time",
            "period_start": None,
            "period_end": None,
        }

    # year.story.md → 2025/year.story.md
    if name == "year" and len(parts) == 2:
        year = parts[0]
        return {
            "title": f"{year}",
            "tier": "yearly",
            "period_start": f"{year}-01-01",
            "period_end": f"{year}-12-31",
        }

    # Q1.story.md → 2026/Q1.story.md
    if name.startswith("Q") and len(parts) == 2:
        year = parts[0]
        quarter = int(name[1])
        month_start = (quarter - 1) * 3 + 1
        month_end = quarter * 3
        return {
            "title": f"Q{quarter} {year}",
            "tier": "quarterly",
            "period_start": f"{year}-{month_start:02d}-01",
            "period_end": f"{year}-{month_end:02d}-28",
        }

    # month.story.md → 2025/11/month.story.md
    if name == "month" and len(parts) == 3:
        year = parts[0]
        month = int(parts[1])
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        return {
            "title": f"{month_names[month]} {year}",
            "tier": "monthly",
            "period_start": f"{year}-{month:02d}-01",
            "period_end": f"{year}-{month:02d}-28",
        }

    # W2.story.md → 2025/11/W2.story.md
    week_match = re.match(r"W(\d+)", name)
    if week_match and len(parts) == 3:
        year = parts[0]
        month = int(parts[1])
        week_num = int(week_match.group(1))
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        # Approximate week start/end
        day_start = max(1, (week_num - 1) * 7 + 1)
        day_end = min(28, week_num * 7)
        return {
            "title": f"Week {week_num}, {month_names[month]} {year}",
            "tier": "weekly",
            "period_start": f"{year}-{month:02d}-{day_start:02d}",
            "period_end": f"{year}-{month:02d}-{day_end:02d}",
        }

    return None


async def main():
    if not STORIES_DIR.exists():
        print(f"Stories directory not found: {STORIES_DIR}")
        return

    story_files = sorted(STORIES_DIR.rglob("*.story.md"))
    print(f"Found {len(story_files)} story files")

    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row

    # Check if stories table exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='stories'"
    )
    if not await cursor.fetchone():
        print("Stories table doesn't exist. Run the server first to apply migrations.")
        await db.close()
        return

    imported = 0
    skipped = 0

    for filepath in story_files:
        meta = derive_metadata(filepath)
        if not meta:
            print(f"  SKIP (unknown pattern): {filepath.relative_to(STORIES_DIR)}")
            skipped += 1
            continue

        content = filepath.read_text()

        # Check for duplicate by title + tier
        cursor = await db.execute(
            "SELECT id FROM stories WHERE title = ? AND tier = ? AND deleted_at IS NULL",
            (meta["title"], meta["tier"]),
        )
        if await cursor.fetchone():
            print(f"  EXISTS: {meta['title']} ({meta['tier']})")
            skipped += 1
            continue

        story_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        await db.execute(
            """INSERT INTO stories (id, title, content, tier, period_start, period_end, tags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                story_id,
                meta["title"],
                content,
                meta["tier"],
                meta["period_start"],
                meta["period_end"],
                None,
                now,
                now,
            ),
        )
        print(f"  IMPORTED: {meta['title']} ({meta['tier']})")
        imported += 1

    await db.commit()
    await db.close()
    print(f"\nDone. Imported: {imported}, Skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
