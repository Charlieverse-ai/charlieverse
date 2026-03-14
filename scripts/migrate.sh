#!/usr/bin/env bash
# Migrate old Charlieverse database to new Python format.
# Usage: ./scripts/migrate.sh [path-to-old-db]
#
# Default old path: ~/.charlie/profiles/default/db/charlie.db

set -euo pipefail

OLD_DB="${1:-$HOME/.charlie/profiles/default/db/charlie.db}"

if [ ! -f "$OLD_DB" ]; then
    echo "Error: Old database not found at $OLD_DB"
    echo "Usage: ./scripts/migrate.sh [path-to-old-db]"
    exit 1
fi

echo "Migrating from: $OLD_DB"
uv run python tools/migrate.py --old "$OLD_DB"
