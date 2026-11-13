"""Shared resource limits and private-file creation, without user-controlled SQL."""
import hashlib
import hmac
import os
import time
from contextlib import contextmanager
from pathlib import Path
from threading import BoundedSemaphore

from flask import abort, make_response

# Public KDF parameters, not a password or a secret.
PASSWORD_METHOD = "scrypt:32768:8:3"  # nosec B105
MIN_PASSWORD_LENGTH = 15
PASSWORD_SLOTS = BoundedSemaphore(2)


@contextmanager
def password_slot():
    if not PASSWORD_SLOTS.acquire(blocking=False):
        response = make_response("Connexion momentanément occupée. Réessaie dans quelques secondes.", 503)
        response.headers["Retry-After"] = "5"
        abort(response)
    try:
        yield
    finally:
        PASSWORD_SLOTS.release()


def rate_limit(db, secret, scope, identity, limit, seconds):
    secret = secret.encode() if isinstance(secret, str) else secret
    key = hmac.new(secret, f"{scope}|{identity}".encode(), hashlib.sha256).hexdigest()
    now = time.time()
    db.execute("DELETE FROM auth_limits WHERE started<?", (now - 86400,))
    db.execute("""INSERT INTO auth_limits(key,started,attempts) VALUES(?,?,1)
        ON CONFLICT(key) DO UPDATE SET
        attempts=CASE WHEN started<? THEN 1 ELSE attempts+1 END,
        started=CASE WHEN started<? THEN excluded.started ELSE started END""",
               (key, now, now-seconds, now-seconds))
    row = db.execute("SELECT started,attempts FROM auth_limits WHERE key=?", (key,)).fetchone()
    db.commit()
    if row[1] > limit:
        response = make_response("Trop de tentatives. Patiente avant de réessayer.", 429)
        response.headers["Retry-After"] = str(max(1, int(row[0] + seconds - now) + 1))
        abort(response)


def private_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)
    return path


def create_private_file(path):
    """Exclusive creation: never follow an existing file or symlink."""
    return os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
