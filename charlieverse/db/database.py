"""Database connection and initialization for Charlieverse."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import aiosqlite
import sqlite_vec

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
logger = logging.getLogger(__name__)


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

        await db._execute(_do_load, db._conn)

    await _load_vec()

    # Enable WAL mode for concurrent reads
    await db.execute("PRAGMA journal_mode=WAL")

    # Safe in WAL mode — reduces fsync overhead for local single-user server
    await db.execute("PRAGMA synchronous=NORMAL")

    # Enable foreign keys
    await db.execute("PRAGMA foreign_keys=ON")

    # Use Row factory for dict-like access
    db.row_factory = aiosqlite.Row

    # Run pending migrations
    await _run_migrations(db)

    return db


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all pending migrations based on PRAGMA user_version.

    Each migration runs statement-by-statement inside an explicit transaction.
    user_version is bumped only after all statements succeed and commit.
    A partial failure rolls back the entire migration, leaving the DB
    at the previous version.

    Note: DDL in SQLite (CREATE TABLE, ALTER TABLE, etc.) is transactional,
    unlike most other databases. This means rollback works for schema changes.
    """
    cursor = await db.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    current_version = row[0] if row else 0

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for idx, migration_file in enumerate(migration_files[current_version:], start=current_version):
        target_version = idx + 1
        logger.info("Applying migration %s (-> version %d)", migration_file.name, target_version)
        sql = migration_file.read_text()
        try:
            # Execute each statement individually within the current transaction.
            # Split on semicolons, skip empty/whitespace-only fragments.
            statements = [s.strip() for s in sql.split(";") if s.strip()]
            for statement in statements:
                await db.execute(statement)
            await db.execute(f"PRAGMA user_version = {target_version}")
            await db.commit()
            logger.info("Migration %s applied successfully", migration_file.name)
        except Exception:
            await db.rollback()
            logger.exception("Migration %s FAILED — rolled back, database remains at version %d", migration_file.name, idx)
            raise
