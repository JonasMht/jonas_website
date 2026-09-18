#!/usr/bin/env bash
# Safe SQLite backup: uses the .backup API (WAL-safe), keeps 7 daily copies.
# Usage: backup-telemetry.sh [db_path] [backup_dir]
set -euo pipefail
DB="${1:-$HOME/jonasx/telemetry/telemetry.db}"
DIR="${2:-$HOME/jonasx/telemetry/backups}"
mkdir -p "$DIR"
TAG=$(date +%a)
if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB" ".backup '$DIR/telemetry-$TAG.db'"
else
    # no sqlite3 CLI — copy db + wal + shm together (reads require a brief lock)
    cp "$DB" "$DIR/telemetry-$TAG.db"
    for ext in wal shm; do
        [ -f "$DB-$ext" ] && cp "$DB-$ext" "$DIR/telemetry-$TAG.db-$ext"
    done
fi
echo "backed up: $DIR/telemetry-$TAG.db"
