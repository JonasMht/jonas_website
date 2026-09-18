#!/usr/bin/env python3
"""WAL-safe SQLite backup (7-day weekday rotation)."""
import sqlite3, datetime, pathlib, sys
DB = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/home/jonas/jonasx/telemetry/telemetry.db")
DIR = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else str(DB.parent / "backups"))
DIR.mkdir(parents=True, exist_ok=True)
out = DIR / ("telemetry-" + datetime.date.today().strftime("%a") + ".db")
src = sqlite3.connect(str(DB))
dst = sqlite3.connect(str(out))
src.backup(dst)
dst.close(); src.close()
print("backed up:", out)
