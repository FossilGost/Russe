import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app import BY_ID, create_app

PASSWORD = "Une longue phrase secrete 123"


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "accounts.sqlite3"
        self.config = {"TESTING": True, "DATABASE": str(self.path), "SECRET_KEY": "test-key-that-is-stable-across-restarts"}
        self.app = create_app(self.config)
        self.a = self.app.test_client()
        self.b = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def token(self, client):
        client.get("/login")
        with client.session_transaction() as state:
            return state["csrf"]

    def post(self, client, path, **data):
        with client.session_transaction() as state:
            token = state.get("csrf")
        if not token:
            token = self.token(client)
        return client.post(path, data={"csrf": token, **data})

    def register(self, client, username):
        response = self.post(client, "/register", username=username, password=PASSWORD, confirmation=PASSWORD)
        self.assertEqual(response.status_code, 302, response.get_data(as_text=True))

    def export(self, client):
        return client.get("/export").get_json()

    def test_anonymous_cannot_access_data_or_change_anything(self):
        for route in ("/", "/export", "/progress", "/settings", "/vocabulary", "/courses", "/audio/1"):
            response = self.a.get(route)
            self.assertEqual(response.status_code, 302, route)
            self.assertTrue(response.location.endswith("/login"))
        self.assertEqual(self.a.get("/health").get_json(), {"status": "ok"})
        self.assertEqual(self.a.post("/settings/interface", data={"volume": 42}).status_code, 401)
        self.assertEqual(self.a.post("/register", data={"username": "evil"}).status_code, 400)
        self.assertEqual(self.a.post("/register", data={"csrf": "é"}).status_code, 400)
        self.assertEqual(self.a.get("/logout").status_code, 405)

    def test_registration_validation_and_password_hashing(self):
        for username, password, confirmation in (("a", PASSWORD, PASSWORD), ("valid", "short", "short"),
                                                   ("valid", PASSWORD, "different"), ("<script>", PASSWORD, PASSWORD)):
            response = self.post(self.a, "/register", username=username, password=password, confirmation=confirmation)
            self.assertEqual(response.status_code, 200)
            self.assertIn('role="alert"', response.get_data(as_text=True))
        self.register(self.a, "Alice")
        self.assertEqual(self.export(self.a)["username"], "alice")
        with closing(sqlite3.connect(self.path)) as db:
            stored = db.execute("SELECT password_hash FROM users WHERE username='alice'").fetchone()[0]
            self.assertTrue(stored.startswith("scrypt:"))
            self.assertNotIn(PASSWORD, stored)
        response = self.post(self.b, "/register", username="ALICE", password=PASSWORD, confirmation=PASSWORD)
        self.assertIn("pas disponible", response.get_data(as_text=True))

    def test_two_users_are_isolated_and_session_resumes_on_other_device(self):
        self.register(self.a, "alice")
        self.register(self.b, "bob")
        self.post(self.a, "/settings", name="Alice privée", goal=150, length=5, theme="full-dark", voice="dmitry", speech_rate="slow", strict="on")
        self.post(self.a, "/settings/interface", volume=37, keyboard_open=1)
        self.post(self.a, "/favorite/1")
        self.post(self.a, "/courses/alphabet/complete")
        self.post(self.a, "/start", mode="copy")
        run = self.export(self.a)["runs"][0]
        question = json.loads(run["questions"])[0]
        self.post(self.a, "/answer", run_id=run["id"], position=0, answer=BY_ID[question["word_id"]]["ru"])
        first = self.export(self.a)
        second = self.export(self.b)
        self.assertGreater(first["stats"]["xp"], 0)
        self.assertEqual(second["stats"]["xp"], 0)
        self.assertEqual(second["words"], [])
        self.assertEqual(second["courses"], [])
        self.assertEqual(second["runs"], [])
        self.assertEqual(second["settings"]["volume"], 100)
        self.assertEqual(second["settings"]["theme"], "normal")
        # Even a valid signed session pointing at another run cannot read/score it.
        with self.b.session_transaction() as state:
            state["run_id"] = run["id"]
        self.post(self.b, "/answer", run_id=run["id"], position=0, answer="injection")
        self.post(self.b, "/next", run_id=run["id"], position=0)
        self.assertEqual(self.export(self.a)["runs"][0]["position"], 0)
        self.assertEqual(self.export(self.b)["words"], [])
        other_device = create_app(self.config).test_client()
        self.post(other_device, "/login", username="alice", password=PASSWORD)
        restored = self.export(other_device)
        self.assertEqual(restored["stats"], first["stats"])
        self.assertEqual(restored["settings"]["volume"], 37)
        self.assertEqual(restored["settings"]["keyboard_open"], 1)
        self.assertEqual(restored["courses"][0]["slug"], "alphabet")
        self.assertEqual(other_device.get("/practice").status_code, 200)
        self.assertIn("Bien joué", other_device.get("/practice").get_data(as_text=True))
        self.assertNotIn("password_hash", json.dumps(restored))

    def test_password_change_logout_and_operator_reset_revoke_sessions(self):
        self.register(self.a, "alice")
        self.post(self.b, "/login", username="alice", password=PASSWORD)
        self.assertEqual(self.b.get("/export").status_code, 200)
        new_password = "Une nouvelle phrase secrete 456"
        self.post(self.a, "/account/password", current_password="wrong", password=new_password, confirmation=new_password)
        self.assertEqual(self.b.get("/export").status_code, 200)
        self.post(self.a, "/account/password", current_password=PASSWORD, password=new_password, confirmation=new_password)
        self.assertEqual(self.b.get("/export").status_code, 302)
        self.assertEqual(self.a.get("/export").status_code, 200)
        cookie = self.a.get_cookie("session").value
        self.post(self.a, "/logout")
        self.a.set_cookie("session", cookie)
        self.assertEqual(self.a.get("/export").status_code, 302)
        self.post(self.a, "/login", username="alice", password=PASSWORD)
        self.assertEqual(self.a.get("/export").status_code, 302)
        self.post(self.a, "/login", username="alice", password=new_password)
        result = self.app.test_cli_runner().invoke(args=["reset-password", "alice"], input=PASSWORD + "\n" + PASSWORD + "\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self.a.get("/export").status_code, 302)

    def test_csrf_rotates_and_protects_account_and_interface_actions(self):
        old_token = self.token(self.a)
        self.register(self.a, "alice")
        with self.a.session_transaction() as state:
            self.assertNotEqual(old_token, state["csrf"])
        for path in ("/logout", "/account/password", "/settings/interface", "/courses/alphabet/complete"):
            self.assertEqual(self.a.post(path, data={"csrf": old_token}).status_code, 400)
        self.assertEqual(self.post(self.a, "/settings/interface", volume=101).status_code, 400)
        self.assertEqual(self.post(self.a, "/settings/interface", keyboard_open=2).status_code, 400)
        self.assertEqual(self.post(self.a, "/settings/interface", volume="NaN").status_code, 400)
        self.assertEqual(self.post(self.a, "/courses/absent/complete").status_code, 404)

    def test_persistent_login_rate_limit(self):
        for _ in range(10):
            response = self.post(self.a, "/login", username="unknown", password=PASSWORD)
            self.assertEqual(response.status_code, 200)
        client = create_app(self.config).test_client()
        response = self.post(client, "/login", username="unknown", password=PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_production_configuration_and_security_headers(self):
        with self.assertRaises(RuntimeError):
            create_app({**self.config, "PRODUCTION": True, "SECRET_KEY": None})
        with self.assertRaises(RuntimeError):
            create_app({**self.config, "PRODUCTION": True, "TRUSTED_HOSTS": None})
        production = create_app({**self.config, "PRODUCTION": True, "SESSION_COOKIE_SECURE": True, "TRUSTED_HOSTS": ["slovo.example"]})
        response = production.test_client().get("/login", base_url="https://slovo.example")
        self.assertEqual(response.status_code, 200)
        for flag in ("Secure", "HttpOnly", "SameSite=Lax"):
            self.assertIn(flag, response.headers["Set-Cookie"])
        self.assertIn("Strict-Transport-Security", response.headers)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(production.test_client().get("/health", base_url="https://evil.example").status_code, 400)

    def test_backup_restores_every_account_without_password_disclosure(self):
        self.register(self.a, "alice")
        self.post(self.a, "/settings/interface", volume=23)
        self.post(self.a, "/favorite/1")
        self.post(self.a, "/courses/alphabet/complete")
        target = Path(self.tmp.name) / "snapshot.sqlite3"
        result = self.app.test_cli_runner().invoke(args=["backup", str(target)])
        self.assertEqual(result.exit_code, 0, result.output)
        again = self.app.test_cli_runner().invoke(args=["backup", str(target)])
        self.assertNotEqual(again.exit_code, 0)
        restored = create_app({**self.config, "DATABASE": str(target)}).test_client()
        self.post(restored, "/login", username="alice", password=PASSWORD)
        profile = self.export(restored)
        self.assertEqual(profile["settings"]["volume"], 23)
        self.assertEqual(profile["words"][0]["favorite"], 1)
        self.assertEqual(profile["courses"][0]["slug"], "alphabet")

    def test_registration_can_be_closed(self):
        closed = create_app({**self.config, "ALLOW_REGISTRATION": False}).test_client()
        self.assertEqual(closed.get("/register").status_code, 403)


if __name__ == "__main__":
    unittest.main()
