"""Security regression checks against temporary databases only."""
import os
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app
from security import PASSWORD_METHOD, PASSWORD_SLOTS
from speech import GENERATION_SLOTS, AudioBusy, generate_audio
from storage import backup_database

PASSWORD = "Une phrase privee pour les tests 123"


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "security.sqlite3"
        self.config = {"TESTING": True, "DATABASE": str(self.path),
                       "SECRET_KEY": "test-secret-used-only-for-temporary-databases"}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, client, url, **data):
        with client.session_transaction() as state:
            token = state.get("csrf")
        if not token:
            client.get("/login")
            with client.session_transaction() as state:
                token = state["csrf"]
        return client.post(url, data={"csrf": token, **data})

    def register(self, client, username="alice"):
        result = self.post(client, "/register", username=username, password=PASSWORD, confirmation=PASSWORD)
        self.assertEqual(result.status_code, 302)

    def test_sql_injection_and_stored_xss_remain_literal_text(self):
        response = self.post(self.client, "/login", username="' OR 1=1 --", password=PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/export").status_code, 302)
        self.register(self.client)
        for payload in ("x'; DROP TABLE users; --", '\"><svg/onload=alert(1)>'):
            self.post(self.client, "/settings", name=payload, goal=50, length=10)
            exported = self.client.get("/export").get_json()
            self.assertEqual(exported["settings"]["name"], payload)
            body = self.client.get("/").get_data(as_text=True)
            self.assertNotIn('<svg/onload=alert(1)>', body)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users WHERE username='alice'").fetchone()[0], 1)

    def test_absolute_session_age_is_not_extended_by_activity(self):
        now = time.time()
        with patch("time.time", return_value=now):
            self.register(self.client)
        with patch("time.time", return_value=now + 6 * 86400):
            self.assertEqual(self.post(self.client, "/start", mode="copy").status_code, 302)
        # The cookie was just re-signed on day 6, but authentication began on day 0.
        with patch("time.time", return_value=now + 8 * 86400):
            self.assertEqual(self.client.get("/export").status_code, 302)

    def test_signed_session_cannot_be_tampered_with(self):
        self.register(self.client)
        cookie = self.client.get_cookie("session").value
        parts = cookie.split(".")
        parts[-1] = ("A" if parts[-1][0] != "A" else "B") + parts[-1][1:]
        self.client.set_cookie("session", ".".join(parts))
        self.assertEqual(self.client.get("/export").status_code, 302)

    def test_production_rejects_plain_http_and_untrusted_hosts(self):
        app = create_app({**self.config, "PRODUCTION": True, "TRUSTED_HOSTS": ["slovo.example"],
                          "SESSION_COOKIE_SECURE": False, "DEBUG": True})
        client = app.test_client()
        for method in ("GET", "POST"):
            self.assertEqual(client.open("/login", method=method, base_url="http://slovo.example").status_code, 400)
        response = client.get("/login", base_url="https://slovo.example")
        self.assertEqual(response.status_code, 200)
        self.assertIn("__Host-slovo=", response.headers["Set-Cookie"])
        self.assertIn("Secure", response.headers["Set-Cookie"])
        self.assertFalse(app.debug)
        self.assertEqual(client.get("/health", base_url="http://slovo.example").status_code, 200)
        self.assertEqual(client.get("/login", base_url="https://evil.example").status_code, 400)
        with self.assertRaises(RuntimeError):
            create_app({**self.config, "PRODUCTION": True, "TRUSTED_HOSTS": [".example.com"]})
        # Untrusted forwarding headers cannot turn direct HTTP into HTTPS.
        self.assertEqual(client.get("/login", base_url="http://slovo.example",
                                    headers={"X-Forwarded-Proto": "https"}).status_code, 400)

    def test_private_files_are_not_served_even_with_path_traversal(self):
        for path in ("/instance/slovo.sqlite3", "/instance/secret.key", "/.env", "/.git/config",
                     "/backups/slovo.sqlite3", "/static/../instance/slovo.sqlite3",
                     "/static/%2e%2e/instance/secret.key", "/static/%2e%2e%5cinstance%5csecret.key"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_private_responses_and_errors_are_not_shared_in_caches(self):
        for path in ("/audio/1", "/login", "/export"):
            response = self.client.get(path)
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.register(self.client)
        fixture = Path(self.tmp.name) / "sample.mp3"
        fixture.write_bytes(b"ID3-test")
        with patch("app.generate_audio", return_value=fixture):
            with self.client.get("/audio/1") as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertIn("Cookie", response.headers["Vary"])

    def test_public_assets_and_readiness_do_not_set_session_cookies(self):
        for path in ("/static/style.css", "/health"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("Set-Cookie", response.headers)

    def test_client_user_id_cannot_target_another_account(self):
        self.register(self.client, "alice")
        self.post(self.client, "/settings", name="CONFIDENTIEL_ALICE", goal=150, length=10)
        self.post(self.client, "/start", mode="copy")
        alice = self.client.get("/export").get_json()
        bob = self.app.test_client()
        self.register(bob, "bob")
        self.post(bob, "/settings/interface", user_id=alice["settings"]["id"], volume=7)
        self.post(bob, "/next", run_id=alice["runs"][0]["id"], position=0)
        for url in ("/", "/settings", "/progress", "/export?user_id=" + str(alice["settings"]["id"])):
            self.assertNotIn("CONFIDENTIEL_ALICE", bob.get(url).get_data(as_text=True))
        self.assertEqual(self.client.get("/export").get_json()["settings"]["volume"], 100)

    def test_weak_new_passwords_rejected_and_legacy_hashes_upgraded(self):
        response = self.post(self.client, "/register", username="alice", password="a" * 14, confirmation="a" * 14)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/export").status_code, 302)
        self.register(self.client)
        old_hash = generate_password_hash(PASSWORD, method="scrypt:32768:8:1")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE users SET password_hash=? WHERE username='alice'", (old_hash,))
            db.commit()
        self.post(self.client, "/logout")
        self.post(self.client, "/login", username="alice", password="incorrect")
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone()[0], old_hash)
        self.post(self.client, "/login", username="alice", password=PASSWORD)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertTrue(db.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone()[0].startswith(PASSWORD_METHOD + "$"))

    def test_payload_size_csrf_and_mass_assignment_are_rejected(self):
        self.client.get("/login")
        self.assertEqual(self.client.post("/login", data={"password": "x" * 17000}).status_code, 413)
        self.register(self.client)
        self.assertEqual(self.client.post("/settings/interface", json={"volume": 0}).status_code, 400)
        self.assertEqual(self.post(self.client, "/settings/interface", auth_version=999, id=1).status_code, 400)
        self.assertEqual(self.post(self.client, "/settings/interface", volume="0; DROP TABLE users").status_code, 400)

    def test_work_limits_preserve_data_and_return_retry_after(self):
        self.register(self.client)
        for _ in range(30):
            self.assertEqual(self.post(self.client, "/start", mode="copy").status_code, 302)
        response = self.post(self.client, "/start", mode="copy")
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 30)

    def test_password_and_audio_expensive_work_is_bounded(self):
        self.register(self.client)
        self.post(self.client, "/logout")
        PASSWORD_SLOTS.acquire()
        PASSWORD_SLOTS.acquire()
        try:
            result = self.post(self.client, "/login", username="alice", password=PASSWORD)
            self.assertEqual(result.status_code, 503)
            self.assertIn("Retry-After", result.headers)
        finally:
            PASSWORD_SLOTS.release()
            PASSWORD_SLOTS.release()
        GENERATION_SLOTS.acquire()
        GENERATION_SLOTS.acquire()
        try:
            with self.assertRaises(AudioBusy):
                generate_audio("тест", "svetlana", "normal", Path(self.tmp.name) / "cache")
        finally:
            GENERATION_SLOTS.release()
            GENERATION_SLOTS.release()

    def test_backup_is_exclusive_and_owner_only_on_unix(self):
        target = Path(self.tmp.name) / "private.sqlite3"
        with closing(sqlite3.connect(self.path)) as db:
            backup_database(db, target)
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                backup_database(db, target)
            self.assertEqual(target.read_bytes(), original)
        if os.name == "posix":
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
