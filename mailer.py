import os
import smtplib
import threading
from email.message import EmailMessage

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

SUBJECT = (
    "הזמנה חדשה מספר {order_id}"
)
PREVIEW_PREFIX = (
    "[בדיקה] "
)
TITLE = (
    "התקבלה הזמנה חדשה באתר."
)
UNPAID = (
    "שים לב: ההזמנה עדיין לא שולמה."
)
PRICE_UNKNOWN = (
    "טרם נקבע"
)
YES = (
    "כן"
)
NO = (
    "לא"
)

# "giant" is no longer offered; kept only for old orders.
SIZE_NAMES = {
    "standard":
        "רגיל",
    "giant":
        "ענק",
}

LABEL_NAME = (
    "שם"
)
LABEL_PHONE = (
    "טלפון"
)
LABEL_EMAIL = (
    "דואר אלקטרוני"
)
LABEL_ADDRESS = (
    "כתובת"
)
LABEL_SIZE = (
    "גודל"
)
LABEL_EMBROIDERY = (
    "רקמה"
)
LABEL_TOTAL = (
    "סכום"
)
LABEL_NOTES = (
    "הערות"
)


def build_message(order):
    sender = os.environ["SMTP_USER"]
    recipient = os.environ.get("ORDER_EMAIL", sender)

    address = "{street} {house_number}, {city}, {zip}".format(**order)
    if order["embroidery"]:
        embroidery = YES + " (" + order["embroidery_text"] + ")"
    else:
        embroidery = NO
    if order["total_price"] is None:
        total = PRICE_UNKNOWN
    else:
        total = "₪" + str(order["total_price"])

    lines = [
        TITLE,
        UNPAID,
        "",
        LABEL_NAME + ": " + order["full_name"],
        LABEL_PHONE + ": " + order["phone"],
        LABEL_EMAIL + ": " + order["email"],
        LABEL_ADDRESS + ": " + address,
        LABEL_SIZE + ": " + SIZE_NAMES[order["size"]],
        LABEL_EMBROIDERY + ": " + embroidery,
        LABEL_TOTAL + ": " + total,
        LABEL_NOTES + ": " + order["notes"],
    ]

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    subject = SUBJECT.format(order_id=order["id"])
    if order.get("preview"):
        subject = PREVIEW_PREFIX + subject
    msg["Subject"] = subject
    msg.set_content("\n".join(lines))
    return msg


def _send(msg):
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_APP_PASSWORD")
    if not user or not password:
        print("Email is not configured, skipping.", flush=True)
        return
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.login(user, password)
            server.send_message(msg)
        print("Order email sent.", flush=True)
    except Exception as exc:
        print("Email failed:", repr(exc), flush=True)


def send_new_order_email(order):
    try:
        msg = build_message(order)
    except Exception as exc:
        print("Email build failed:", repr(exc), flush=True)
        return
    threading.Thread(target=_send, args=(msg,), daemon=True).start()
