"""SQLite schema, transactional legacy migration and consistent backups."""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
from security import create_private_file

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
 auth_version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings (
 id INTEGER PRIMARY KEY REFERENCES users(id), name TEXT DEFAULT 'Explorateur',
 goal INTEGER DEFAULT 50, length INTEGER DEFAULT 10, strict INTEGER DEFAULT 0,
 sound INTEGER DEFAULT 1, theme TEXT NOT NULL DEFAULT 'normal',
 voice TEXT NOT NULL DEFAULT 'svetlana', speech_rate TEXT NOT NULL DEFAULT 'normal',
 browser_voice TEXT NOT NULL DEFAULT '', volume INTEGER NOT NULL DEFAULT 100,
 keyboard_open INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS mastery (
 user_id INTEGER NOT NULL REFERENCES users(id), word_id INTEGER NOT NULL,
 attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, chain INTEGER DEFAULT 0,
 due TEXT, favorite INTEGER DEFAULT 0, PRIMARY KEY(user_id, word_id));
CREATE TABLE IF NOT EXISTS runs (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), mode TEXT,
 category TEXT, questions TEXT, position INTEGER DEFAULT 0, xp INTEGER DEFAULT 0,
 correct INTEGER DEFAULT 0, combo INTEGER DEFAULT 0, feedback TEXT, started TEXT, finished TEXT);
CREATE TABLE IF NOT EXISTS answers (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), run_id TEXT,
 position INTEGER, word_id INTEGER, correct INTEGER, xp INTEGER, day TEXT,
 UNIQUE(run_id, position));
CREATE TABLE IF NOT EXISTS course_progress (
 user_id INTEGER NOT NULL REFERENCES users(id), slug TEXT NOT NULL,
 completed TEXT NOT NULL, PRIMARY KEY(user_id, slug));
CREATE TABLE IF NOT EXISTS auth_limits (
 key TEXT PRIMARY KEY, started REAL NOT NULL, attempts INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS answers_user_day ON answers(user_id, day);
CREATE INDEX IF NOT EXISTS runs_user_started ON runs(user_id, started);
CREATE INDEX IF NOT EXISTS auth_limits_started ON auth_limits(started);
"""


def backup_database(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # O_EXCL rejects existing paths, including dangling symbolic links.
    descriptor = create_private_file(destination)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("La vérification de la sauvegarde a échoué.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def initialize(connection, path):
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    legacy = "settings" in tables and "users" not in tables
    if legacy:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_database(connection, Path(path).with_suffix(f".pre-accounts-{stamp}.sqlite3"))
    connection.execute("BEGIN IMMEDIATE")
    try:
        if legacy:
            for table in ("settings", "mastery", "runs", "answers"):
                if table in tables:
                    connection.execute(f"ALTER TABLE {table} RENAME TO legacy_{table}")
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.execute(statement)
        connection.execute("INSERT OR IGNORE INTO users(id,created) VALUES(1,?)",
                           (datetime.now(timezone.utc).isoformat(),))
        if legacy:
            for table in ("settings", "mastery", "runs", "answers"):
                if table not in tables:
                    continue
                old_columns = [r[1] for r in connection.execute(f"PRAGMA table_info(legacy_{table})")]
                new_columns = {r[1] for r in connection.execute(f"PRAGMA table_info({table})")}
                columns = [c for c in old_columns if c in new_columns]
                names = ",".join(columns)
                if table == "settings":
                    # Names are intersected with columns from our fixed SCHEMA above.
                    connection.execute(f"INSERT INTO settings({names}) SELECT {names} FROM legacy_settings WHERE id=1")  # nosec B608
                else:
                    # Table allowlist and fixed-schema column intersection above.
                    connection.execute(f"INSERT INTO {table}(user_id,{names}) SELECT 1,{names} FROM legacy_{table}")  # nosec B608
                connection.execute(f"DROP TABLE legacy_{table}")
        connection.execute("INSERT OR IGNORE INTO settings(id) VALUES(1)")
        connection.execute("PRAGMA user_version=1")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
