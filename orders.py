import os
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from mailer import send_new_order_email
from security import csrf_ok, rate_limited

bp = Blueprint("orders", __name__)

BASE_DIR = Path(__file__).resolve().parent


def data_dir():
    """Folder for orders.db and uploads/ (DATA_DIR, default: the project
    folder). A relative DATA_DIR is relative to the project folder."""
    value = os.environ.get("DATA_DIR", "").strip()
    if not value:
        return BASE_DIR
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


DATA_DIR = data_dir()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "orders.db"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 200
MAX_NOTES_LENGTH = 1000

SIGNATURES = {
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".pdf": b"%PDF",
}

PHONE_RE = re.compile(r"^(?:\+?972|0)5\d{8}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ZIP_RE = re.compile(r"^\d{5}(\d{2})?$")

FIELDS = [
    "full_name",
    "phone",
    "email",
    "street",
    "house_number",
    "city",
    "zip",
    "embroidery_text",
    "notes",
    "embroidery",
    "accept_terms",
]

REQUIRED = [
    "full_name",
    "phone",
    "email",
    "street",
    "house_number",
    "city",
    "zip",
]

LABELS = {
    "full_name":
        "שם מלא",
    "phone":
        "טלפון נייד",
    "email":
        "דואר אלקטרוני",
    "street":
        "רחוב",
    "house_number":
        "מספר בית",
    "city":
        "עיר",
    "zip":
        "מיקוד",
}

MSG_MISSING = (
    "יש למלא את השדה: "
)
MSG_PHONE = (
    "מספר הטלפון אינו תקין. יש להזין מספר נייד ישראלי, למשל 0501234567."
)
MSG_EMAIL = (
    "כתובת הדואר האלקטרוני אינה תקינה."
)
MSG_ZIP = (
    "המיקוד צריך להכיל 5 או 7 ספרות."
)
MSG_EMB_TEXT = (
    "סימנת רקמה אישית, ולכן יש להזין את הטקסט לרקמה."
)
MSG_LONG = (
    "אחד השדות ארוך מדי."
)
MSG_FILE_REQUIRED = (
    "יש להעלות את הציור או התמונה."
)
MSG_FILE_TYPE = (
    "סוג הקובץ אינו נתמך. הקבצים המותרים מופיעים מתחת לשדה ההעלאה."
)
MSG_FILE_SIZE = (
    "הקובץ גדול מדי. הגודל המרבי הוא 10 מגה-בייט."
)
MSG_CSRF = (
    "פג תוקף הטופס. נא לבחור שוב את הקובץ ולשלוח."
)
MSG_TERMS = (
    "יש לאשר את התקנון ואת מדיניות הפרטיות."
)
MSG_RATE = (
    "נשלחו יותר מדי בקשות. נא לנסות שוב בעוד שעה."
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                street TEXT NOT NULL,
                house_number TEXT NOT NULL,
                city TEXT NOT NULL,
                zip TEXT NOT NULL,
                size TEXT NOT NULL,
                embroidery INTEGER NOT NULL,
                embroidery_text TEXT,
                notes TEXT,
                drawing_file TEXT NOT NULL,
                drawing_original_name TEXT,
                total_price INTEGER,
                terms_accepted_at TEXT
            )
            """
        )
        columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(orders)")
        ]
        if "terms_accepted_at" not in columns:
            conn.execute(
                "ALTER TABLE orders ADD COLUMN terms_accepted_at TEXT"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                ip_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS submissions_ip_hash
            ON submissions (ip_hash)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_failures (
                ip_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS login_failures_ip_hash
            ON login_failures (ip_hash)
            """
        )
    conn.close()


def empty_form():
    return dict.fromkeys(FIELDS, "")


def render_order(form, errors, status=200):
    page = render_template(
        "order.html",
        price=current_app.config["PRICE"],
        embroidery_price=current_app.config["EMBROIDERY_PRICE"],
        form=form,
        errors=errors,
    )
    return page, status


def calc_total(embroidery):
    total = current_app.config["PRICE"]
    if embroidery:
        total += current_app.config["EMBROIDERY_PRICE"]
    return total


@bp.route("/order", methods=["GET", "POST"])
def order():
    # Pre-launch: no form, and a POST is rejected before the upload,
    # CSRF or rate limit are touched, so nothing is read or stored.
    if not current_app.config["ORDERS_OPEN"]:
        status = 200 if request.method == "GET" else 403
        return render_template("orders_closed.html"), status

    if request.method == "GET":
        return render_order(empty_form(), [])

    form = {key: request.form.get(key, "").strip() for key in FIELDS}
    embroidery = form["embroidery"] == "yes"
    if not embroidery:
        form["embroidery_text"] = ""

    conn = get_db()
    limited = rate_limited(conn)
    conn.close()
    if limited:
        return render_order(form, [MSG_RATE], 429)

    if not csrf_ok():
        return render_order(form, [MSG_CSRF], 400)

    if request.form.get("website", "").strip():
        return redirect(url_for("index"))

    errors = []

    for key in REQUIRED:
        if not form[key]:
            errors.append(MSG_MISSING + LABELS[key])

    phone = re.sub(r"[\s-]", "", form["phone"])
    if form["phone"] and not PHONE_RE.match(phone):
        errors.append(MSG_PHONE)
    if form["email"] and not EMAIL_RE.match(form["email"]):
        errors.append(MSG_EMAIL)
    if form["zip"] and not ZIP_RE.match(form["zip"]):
        errors.append(MSG_ZIP)
    if embroidery and not form["embroidery_text"]:
        errors.append(MSG_EMB_TEXT)
    if form["accept_terms"] != "yes":
        errors.append(MSG_TERMS)

    too_long = len(form["notes"]) > MAX_NOTES_LENGTH
    for key in FIELDS:
        if key != "notes" and len(form[key]) > MAX_TEXT_LENGTH:
            too_long = True
    if too_long:
        errors.append(MSG_LONG)

    upload = request.files.get("drawing")
    data = b""
    ext = ""
    original_name = ""
    if upload is None or not upload.filename:
        errors.append(MSG_FILE_REQUIRED)
    else:
        original_name = upload.filename
        ext = Path(original_name).suffix.lower()
        data = upload.read()
        if ext not in SIGNATURES:
            errors.append(MSG_FILE_TYPE)
        elif len(data) > MAX_FILE_BYTES:
            errors.append(MSG_FILE_SIZE)
        elif not data.startswith(SIGNATURES[ext]):
            errors.append(MSG_FILE_TYPE)

    if errors:
        return render_order(form, errors, 400)

    now = datetime.now().isoformat(timespec="seconds")
    preview = current_app.config["ORDERS_MODE"] == "preview"
    stored_name = uuid.uuid4().hex + ext
    (UPLOAD_DIR / stored_name).write_bytes(data)

    conn = get_db()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO orders (
                created_at, status, full_name, phone, email,
                street, house_number, city, zip, size,
                embroidery, embroidery_text, notes,
                drawing_file, drawing_original_name, total_price,
                terms_accepted_at
            ) VALUES (
                :created_at, :status, :full_name, :phone, :email,
                :street, :house_number, :city, :zip, :size,
                :embroidery, :embroidery_text, :notes,
                :drawing_file, :drawing_original_name, :total_price,
                :terms_accepted_at
            )
            """,
            {
                "created_at": now,
                "status": "preview" if preview else "pending_payment",
                "full_name": form["full_name"],
                "phone": phone,
                "email": form["email"],
                "street": form["street"],
                "house_number": form["house_number"],
                "city": form["city"],
                "zip": form["zip"],
                "size": "standard",
                "embroidery": 1 if embroidery else 0,
                "embroidery_text": form["embroidery_text"],
                "notes": form["notes"],
                "drawing_file": stored_name,
                "drawing_original_name": original_name,
                "total_price": calc_total(embroidery),
                "terms_accepted_at": now,
            },
        )
    order_id = cur.lastrowid
    conn.close()

    send_new_order_email(
        {
            "id": order_id,
            "full_name": form["full_name"],
            "phone": phone,
            "email": form["email"],
            "street": form["street"],
            "house_number": form["house_number"],
            "city": form["city"],
            "zip": form["zip"],
            "size": "standard",
            "embroidery": embroidery,
            "embroidery_text": form["embroidery_text"],
            "notes": form["notes"],
            "total_price": calc_total(embroidery),
            "preview": preview,
        }
    )

    return redirect(url_for("orders.thanks", order_id=order_id))


@bp.route("/thanks/<int:order_id>")
def thanks(order_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    if row is None:
        abort(404)
    return render_template("thanks.html", order_id=order_id)


init_db()
