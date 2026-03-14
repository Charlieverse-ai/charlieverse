"""Database connection and initialization for Charlieverse."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import aiosqlite
import sqlite_vec


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def connect(db_path: str | Path) -> aiosqlite.Connection:
    """Open a connection to the Charlieverse database.

    Loads sqlite-vec extension, enables WAL mode and foreign keys,
    then runs any pending migrations.
    """
    db = await aiosqlite.connect(str(db_path))

    # Load sqlite-vec extension via aiosqlite's internal thread.
    # aiosqlite dispatches all work to a background thread, so we use _execute
    # to run the extension loading on that same thread.
    async def _load_vec() -> None:
        def _do_load(conn: sqlite3.Connection) -> None:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            return None

        await db._execute(_do_load, db._conn)  # noqa: SLF001

    await _load_vec()

    # Enable WAL mode for concurrent reads
    await db.execute("PRAGMA journal_mode=WAL")

    # Enable foreign keys
    await db.execute("PRAGMA foreign_keys=ON")

    # Use Row factory for dict-like access
    db.row_factory = aiosqlite.Row

    # Run pending migrations
    await _run_migrations(db)

    return db


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all pending migrations based on PRAGMA user_version."""
    cursor = await db.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    current_version = row[0] if row else 0

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files[current_version:]:
        sql = migration_file.read_text()
        await db.executescript(sql)

    await db.commit()
