import hashlib
import hmac
import secrets
import time

from flask import abort, current_app, request, session

RATE_WINDOW_SECONDS = 60 * 60
RATE_MAX_REQUESTS = 10

LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def csrf_ok():
    sent = request.form.get("csrf", "")
    expected = session.get("csrf", "")
    if not expected:
        return False
    return hmac.compare_digest(sent.encode(), expected.encode())


def check_csrf():
    if not csrf_ok():
        abort(400)


def client_hash():
    ip = request.remote_addr or ""
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()


def rate_limited(conn):
    now = time.time()
    ip_hash = client_hash()
    with conn:
        conn.execute(
            "DELETE FROM submissions WHERE created_at < ?",
            (now - RATE_WINDOW_SECONDS,),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE ip_hash = ?",
            (ip_hash,),
        ).fetchone()[0]
        if count >= RATE_MAX_REQUESTS:
            return True
        conn.execute(
            "INSERT INTO submissions (ip_hash, created_at) VALUES (?, ?)",
            (ip_hash, now),
        )
    return False


def login_blocked(conn):
    with conn:
        conn.execute(
            "DELETE FROM login_failures WHERE created_at < ?",
            (time.time() - LOGIN_WINDOW_SECONDS,),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM login_failures WHERE ip_hash = ?",
            (client_hash(),),
        ).fetchone()[0]
    return count >= LOGIN_MAX_FAILURES


def record_login_failure(conn):
    with conn:
        conn.execute(
            "INSERT INTO login_failures (ip_hash, created_at) VALUES (?, ?)",
            (client_hash(), time.time()),
        )


def clear_login_failures(conn):
    with conn:
        conn.execute(
            "DELETE FROM login_failures WHERE ip_hash = ?",
            (client_hash(),),
        )
