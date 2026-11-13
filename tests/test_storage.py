import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from storage import initialize

ROOT = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def test_full_legacy_migration_is_atomic_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.sqlite3"
            with closing(sqlite3.connect(path)) as db:
                db.executescript("""
                    CREATE TABLE settings(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT);
                    INSERT INTO settings VALUES(1,'Ancien profil');
                    CREATE TABLE mastery(word_id INTEGER PRIMARY KEY,chain INTEGER,favorite INTEGER);
                    INSERT INTO mastery VALUES(17,4,1);
                    CREATE TABLE runs(id TEXT PRIMARY KEY,questions TEXT,xp INTEGER,finished TEXT);
                    INSERT INTO runs VALUES('historique','[]',99,'2026-11-01');
                    CREATE TABLE answers(id INTEGER PRIMARY KEY,run_id TEXT,position INTEGER,xp INTEGER);
                    INSERT INTO answers VALUES(31,'historique',0,99);
                """)
                with patch("storage.SCHEMA", "INVALID SQL"):
                    with self.assertRaises(sqlite3.OperationalError):
                        initialize(db, path)
                self.assertEqual(db.execute("SELECT name FROM settings").fetchone()[0], "Ancien profil")
                self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone())
                initialize(db, path)
                self.assertEqual(db.execute("SELECT user_id,chain,favorite FROM mastery").fetchone(), (1,4,1))
                self.assertEqual(db.execute("SELECT user_id,xp FROM runs").fetchone(), (1,99))
                self.assertEqual(db.execute("SELECT id,user_id,xp FROM answers").fetchone(), (31,1,99))
                db.execute("INSERT INTO users(username,password_hash,created) VALUES('second','hash','now')")
                second = db.execute("SELECT id FROM users WHERE username='second'").fetchone()[0]
                db.execute("INSERT INTO settings(id) VALUES(?)", (second,))
                db.execute("INSERT INTO mastery(user_id,word_id,chain) VALUES(?,17,1)", (second,))
                db.commit()
                initialize(db, path)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM answers").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM mastery").fetchone()[0], 2)

    def test_offline_restore_keeps_previous_data_and_rejects_invalid_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            snapshot = path / "snapshot.sqlite3"
            destination = path / "data" / "slovo.sqlite3"
            destination.parent.mkdir()
            for file, name in ((snapshot, "Sauvegarde"), (destination, "Avant restauration")):
                with closing(sqlite3.connect(file)) as db:
                    initialize(db, file)
                    db.execute("UPDATE settings SET name=? WHERE id=1", (name,))
                    db.commit()
            environment = {**os.environ, "SLOVO_DATA_DIR": str(destination.parent)}
            result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/restore.py"), str(snapshot)],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute("SELECT name FROM settings").fetchone()[0], "Sauvegarde")
            previous = list(destination.parent.glob("*.before-restore-*.sqlite3"))
            self.assertEqual(len(previous), 1)
            with closing(sqlite3.connect(previous[0])) as db:
                self.assertEqual(db.execute("SELECT name FROM settings").fetchone()[0], "Avant restauration")
            invalid = path / "invalid.sqlite3"
            with closing(sqlite3.connect(invalid)) as db:
                db.execute("CREATE TABLE unrelated(id INTEGER)")
                db.commit()
            result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts/restore.py"), str(invalid)],
                                    env=environment, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            with closing(sqlite3.connect(destination)) as db:
                self.assertEqual(db.execute("SELECT name FROM settings").fetchone()[0], "Sauvegarde")


if __name__ == "__main__":
    unittest.main()
