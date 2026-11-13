"""Offline restoration. Stop the app and backup scheduler before running."""
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import backup_database

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage : python scripts/restore.py sauvegarde.sqlite3")
    source = Path(sys.argv[1]).resolve()
    destination = Path(os.environ.get("SLOVO_DATA_DIR", Path(__file__).resolve().parents[1] / "instance")) / "slovo.sqlite3"
    if source == destination.resolve() or not source.is_file():
        raise SystemExit("Choisir une sauvegarde existante différente de la base cible.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    temporary = destination.with_suffix(f".restore-{stamp}.sqlite3")
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as incoming:
        if incoming.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit("Sauvegarde endommagée : restauration refusée.")
        if not incoming.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'").fetchone():
            raise SystemExit("Ce fichier ne contient pas une base Slovo.")
        backup_database(incoming, temporary)
    if destination.exists():
        with closing(sqlite3.connect(destination)) as current:
            backup_database(current, destination.with_suffix(f".before-restore-{stamp}.sqlite3"))
    os.replace(temporary, destination)
    if hasattr(os, "chown") and os.getuid() == 0:
        os.chown(destination, 10001, 10001)
    print("Base restaurée. Les données précédentes ont été conservées si elles existaient.")
