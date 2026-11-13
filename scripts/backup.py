"""Scheduled backup: python scripts/backup.py [directory], on the server."""
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import backup_database

if __name__ == "__main__":
    database = Path(os.environ.get("SLOVO_DATA_DIR", Path(__file__).resolve().parents[1] / "instance")) / "slovo.sqlite3"
    if not database.is_file():
        raise SystemExit("Base introuvable : " + str(database))
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "backups")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        print(backup_database(source, folder / f"slovo-{stamp}.sqlite3"))
