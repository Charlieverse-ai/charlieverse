#!/usr/bin/env python3
"""Split a combined conversations.jsonl into weekly files organized by year/month.

Takes the output of extract_conversations.py and groups entries by week,
creating a directory structure suitable for tiered Storyteller processing.

Usage:
    python tools/split_conversations.py [input_file] [output_dir]

Defaults:
    input_file:  ./conversations.jsonl
    output_dir:  ./conversations/

Output structure:
    conversations/
      2025/
        07/
          W1.jsonl    (Jul 1-6)
          W2.jsonl    (Jul 7-13)
          ...
        08/
          W1.jsonl
      2026/
        02/
          W1.jsonl
          W2.jsonl
          W3.jsonl
          W4.jsonl
        03/
          W1.jsonl
          W2.jsonl
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp or epoch ms."""
    if not ts:
        return None
    try:
        # ISO format
        if isinstance(ts, str):
            # Handle various ISO formats
            ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        # Epoch ms
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        return None
    return None


def _week_of_month(dt: datetime) -> int:
    """Get the week number within the month (1-indexed)."""
    return (dt.day - 1) // 7 + 1


def main():
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("conversations.jsonl")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("conversations")

    if not input_file.exists():
        print(f"Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Group entries by year/month/week
    buckets: dict[str, list[str]] = defaultdict(list)
    total = 0
    skipped = 0

    with open(input_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            dt = _parse_timestamp(obj.get("timestamp"))
            if not dt:
                skipped += 1
                continue

            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            week = _week_of_month(dt)
            key = f"{year}/{month}/W{week}"
            buckets[key].append(line)

    # Write files
    output_dir.mkdir(parents=True, exist_ok=True)
    files_written = 0

    for key in sorted(buckets.keys()):
        entries = buckets[key]
        file_path = output_dir / f"{key}.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w") as out:
            for entry in entries:
                out.write(entry + "\n")

        files_written += 1

    print(f"Split {total} entries into {files_written} weekly files")
    if skipped:
        print(f"  Skipped {skipped} entries (no timestamp or parse error)")
    print(f"  Output: {output_dir}/")

    # Summary
    print(f"\nBreakdown:")
    for key in sorted(buckets.keys()):
        print(f"  {key}: {len(buckets[key])} entries")


if __name__ == "__main__":
    main()
