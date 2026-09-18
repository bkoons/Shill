#!/usr/bin/env bash
# SQLite backup with the safe .backup API (consistent copy under WAL).
# Usage: scripts/backup_db.sh [keep_count]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="${SHILL_DB_PATH:-$ROOT/data/shill.db}"
BACKUP_DIR="${SHILL_BACKUP_DIR:-$ROOT/data/backups}"
KEEP="${1:-7}"

if [ ! -f "$DB_PATH" ]; then
  echo "backup: no database at $DB_PATH — nothing to do" >&2
  exit 0
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
DEST="$BACKUP_DIR/shill-$STAMP.db"

python3 - "$DB_PATH" "$DEST" <<'PYEOF'
import sqlite3, sys
src, dest = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as conn:
    dest_conn = sqlite3.connect(dest)
    conn.backup(dest_conn)
    dest_conn.close()
print(f"backup: wrote {dest}")
PYEOF

# Retention: keep newest N
ls -1t "$BACKUP_DIR"/shill-*.db 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f
echo "backup: retained last $KEEP in $BACKUP_DIR"
