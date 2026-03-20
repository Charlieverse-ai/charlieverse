"""CLI command to extract and import conversation history.

Wraps tools/extract_conversations.py as `charlie import`.
Auto-discovers Claude, Copilot, and Codex session files, extracts
messages, and writes a combined JSONL file for the Storyteller.

With --messages, also bulk-imports the extracted messages into the
database for search_messages / FTS lookup.

With --stories, splits the JSONL into weekly files and reports which
weeks need Storyteller processing (no stories in DB yet).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import typer

from charlieverse.config import config

DEFAULT_OUTPUT = config.path / "import" / "conversations.jsonl"
DEFAULT_SPLIT_DIR = config.path / "import" / "weekly"
DEFAULT_HOST = config.server.ip_address()
DEFAULT_PORT = config.server.port


def import_conversations(
    output: Path = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Output JSONL file path"),
    from_file: Path | None = typer.Option(None, "--from-file", "-f", help="Import from existing JSONL instead of auto-discovering"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Filter to specific provider (claude, copilot, codex)"),
    extra_dirs: list[str] = typer.Option([], "--dir", "-d", help="Extra directories to scan"),
    host: str = typer.Option(DEFAULT_HOST, help="Server host"),
    port: int = typer.Option(DEFAULT_PORT, help="Server port"),
    skip_existing: bool = typer.Option(True, help="Skip sessions that already have stories"),
    messages: bool = typer.Option(False, "--messages", "-m", help="Also import messages into the database"),
    stories: bool = typer.Option(True, "--stories", "-s", help="Split into weekly files and report gaps needing Storyteller processing"),
    split_dir: Path = typer.Option(DEFAULT_SPLIT_DIR, "--split-dir", help="Directory for weekly split files"),
    recent_days: int | None = typer.Option(None, "--recent-days", help="Import only the last N days in foreground, queue rest in background"),
) -> None:
    """Extract conversation history from AI providers into JSONL."""
    asyncio.run(_import(output, from_file, provider, extra_dirs, host, port, skip_existing, messages, stories, split_dir, recent_days))


async def _import(
    output: Path,
    from_file: Path | None,
    provider: str | None,
    extra_dirs: list[str],
    host: str,
    port: int,
    skip_existing: bool,
    import_messages: bool,
    import_stories: bool,
    split_dir: Path,
    recent_days: int | None = None,
) -> None:
    total_entries = 0
    total_sessions = 0
    provider_stats: dict[str, dict] = {}

    if from_file:
        # Skip extraction, use existing JSONL
        if not from_file.exists():
            typer.echo(f"File not found: {from_file}", err=True)
            raise typer.Exit(1)

        # Count entries in the file
        with open(from_file) as f:
            for line in f:
                if line.strip():
                    total_entries += 1

        # Use the from_file as our output for downstream steps
        output = from_file
        typer.echo(f"Using existing JSONL: {from_file} ({total_entries} entries)")

    else:
        # Auto-discover and extract
        tools_dir = Path(__file__).resolve().parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir))

        try:
            from extract_conversations import (  # ty:ignore[unresolved-import]
                _discover_providers,
                PROVIDER_PROCESSORS,
            )
        except ImportError:
            typer.echo("Can't find tools/extract_conversations.py", err=True)
            raise typer.Exit(1)

        extra_paths = [Path(d) for d in extra_dirs]
        providers = _discover_providers(extra_paths)

        if provider:
            providers = [(name, path) for name, path in providers if name == provider]

        if not providers:
            typer.echo("No provider data found.", err=True)
            raise typer.Exit(1)

        output.parent.mkdir(parents=True, exist_ok=True)

        typer.echo(f"Discovered: {', '.join(f'{name} ({path})' for name, path in providers)}")

        with open(output, "w") as out:
            for provider_name, provider_dir in providers:
                spec = PROVIDER_PROCESSORS.get(provider_name)
                if not spec:
                    continue

                finder, default_processor = spec
                typer.echo(f"\n[{provider_name}] Scanning {provider_dir}")
                found = finder(provider_dir)
                typer.echo(f"[{provider_name}] Found {len(found)} files")

                p_entries = 0
                p_sessions = 0

                for i, item in enumerate(found):
                    if isinstance(item, tuple):
                        file_path, processor = item
                    else:
                        file_path, processor = item, default_processor

                    entries = processor(file_path)
                    if entries:
                        p_sessions += 1
                        for entry in entries:
                            out.write(json.dumps(entry) + "\n")
                            p_entries += 1

                    if (i + 1) % 100 == 0:
                        typer.echo(f"[{provider_name}]   {i + 1}/{len(found)} files...")

                typer.echo(f"[{provider_name}] {p_sessions} sessions, {p_entries} entries")
                provider_stats[provider_name] = {"sessions": p_sessions, "entries": p_entries}
                total_entries += p_entries
                total_sessions += p_sessions

    # Sort JSONL newest-first so recent context gets priority
    _sort_jsonl_newest_first(output)

    # Optionally bulk-import messages into the database
    messages_imported = 0
    messages_skipped = 0

    if import_messages:
        if recent_days is not None:
            # Import recent messages in foreground, older ones in background
            cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(days=recent_days)
            recent_file, older_file = _split_by_date(output, cutoff)

            typer.echo(f"\nImporting recent messages ({recent_days} days) from {recent_file}...")
            recent_imported, recent_skipped = await _import_messages_to_db(recent_file, host, port)
            typer.echo(f"Recent: {recent_imported} imported, {recent_skipped} duplicates skipped")
            messages_imported += recent_imported
            messages_skipped += recent_skipped

            if older_file.exists() and older_file.stat().st_size > 0:
                typer.echo("\nImporting older messages in the background...")
                # Fork a background process for older messages
                import subprocess
                bg_cmd = [
                    "uv", "run", "python", "-m", "charlieverse.cli", "import",
                    "--from-file", str(older_file),
                    "--messages",
                    "--no-stories",
                ]
                subprocess.Popen(
                    bg_cmd,
                    stdout=open(config.logs / "import-bg.log", "w"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                typer.echo("Background import started — log at ~/.charlieverse/logs/import-bg.log")
        else:
            typer.echo(f"\nImporting messages into database from {output}...")
            messages_imported, messages_skipped = await _import_messages_to_db(output, host, port)
            typer.echo(f"Messages: {messages_imported} imported, {messages_skipped} duplicates skipped")

    # Optionally split into weekly files and find gaps
    weeks_needing_stories: list[dict] = []

    if import_stories:
        typer.echo(f"\nSplitting into weekly files at {split_dir}...")
        weekly_files = _split_into_weeks(output, split_dir)
        typer.echo(f"Split into {len(weekly_files)} weekly files")

        # Check which weeks already have stories in the DB
        existing_weeks = await _get_existing_weekly_stories()
        typer.echo(f"Found {len(existing_weeks)} existing weekly stories in DB")

        for week_key, info in sorted(weekly_files.items()):
            if week_key not in existing_weeks:
                weeks_needing_stories.append({
                    "week": week_key,
                    "file": str(info["path"]),
                    "entries": info["count"],
                })

        if weeks_needing_stories:
            typer.echo(f"\n{len(weeks_needing_stories)} weeks need Storyteller processing:")
            for w in weeks_needing_stories:
                typer.echo(f"  {w['week']}: {w['entries']} entries → {w['file']}")
        else:
            typer.echo("\nAll weeks have stories.")

        # Check monthly gaps — any month with weeklies but no monthly
        months_needing_stories = await _get_months_needing_stories()
        if months_needing_stories:
            typer.echo(f"\n{len(months_needing_stories)} months need rollup stories:")
            for m in months_needing_stories:
                typer.echo(f"  {m['month']}: {m['weekly_count']} weekly stories to synthesize")
        else:
            typer.echo("\nAll months have stories.")

        # Check if all-time needs regeneration
        alltime_stale = await _is_alltime_stale()
        if alltime_stale:
            typer.echo(f"\nAll-time story is stale (covers {alltime_stale['covers']}, data extends to {alltime_stale['data_extends_to']})")
        else:
            typer.echo("\nAll-time story is current.")

    # Output summary as JSON to stdout for skill consumption
    summary = {
        "output_file": str(output),
        "total_sessions": total_sessions,
        "total_entries": total_entries,
        "providers": provider_stats,
        "messages_imported": messages_imported,
        "messages_skipped": messages_skipped,
        "weeks_needing_stories": weeks_needing_stories,
        "months_needing_stories": months_needing_stories if import_stories else [],
        "alltime_stale": alltime_stale if import_stories else None,
    }

    typer.echo(f"\nDone. {total_sessions} sessions, {total_entries} entries → {output}")
    typer.echo(f"\n<import_summary>{json.dumps(summary)}</import_summary>")


def _sort_jsonl_newest_first(jsonl_path: Path) -> None:
    """Sort a JSONL file by timestamp descending (newest first)."""
    lines: list[tuple[str, str]] = []  # (sort_key, raw_line)

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp", "")
                lines.append((ts, line))
            except json.JSONDecodeError:
                lines.append(("", line))

    # Sort descending by timestamp
    lines.sort(key=lambda x: x[0], reverse=True)

    with open(jsonl_path, "w") as f:
        for _, line in lines:
            f.write(line + "\n")


def _split_by_date(jsonl_path: Path, cutoff: datetime) -> tuple[Path, Path]:
    """Split a JSONL file into recent (>= cutoff) and older (< cutoff) files."""
    recent_path = jsonl_path.with_suffix(".recent.jsonl")
    older_path = jsonl_path.with_suffix(".older.jsonl")
    cutoff_iso = cutoff.isoformat()

    with open(jsonl_path) as f, \
         open(recent_path, "w") as recent_f, \
         open(older_path, "w") as older_f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp", "")
                if ts >= cutoff_iso:
                    recent_f.write(line + "\n")
                else:
                    older_f.write(line + "\n")
            except json.JSONDecodeError:
                older_f.write(line + "\n")

    return recent_path, older_path


def _deterministic_id(session_id: str, timestamp: str, role: str) -> str:
    """Generate a stable ID from session_id + timestamp + role.

    Makes re-running the import idempotent — same input always produces
    the same ID, so INSERT OR IGNORE naturally dedupes.
    """
    raw = f"{session_id}:{timestamp}:{role}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


async def _import_messages_to_db(
    jsonl_path: Path,
    host: str,
    port: int,
) -> tuple[int, int]:
    """Bulk-import messages from JSONL into the messages table.

    Returns (imported_count, skipped_count).
    """
    db_path = config.database
    imported = 0
    skipped = 0
    batch: list[tuple] = []
    batch_size = 5000

    from charlieverse.db.database import connect

    db = await connect(db_path)
    try:

        with open(jsonl_path) as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                session_id = entry.get("session_id", "")
                role = entry.get("role", "")
                content = entry.get("text", "")
                timestamp = entry.get("timestamp", "")

                if not content or not timestamp:
                    continue

                msg_id = _deterministic_id(session_id, timestamp, role)
                batch.append((msg_id, session_id, role, content, timestamp))

                if len(batch) >= batch_size:
                    result = await _flush_batch(db, batch)
                    imported += result
                    skipped += len(batch) - result
                    batch = []

                    if line_num % 25000 == 0:
                        typer.echo(f"  {line_num} lines processed...")

        # Flush remaining
        if batch:
            result = await _flush_batch(db, batch)
            imported += result
            skipped += len(batch) - result

        # Single FTS rebuild at the end
        typer.echo("  Rebuilding FTS index...")
        await db.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
        await db.commit()
    finally:
        await db.close()

    return imported, skipped

async def total_messages(db: "aiosqlite.Connection") -> int:
    cursor = await db.execute("SELECT COUNT(*) as total FROM messages LIMIT 1")
    row: aiosqlite.Row | None = await cursor.fetchone()
    return row[0] if row else 0

async def _flush_batch(db: "aiosqlite.Connection", batch: list[tuple]) -> int:
    """Insert a batch of messages, returns count of rows inserted."""
    before = await total_messages(db)

    await db.executemany(
        """INSERT OR IGNORE INTO messages (id, session_id, role, content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        batch,
    )
    await db.commit()

    after = await total_messages(db)

    return after - before


# ── Weekly split + story gap detection ─────────────────────────


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp or epoch ms."""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        return None
    return None


def _week_key(dt: datetime) -> str:
    """Return a key like '2025/07/W2' for grouping."""
    week = (dt.day - 1) // 7 + 1
    return f"{dt.strftime('%Y/%m')}/W{week}"


def _split_into_weeks(jsonl_path: Path, output_dir: Path) -> dict[str, dict]:
    """Split JSONL into weekly files. Returns {week_key: {path, count}}."""
    buckets: dict[str, list[str]] = defaultdict(list)

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            dt = _parse_timestamp(obj.get("timestamp"))
            if not dt:
                continue

            key = _week_key(dt)
            buckets[key].append(line)

    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, dict] = {}

    for key in sorted(buckets.keys()):
        entries = buckets[key]
        file_path = output_dir / f"{key}.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as out:
            for entry in entries:
                out.write(entry + "\n")

        result[key] = {"path": file_path, "count": len(entries)}

    return result


async def _get_existing_weekly_stories() -> set[str]:
    """Query the DB for existing weekly stories, return set of week keys.

    Matches week keys like '2025/07/W2' by converting period_start dates.
    """
    from charlieverse.db.database import connect

    db_path = config.database
    existing: set[str] = set()

    db = await connect(db_path)
    try:
        cursor = await db.execute(
            "SELECT period_start, period_end FROM stories WHERE tier = 'weekly'"
        )
        rows = await cursor.fetchall()

        for period_start, _period_end in rows:
            dt = _parse_timestamp(period_start)
            if dt:
                existing.add(_week_key(dt))
    finally:
        await db.close()

    return existing


async def _get_months_needing_stories() -> list[dict]:
    """Find months that have weekly stories but no monthly rollup.

    Returns list of {month: "2025/08", weekly_count: 5}.
    """
    from charlieverse.db.database import connect

    db_path = config.database
    results: list[dict] = []

    db = await connect(db_path)
    try:
        # Get all months that have weekly stories
        cursor = await db.execute(
            "SELECT period_start FROM stories WHERE tier = 'weekly'"
        )
        weekly_rows = await cursor.fetchall()

        months_with_weeklies: dict[str, int] = defaultdict(int)
        for (period_start,) in weekly_rows:
            dt = _parse_timestamp(period_start)
            if dt:
                month_key = dt.strftime("%Y/%m")
                months_with_weeklies[month_key] += 1

        # Get all months that have monthly stories
        cursor = await db.execute(
            "SELECT period_start FROM stories WHERE tier = 'monthly'"
        )
        monthly_rows = await cursor.fetchall()

        months_with_monthlies: set[str] = set()
        for (period_start,) in monthly_rows:
            dt = _parse_timestamp(period_start)
            if dt:
                months_with_monthlies.add(dt.strftime("%Y/%m"))

        # Diff
        for month_key in sorted(months_with_weeklies):
            if month_key not in months_with_monthlies:
                results.append({
                    "month": month_key,
                    "weekly_count": months_with_weeklies[month_key],
                })
    finally:
        await db.close()

    return results


async def _is_alltime_stale() -> dict | None:
    """Check if the all-time story is missing or doesn't cover the full data range.

    Returns {covers: "2025-11 to 2026-03", data_extends_to: "2025-06"} or None.
    """
    from charlieverse.db.database import connect

    db_path = config.database

    db = await connect(db_path)
    try:
        # Get earliest weekly story date
        cursor = await db.execute(
            "SELECT MIN(period_start) FROM stories WHERE tier = 'weekly'"
        )
        row = await cursor.fetchone()
        earliest_weekly = row[0] if row else None

        if not earliest_weekly:
            return None

        # Get all-time story
        cursor = await db.execute(
            "SELECT period_start, period_end FROM stories WHERE tier = 'all-time' LIMIT 1"
        )
        alltime = await cursor.fetchone()

        if not alltime:
            return {
                "covers": "none",
                "data_extends_to": earliest_weekly[:7],
            }

        alltime_start = alltime[0]

        # If all-time starts later than earliest weekly, it's stale
        if alltime_start > earliest_weekly:
            return {
                "covers": f"{alltime_start[:7]} to {alltime[1][:7]}",
                "data_extends_to": earliest_weekly[:7],
            }
    finally:
        await db.close()

    return None
