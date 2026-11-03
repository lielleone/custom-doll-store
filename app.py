import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, abort, render_template, url_for
from markupsafe import escape
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv(Path(__file__).resolve().parent / ".env")


def production_problems():
    """Unsafe settings when APP_ENV=production (empty list if all good)."""
    env = os.environ
    problems = []
    if len(env.get("SECRET_KEY", "")) < 32:
        problems.append("SECRET_KEY is missing or shorter than 32 characters.")
    if not env.get("ADMIN_PASSWORD_HASH", "").strip():
        problems.append("ADMIN_PASSWORD_HASH is missing.")
    if env.get("SESSION_COOKIE_SECURE") != "1":
        problems.append("SESSION_COOKIE_SECURE must be 1 (HTTPS-only session cookie).")
    if not env.get("SITE_URL", "").strip().startswith("https://"):
        problems.append("SITE_URL is missing or does not start with https://.")
    if env.get("FLASK_DEBUG") == "1":
        problems.append("FLASK_DEBUG must not be 1 in production.")
    if env.get("ORDERS_OPEN") == "1":
        # Safety lock: no orders while the legal pages are unfinished.
        from legal import legal_problems
        problems.extend(legal_problems())
    return problems


if os.environ.get("APP_ENV", "").strip().lower() == "production":
    _problems = production_problems()
    if _problems:
        raise RuntimeError(
            "Refusing to start: APP_ENV is production but these settings are unsafe:\n"
            + "\n".join("  - " + p for p in _problems)
        )

from admin import bp as admin_bp
from legal import LEGAL_DRAFT, LEGAL_PAGES
from orders import bp as orders_bp

app = Flask(__name__)

PRICE = 380
EMBROIDERY_PRICE = 30

SITE = {
    "phone": "050-1234567",
    "whatsapp": "972501234567",
    "email": "hello@example.com",
}


@app.route("/")
def index():
    return render_template(
        "index.html",
        price=PRICE,
        embroidery_price=EMBROIDERY_PRICE,
    )


@app.route("/contact")
def contact():
    return render_template("contact.html", site=SITE)


SITEMAP_PATHS = ["/", "/order", "/contact"]


@app.route("/robots.txt")
def robots_txt():
    if not app.config["INDEXABLE"]:
        return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")
    lines = [
        "User-agent: *",
        "Disallow: /admin",
        "Disallow: /thanks",
    ]
    site_url = app.config["SITE_URL"]
    if site_url:
        lines.append("Sitemap: " + site_url + "/sitemap.xml")
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    site_url = app.config["SITE_URL"]
    if not site_url or not app.config["INDEXABLE"]:
        abort(404)
    urls = "".join(
        "  <url><loc>" + str(escape(site_url + path)) + "</loc></url>\n"
        for path in SITEMAP_PATHS
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + urls
        + "</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")


@app.route("/<any(terms, cancellation, privacy, accessibility):slug>")
def legal(slug):
    return render_template(
        "legal.html", page=LEGAL_PAGES[slug], legal_draft=LEGAL_DRAFT
    )


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(error):
    return render_template("413.html"), 413


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


@app.context_processor
def inject_site_url():
    return {
        "site_url": app.config["SITE_URL"],
        "orders_open": app.config["ORDERS_OPEN"],
        "indexable": app.config["INDEXABLE"],
    }


def static_url(filename):
    """Static file URL with ?v=<modification time>, so browsers fetch
    the new file after it changes."""
    try:
        version = int((Path(app.static_folder) / filename).stat().st_mtime)
    except OSError:
        version = 0
    return url_for("static", filename=filename, v=version)


@app.context_processor
def inject_static_url():
    return {"static_url": static_url}


@app.after_request
def add_security_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if not app.config["INDEXABLE"]:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


app.config["PRICE"] = PRICE
app.config["EMBROIDERY_PRICE"] = EMBROIDERY_PRICE
app.config["MAX_CONTENT_LENGTH"] = 11 * 1024 * 1024
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SITE_URL"] = os.environ.get("SITE_URL", "").strip().rstrip("/")
# Pre-launch switch (ORDERS_OPEN): exactly "1" is open, exactly "preview"
# shows the form to people with the link but stays hidden from search
# engines and saves orders with status "preview", anything else is closed.
_orders_value = os.environ.get("ORDERS_OPEN")
if _orders_value == "1":
    ORDERS_MODE = "open"
elif _orders_value == "preview":
    ORDERS_MODE = "preview"
else:
    ORDERS_MODE = "closed"
app.config["ORDERS_MODE"] = ORDERS_MODE
# The order form works (open or preview).
app.config["ORDERS_OPEN"] = ORDERS_MODE != "closed"
# Search engines may index the site (open only).
app.config["INDEXABLE"] = ORDERS_MODE == "open"
print("Orders: " + ORDERS_MODE.upper(), flush=True)
app.register_blueprint(orders_bp)
app.register_blueprint(admin_bp)


def trusted_proxies():
    """Number of reverse proxies in front of the app (TRUST_PROXY).
    0 or unset: forwarded headers are ignored."""
    value = os.environ.get("TRUST_PROXY", "").strip() or "0"
    try:
        count = int(value)
    except ValueError:
        raise RuntimeError("TRUST_PROXY must be a whole number, got: " + value)
    return max(count, 0)


TRUST_PROXY = trusted_proxies()
if TRUST_PROXY:
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=TRUST_PROXY,
        x_proto=TRUST_PROXY,
        x_host=TRUST_PROXY,
        x_prefix=TRUST_PROXY,
    )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug, port=5001)
