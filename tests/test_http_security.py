"""Real local Waitress requests; TLS termination itself is a deployment check."""
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from waitress import create_server
from app import create_app


class HTTPTests(unittest.TestCase):
    def test_production_proxy_headers_and_transport_on_real_wsgi_server(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"SLOVO_PROXY": "1"}):
                app = create_app({"TESTING": True, "PRODUCTION": True,
                                  "SECRET_KEY": "temporary-test-key-for-http-verification-only",
                                  "DATABASE": str(Path(folder) / "http.sqlite3"),
                                  "TRUSTED_HOSTS": ["slovo.example"]})
            server = create_server(app, host="127.0.0.1", port=0,
                                   clear_untrusted_proxy_headers=False, expose_tracebacks=False)
            worker = threading.Thread(target=server.run, daemon=True)
            worker.start()
            base = "http://127.0.0.1:" + str(server.effective_port)
            try:
                request = urllib.request.Request(base + "/login", headers={"Host": "slovo.example"})
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(raised.exception.code, 400)
                raised.exception.close()
                request = urllib.request.Request(base + "/login", headers={"Host": "slovo.example", "X-Forwarded-Proto": "https"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn("__Host-slovo=", response.headers["Set-Cookie"])
                    self.assertIn("Secure", response.headers["Set-Cookie"])
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    self.assertIn("Strict-Transport-Security", response.headers)
                    response.read()
            finally:
                server.task_dispatcher.shutdown()
                server.close()
                worker.join(timeout=5)
