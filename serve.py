"""Run the production WSGI server (Windows and Linux)."""
import os

from waitress import serve
# Keep newly created database journals and other private files owner-only on Unix.
os.umask(0o077)
from wsgi import app

if __name__ == "__main__":
    # Proxy headers are passed through only on the private Caddy/app network.
    serve(app, host=os.environ.get("HOST", "127.0.0.1"),
          port=int(os.environ.get("PORT", "8080")), threads=max(1,min(32,int(os.environ.get("SLOVO_THREADS", "4")))),
          clear_untrusted_proxy_headers=os.environ.get("SLOVO_PROXY") != "1",
          max_request_body_size=16384, max_request_header_size=16384,
          connection_limit=100, cleanup_interval=5, channel_timeout=30,
          expose_tracebacks=False)
