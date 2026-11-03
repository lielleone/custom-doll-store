import os
import time
from functools import wraps
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from orders import UPLOAD_DIR, get_db
from security import (
    check_csrf,
    clear_login_failures,
    csrf_token,
    login_blocked,
    record_login_failure,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = {
    "pending_payment":
        "ממתינה לתשלום",
    "paid":
        "שולמה",
    "in_production":
        "בייצור",
    "shipped":
        "נשלחה",
    "cancelled":
        "בוטלה",
    # Test orders made while ORDERS_OPEN=preview.
    "preview":
        "הזמנת בדיקה",
}

# "giant" is no longer offered; kept only to display old orders.
SIZES = {
    "standard":
        "רגיל",
    "giant":
        "ענק",
}

MSG_LOGIN = (
    "הסיסמה שגויה."
)
MSG_LOGIN_LIMIT = (
    "יותר מדי ניסיונות כניסה שגויים. נא לנסות שוב בעוד 15 דקות."
)


@bp.app_context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login"))
        lifetime = current_app.permanent_session_lifetime.total_seconds()
        if time.time() - session.get("admin_since", 0) > lifetime:
            session.clear()
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


def fetch_order(order_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    if row is None:
        abort(404)
    return row


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        check_csrf()
        conn = get_db()
        try:
            if login_blocked(conn):
                page = render_template(
                    "admin_login.html", error=MSG_LOGIN_LIMIT
                )
                return page, 429
            stored = os.environ.get("ADMIN_PASSWORD_HASH", "")
            password = request.form.get("password", "")
            if stored and check_password_hash(stored, password):
                clear_login_failures(conn)
                session.clear()
                session.permanent = True
                session["admin"] = True
                session["admin_since"] = time.time()
                return redirect(url_for("admin.index"))
            record_login_failure(conn)
        finally:
            conn.close()
        time.sleep(1)
        error = MSG_LOGIN
    return render_template("admin_login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    check_csrf()
    session.clear()
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def index():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, created_at, status, full_name, phone, city,
               size, embroidery, total_price
        FROM orders ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    preview_count = sum(1 for r in rows if r["status"] == "preview")
    return render_template(
        "admin_orders.html",
        rows=rows,
        statuses=STATUSES,
        sizes=SIZES,
        preview_count=preview_count,
    )


def upload_path(name):
    """Path of an uploaded file, or None if it is not directly inside
    the uploads folder (for example a name with .. or a slash)."""
    upload_dir = UPLOAD_DIR.resolve()
    path = (upload_dir / name).resolve()
    if not name or path.parent != upload_dir:
        return None
    return path


@bp.route("/preview/delete", methods=["POST"])
@login_required
def delete_previews():
    """Delete all test orders (status "preview") and their drawings.
    Rows with any other status and their files are never touched."""
    check_csrf()
    conn = get_db()
    with conn:
        rows = conn.execute(
            "SELECT id, drawing_file FROM orders WHERE status = 'preview'"
        ).fetchall()
        conn.execute("DELETE FROM orders WHERE status = 'preview'")
        # Files still used by a remaining order are kept.
        kept = {
            r["drawing_file"]
            for r in conn.execute("SELECT drawing_file FROM orders")
        }
    conn.close()
    for r in rows:
        name = r["drawing_file"]
        path = upload_path(name)
        if path is None or name in kept:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            print("Could not delete test drawing:", repr(exc), flush=True)
    return redirect(url_for("admin.index"))


@bp.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    row = fetch_order(order_id)
    is_pdf = Path(row["drawing_file"]).suffix.lower() == ".pdf"
    return render_template(
        "admin_order.html",
        o=row,
        is_pdf=is_pdf,
        statuses=STATUSES,
        sizes=SIZES,
    )


@bp.route("/order/<int:order_id>/status", methods=["POST"])
@login_required
def set_status(order_id):
    check_csrf()
    row = fetch_order(order_id)
    new_status = request.form.get("status", "")
    if new_status not in STATUSES:
        abort(400)
    # A real order must never become a test order, because the clean-up
    # button deletes every "preview" row.
    if new_status == "preview" and row["status"] != "preview":
        abort(400)
    conn = get_db()
    with conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (new_status, order_id),
        )
    conn.close()
    return redirect(url_for("admin.order_detail", order_id=order_id))


@bp.route("/drawing/<int:order_id>")
@login_required
def drawing(order_id):
    row = fetch_order(order_id)
    is_pdf = Path(row["drawing_file"]).suffix.lower() == ".pdf"
    return send_from_directory(
        UPLOAD_DIR, row["drawing_file"], as_attachment=is_pdf
    )
