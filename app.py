"""
app.py
-------
ULTRA ERP web application.

Two logins share one /login page:
  - super_admin -> platform admin panel (/admin/...): create companies,
    manage subscriptions, create users.
  - company users (admin/staff) -> the actual ERP app (/...): Parties,
    Quality, Sale & Purchase, Receipt & Payment, Reports.

Run with:  python3 app.py
Then open  http://localhost:5000  (or http://<this-pc's-LAN-IP>:5000
from another device on the same network).
"""

import os
import re
import shutil
import zipfile
import subprocess
import json
import tempfile
import csv
import io
from datetime import date, datetime
from functools import wraps
from itertools import zip_longest

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    send_file, jsonify, g, abort
)
from werkzeug.utils import secure_filename

import master
import db
import settings
import ui_theme
import email_utils

try:
    import pdf_export
except ImportError:
    pdf_export = None
try:
    import voucher_print
except ImportError:
    voucher_print = None
try:
    import retail_pdf
except ImportError:
    retail_pdf = None
try:
    import excel_export
except ImportError:
    excel_export = None
try:
    import data_import
except ImportError:
    data_import = None
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    Limiter = None
try:
    from flask_wtf import CSRFProtect
    from flask_wtf.csrf import CSRFError
except ImportError:
    CSRFProtect = None

app = Flask(__name__)
app.secret_key = os.environ.get("ULTRAERP_SECRET_KEY", "dev-secret-change-me-in-production")
if app.secret_key == "dev-secret-change-me-in-production":
    print("WARNING: ULTRAERP_SECRET_KEY is not set - using the insecure built-in default. "
          "Sessions can be forged by anyone who knows this default. Set ULTRAERP_SECRET_KEY "
          "in your environment (deploy/setup.sh does this automatically for a standard deploy).")

# SameSite=Lax and HttpOnly cost nothing even for plain-http local dev, so
# they're always on. Secure (only send the cookie over HTTPS) is opt-in via
# env var instead of always-on, because forcing it would silently break
# cookies for anyone running `python app.py` locally over plain http - a
# documented, supported way to run this app (see the module docstring).
# deploy/setup.sh sets this for you on a real server, where Caddy always
# terminates HTTPS in front of the app.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("ULTRAERP_FORCE_SECURE_COOKIES") == "1"

# CSRF protection on every POST/PUT/PATCH/DELETE. The token itself is
# handed to every page via the <meta name="csrf-token"> tag in base.html
# and auto-injected into every <form> by the inline script right after
# it - so no individual template had to be touched. The 4 places that
# submit via fetch() instead of a real <form> (barcode-scan quick-add,
# see searchable-select.js and the inline scripts on the Sale/Purchase
# pages) send it as an X-CSRFToken header instead, which Flask-WTF
# accepts equally. No time limit: this app doesn't set its own session
# expiry, so tying the token to one instead would just produce a
# confusing "session expired" error on a Sale form someone left open
# for a while between customers, for no real security benefit - the
# session cookie itself is already the thing that has to stay valid.
csrf = None
if CSRFProtect is not None:
    app.config["WTF_CSRF_TIME_LIMIT"] = None
    csrf = CSRFProtect(app)

    @app.errorhandler(CSRFError)
    def _handle_csrf_error(e):
        """Without this, a rejected token shows Flask-WTF's bare default
        400 page ("The CSRF token is missing.") instead of fitting in
        with how every other validation failure in this app behaves. In
        practice a real user only ever hits this from a page left open
        since before the server last restarted (the token is tied to
        the running app's secret key) - reloading and resubmitting
        always works, hence pointing them back rather than to /login."""
        flash("Your session needs a refresh before that will go through - please try again.", "error")
        return redirect(request.referrer or url_for("login"))
else:
    print("WARNING: flask-wtf is not installed - CSRF protection is disabled. "
          "Run pip install -r requirements.txt.")
    # base.html calls csrf_token() unconditionally (normally registered
    # by CSRFProtect itself) - keep that from breaking every page if the
    # package genuinely isn't installed.
    app.jinja_env.globals["csrf_token"] = lambda: ""

# Brute-force protection on login attempts only (not page views, not the
# rest of the app) - in-memory storage is fine here since this runs as a
# single waitress process per deploy/ultraerp.service, not multiple
# workers that would need a shared backend like Redis.
MIN_PASSWORD_LENGTH = 6

limiter = None
if Limiter is not None:
    limiter = Limiter(key_func=get_remote_address, app=app, default_limits=[])

    @app.errorhandler(429)
    def _too_many_login_attempts(e):
        flash("Too many login attempts. Please wait a minute and try again.", "error")
        return render_template("login.html", hide_shell=True), 429


@app.errorhandler(ValueError)
def _handle_bad_numeric_input(e):
    """Safety net for malformed numeric input - dozens of routes parse a
    quantity/rate/amount field with float(request.form.get(...)) and no
    per-call try/except, relying on the browser's <input type="number">
    to keep the value parseable. That holds for normal use, but a
    tampered or hand-crafted request (not a real user mistake - those
    are already caught by each form's own "every line needs a valid
    quantity" checks before this could ever trigger) could still send
    something like "abc" and hit an uncaught ValueError, which without
    this would surface as a raw, unbranded "Internal Server Error" page
    instead of the flash-and-redirect experience every other validation
    failure in this app gives. One handler here is deliberately simpler
    and more maintainable than wrapping every individual call site."""
    print(f"WARNING: unhandled ValueError on {request.path}: {e}")
    flash("Something in that submission wasn't valid - please check the values and try again.", "error")
    return redirect(request.referrer or url_for("login"))


# ---------------------------------------------------------------------
# auth helpers
# ---------------------------------------------------------------------
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return master.get_user(uid)


@app.before_request
def load_tenant_context():
    g.user = current_user()
    if g.user:
        # admins always have edit rights, regardless of the per-staff
        # can_edit flag (that flag only exists to grant it to specific
        # staff members) - fix this once here so every template that
        # checks current_user.can_edit gets the right answer, rather
        # than re-deriving "admin OR granted" in each template
        g.user["can_edit"] = g.user["role"] == "admin" or g.user.get("can_edit", False)
    g.company = None
    if g.user and g.user["company_id"]:
        g.company = master.get_company(g.user["company_id"])
    # Always explicitly set (or reset) the active database for this
    # request - never leave a previous request's tenant DB "stuck" in
    # the thread-local, which would otherwise leak one company's data
    # into another request handled by the same worker thread (e.g. the
    # super-admin viewing a company right after a tenant request).
    if g.company:
        db.set_active_db_path(master.tenant_db_path(g.company["slug"]))
    else:
        db.set_active_db_path(None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def company_required(view):
    """For tenant-app routes: must be logged in as a company user, and
    that company's subscription must currently be usable."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] == "super_admin":
            return redirect(url_for("admin_dashboard"))
        if not g.company:
            flash("Your account isn't linked to a company. Contact your administrator.", "error")
            return redirect(url_for("login"))
        if not master.is_subscription_active(g.company):
            return render_template("app/subscription_expired.html", company=g.company, hide_shell=True)
        return view(*args, **kwargs)
    return wrapped


def company_admin_required(view):
    """Same as company_required, but only for tenant users with the
    'admin' role - used for pages that manage other users within the
    company, which regular staff shouldn't be able to touch."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] == "super_admin":
            return redirect(url_for("admin_dashboard"))
        if not g.company:
            flash("Your account isn't linked to a company. Contact your administrator.", "error")
            return redirect(url_for("login"))
        if not master.is_subscription_active(g.company):
            return render_template("app/subscription_expired.html", company=g.company, hide_shell=True)
        if g.user["role"] != "admin":
            flash("Only a company admin can manage users.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def delete_permission_required(view):
    """Deleting entries is admin-only, always - there is no per-staff
    override for this one, unlike editing."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] == "super_admin":
            return redirect(url_for("admin_dashboard"))
        if not g.company:
            flash("Your account isn't linked to a company. Contact your administrator.", "error")
            return redirect(url_for("login"))
        if not master.is_subscription_active(g.company):
            return render_template("app/subscription_expired.html", company=g.company, hide_shell=True)
        if g.user["role"] != "admin":
            flash("Only an admin can delete entries. Ask your company admin if you need this removed.", "error")
            return redirect(request.referrer or url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def edit_permission_required(view):
    """Editing entries is admin-only by default, but an admin can grant
    a specific staff member edit rights (see Team page / can_edit)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] == "super_admin":
            return redirect(url_for("admin_dashboard"))
        if not g.company:
            flash("Your account isn't linked to a company. Contact your administrator.", "error")
            return redirect(url_for("login"))
        if not master.is_subscription_active(g.company):
            return render_template("app/subscription_expired.html", company=g.company, hide_shell=True)
        if not master.user_can_edit(g.user):
            flash("You don't have permission to edit entries. Ask your company admin to grant it.", "error")
            return redirect(request.referrer or url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] != "super_admin":
            flash(f"You're currently signed in as {g.user['username']} (not the platform admin), "
                  f"so you were sent to your own dashboard instead. Sign out and sign back in as "
                  f"the platform admin to manage companies.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    theme_colors = ui_theme.get_colors(settings.get_theme() if g.company else None) if g.company else ui_theme.get_colors("Purple")
    return {
        "current_user": g.user,
        "current_company": g.company,
        "theme_colors": theme_colors,
        "company_name": settings.get_company_name() if g.company else "Khatay",
    }


# ---------------------------------------------------------------------
# login / logout
# ---------------------------------------------------------------------
def _login_rate_limit(view):
    """No-op if flask-limiter isn't installed, so the app still runs
    without it - see the optional import above."""
    if limiter is None:
        return view
    return limiter.limit("8 per minute", methods=["POST"])(view)


@app.route("/login", methods=["GET", "POST"])
@_login_rate_limit
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = master.verify_login(username, password)
        if not user:
            flash("Incorrect username or password.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        session.permanent = True
        if user["role"] == "super_admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(request.args.get("next") or url_for("business_select"))

    # If already signed in, don't silently bounce away - show who's
    # signed in and let them continue or switch accounts. (Previously
    # this auto-redirected, which meant there was no way to get back
    # to the login form to sign in as someone else without an explicit
    # /logout first - confusing when testing multiple accounts.)
    already_signed_in = None
    if g.user:
        already_signed_in = g.user
    return render_template("login.html", already_signed_in=already_signed_in, hide_shell=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _forgot_password_rate_limit(view):
    if limiter is None:
        return view
    return limiter.limit("5 per hour", methods=["POST"])(view)


@app.route("/forgot-password", methods=["GET", "POST"])
@_forgot_password_rate_limit
def forgot_password():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        # Always show the same message regardless of whether the account
        # (or an email on file for it) actually exists - telling an
        # attacker "no such account" would let them enumerate usernames.
        generic_message = ("If an account with an email on file matches what you entered, "
                            "a reset link has been sent to it.")
        user = master.get_user_by_login_identifier(identifier) if identifier else None
        if user and user.get("email") and email_utils.smtp_configured():
            token, valid_minutes = master.create_password_reset(user["id"])
            reset_url = url_for("reset_password", token=token, _external=True)
            email_utils.send_email(
                user["email"], "Reset your ULTRA ERP password",
                f"Hi {user['full_name'] or user['username']},\n\n"
                f"Someone (hopefully you) requested a password reset for your ULTRA ERP account.\n\n"
                f"Reset your password here (valid for {valid_minutes} minutes):\n{reset_url}\n\n"
                f"If you didn't request this, you can safely ignore this email.",
            )
        flash(generic_message, "success")
        return redirect(url_for("login"))
    return render_template("forgot_password.html", hide_shell=True)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = master.get_valid_password_reset(token)
    if not user:
        flash("That reset link is invalid or has expired. Request a new one below.", "error")
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
            return render_template("reset_password.html", hide_shell=True, token=token)
        if new_password != confirm:
            flash("Passwords don't match.", "error")
            return render_template("reset_password.html", hide_shell=True, token=token)
        master.change_password(user["id"], new_password)
        master.consume_password_reset(token)
        flash("Password updated - sign in with your new password.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", hide_shell=True, token=token, username=user["username"])


@app.route("/manifest.json")
def pwa_manifest():
    resp = send_file(os.path.join(app.static_folder, "manifest.json"), mimetype="application/manifest+json")
    return resp


@app.route("/service-worker.js")
def pwa_service_worker():
    """Served at the root path (not /static/service-worker.js) so its
    default scope covers the whole app, not just /static/."""
    resp = send_file(os.path.join(app.static_folder, "service-worker.js"), mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/theme.css")
def theme_css():
    theme_name = settings.get_theme() if g.company else "Purple"
    colors = ui_theme.get_colors(theme_name)
    css = render_template("theme.css.j2", theme_colors=colors)
    return app.response_class(css, mimetype="text/css")


# =======================================================================
# SUPER-ADMIN PANEL — create companies, manage subscriptions & users
# =======================================================================
@app.route("/admin")
@super_admin_required
def admin_dashboard():
    companies = master.list_companies()
    return render_template("admin/dashboard.html", companies=companies)


@app.route("/admin/subscriptions")
@super_admin_required
def admin_subscriptions():
    companies = master.list_companies()
    today_iso = date.today().isoformat()

    def sort_key(c):
        # companies with no expiry (permanently active) sort last;
        # everything else sorts by how soon it's due, overdue first
        if not c["subscription_expiry"]:
            return (2, "")
        return (0 if c["is_expired"] else 1, c["subscription_expiry"])

    for c in companies:
        if c["subscription_expiry"]:
            try:
                days = (date.fromisoformat(c["subscription_expiry"]) - date.fromisoformat(today_iso)).days
                c["days_until_due"] = days
            except ValueError:
                c["days_until_due"] = None
        else:
            c["days_until_due"] = None

    companies.sort(key=sort_key)
    overdue_count = sum(1 for c in companies if c["is_expired"])
    due_soon_count = sum(1 for c in companies if not c["is_expired"] and c["days_until_due"] is not None and c["days_until_due"] <= 7)
    return render_template("admin/subscriptions.html", companies=companies,
                            overdue_count=overdue_count, due_soon_count=due_soon_count, today=today_iso)


@app.route("/admin/companies", methods=["POST"])
@super_admin_required
def admin_create_company():
    name = request.form.get("company_name", "").strip()
    admin_username = request.form.get("admin_username", "").strip()
    admin_password = request.form.get("admin_password", "")
    admin_full_name = request.form.get("admin_full_name", "").strip()
    admin_email = request.form.get("admin_email", "").strip()
    trial_days = int(request.form.get("trial_days") or 14)

    if not name or not admin_username or not admin_password:
        flash("Company name, admin username, and admin password are all required.", "error")
        return redirect(url_for("admin_dashboard"))
    if len(admin_password) < MIN_PASSWORD_LENGTH:
        flash(f"Admin password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        return redirect(url_for("admin_dashboard"))

    company_id, slug = master.create_company(
        name, admin_username, admin_password, admin_full_name,
        subscription_status="trial", trial_days=trial_days, admin_email=admin_email,
    )
    flash(f"Company '{name}' created ({trial_days}-day trial). Admin login: {admin_username}", "success")
    return redirect(url_for("admin_company_detail", company_id=company_id))


@app.route("/admin/companies/<int:company_id>")
@super_admin_required
def admin_company_detail(company_id):
    company = master.get_company(company_id)
    if not company:
        flash("Company not found.", "error")
        return redirect(url_for("admin_dashboard"))
    users = master.list_users_for_company(company_id)
    return render_template("admin/company_detail.html", company=company, users=users, today=date.today().isoformat())


@app.route("/admin/companies/<int:company_id>/subscription", methods=["POST"])
@super_admin_required
def admin_update_subscription(company_id):
    status = request.form.get("status")
    expiry = request.form.get("expiry") or None
    notes = request.form.get("notes", "")
    master.set_subscription(company_id, status, expiry, notes)
    flash("Subscription updated.", "success")
    return redirect(url_for("admin_company_detail", company_id=company_id))


@app.route("/admin/companies/<int:company_id>/users", methods=["POST"])
@super_admin_required
def admin_create_user(company_id):
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "staff")
    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("admin_company_detail", company_id=company_id))
    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        return redirect(url_for("admin_company_detail", company_id=company_id))
    user_id = master.create_user(company_id, username, password, full_name, role, email)
    if user_id is None:
        flash(f"Username '{username}' is already taken.", "error")
    else:
        flash(f"User '{username}' created.", "success")
    return redirect(url_for("admin_company_detail", company_id=company_id))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@super_admin_required
def admin_delete_user(user_id):
    user = master.get_user(user_id)
    if user and user["role"] != "super_admin":
        master.delete_user(user_id)
        flash("User removed.", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))


@app.route("/admin/change-password", methods=["GET", "POST"])
@super_admin_required
def admin_change_password():
    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        if len(new_password) < MIN_PASSWORD_LENGTH:
            flash(f"Password should be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        else:
            master.change_password(g.user["id"], new_password)
            flash("Password changed.", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/change_password.html")


# =======================================================================
# TENANT APP — the actual ERP, scoped to the logged-in company
# =======================================================================
@app.route("/business")
@company_required
def business_select():
    return render_template("app/business_select.html", hide_shell=True)


@app.route("/")
@company_required
def dashboard():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM parties WHERE is_gl = 0")
    party_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM quality")
    item_count = cur.fetchone()[0]
    conn.close()

    as_of = date.today().isoformat()
    receivable = db.get_receivable_aging(as_of)
    payable = db.get_payable_aging(as_of)
    total_receivable = sum(r["outstanding"] for r in receivable)
    total_payable = sum(r["outstanding"] for r in payable)
    overdue_receivable = sum(r["outstanding"] for r in receivable if r["is_overdue"])

    month_start = date.today().replace(day=1).isoformat()
    profit = db.get_profit_summary(month_start, as_of)

    return render_template(
        "app/dashboard.html", party_count=party_count, item_count=item_count,
        total_receivable=total_receivable, total_payable=total_payable,
        overdue_receivable=overdue_receivable, profit=profit,
    )


# =======================================================================
# KIRYANA MODULE — grocery-store business type: Inventory, Sale Book,
# Purchase List, Cash Book, Ledger, Expenses. Separate engine from the
# Yarn app above (see db.py's Kiryana section for why), reachable once
# a company picks "Kiryana" from the business-type picker (business_select).
# =======================================================================
KIRYANA_STANDARD_UNITS = ["kg", "g", "L", "ml", "pcs", "dozen", "packet", "box", "bag", "bundle"]


def _resolve_kiryana_unit(form):
    """The Unit field is a dropdown of common units plus an 'Other' option
    that reveals a free-text box (see inventory.html/item_edit.html) -
    this resolves whichever one the user actually meant."""
    unit = form.get("unit", "").strip()
    if unit == "__other__":
        unit = form.get("unit_other", "").strip()
    return unit


@app.route("/kiryana")
@company_required
def kiryana_dashboard():
    today = date.today().isoformat()
    stock = db.kiryana_stock_summary()
    receivable = db.kiryana_balance_summary("Customer")
    payable = db.kiryana_balance_summary("Supplier")
    sales_today_total = sum(t["amount"] for t in db.kiryana_list_transactions("SALE", limit=1000) if t["date"] == today)
    total_sales = db.kiryana_total_sales()
    total_expenses = db.kiryana_total_expenses()
    cash_events = db.kiryana_cash_book()
    cash_balance = cash_events[-1]["balance"] if cash_events else 0
    low_stock = db.kiryana_low_stock_summary()
    expiring = db.kiryana_expiring_batches()
    return render_template("app/kiryana/dashboard.html", stock=stock, receivable=receivable, payable=payable,
                            sales_today_total=sales_today_total, total_sales=total_sales,
                            net_profit=total_sales - total_expenses, cash_balance=cash_balance,
                            low_stock=low_stock, expiring=expiring)


@app.route("/kiryana/inventory", methods=["GET", "POST"])
@company_required
def kiryana_inventory():
    if request.method == "POST":
        names = request.form.getlist("name[]")
        units = request.form.getlist("unit[]")
        unit_others = request.form.getlist("unit_other[]")
        categories_in = request.form.getlist("category[]")
        barcodes_in = request.form.getlist("barcode[]")
        purchase_rates = request.form.getlist("purchase_rate[]")
        sale_rates = request.form.getlist("sale_rate[]")
        opening_qtys = request.form.getlist("opening_qty[]")
        reorder_levels = request.form.getlist("reorder_level[]")
        purchase_units = request.form.getlist("purchase_unit[]")
        conversion_factors = request.form.getlist("conversion_factor[]")

        existing_barcodes = {i["barcode"] for i in db.kiryana_list_items() if i["barcode"]}
        seen_barcodes = set()
        rows = []
        for name, unit, unit_other, category, barcode, p_rate, s_rate, opening_qty, reorder, p_unit, factor in zip_longest(
            names, units, unit_others, categories_in, barcodes_in, purchase_rates, sale_rates,
            opening_qtys, reorder_levels, purchase_units, conversion_factors, fillvalue="",
        ):
            name = (name or "").strip()
            if not name:
                continue
            barcode = (barcode or "").strip() or None
            if barcode and (barcode in existing_barcodes or barcode in seen_barcodes):
                flash(f"Barcode '{barcode}' is already used by another item.", "error")
                return redirect(url_for("kiryana_inventory"))
            if barcode:
                seen_barcodes.add(barcode)
            resolved_unit = unit_other.strip() if unit == "__other__" else unit.strip()
            rows.append((
                name, resolved_unit, float(p_rate or 0), float(s_rate or 0), float(opening_qty or 0),
                barcode, float(reorder or 0), category.strip() or None, p_unit.strip() or None,
                float(factor or 1),
            ))
        if not rows:
            flash("Add at least one item (a name is required).", "error")
            return redirect(url_for("kiryana_inventory"))

        for row in rows:
            db.kiryana_add_item(*row)
        if len(rows) == 1:
            flash(f"{rows[0][0]} added to inventory.", "success")
        else:
            flash(f"{len(rows)} items added to inventory.", "success")
        return redirect(url_for("kiryana_inventory"))
    return render_template("app/kiryana/inventory.html", items=db.kiryana_list_items(),
                            standard_units=KIRYANA_STANDARD_UNITS, categories=db.kiryana_list_categories())


@app.route("/kiryana/items/quick-add", methods=["POST"])
@company_required
def kiryana_item_quick_add():
    """Adds a new inventory item without leaving the Sale/Purchase form -
    called via JS (see static/js/searchable-select.js's quick-add
    support, and static/js/barcode-scanner.js for the barcode-not-found
    flow), returns JSON so the new item can be dropped straight into
    that page's Item dropdown, already selected, with everything else on
    the form left untouched. Rate/unit start at 0/blank - meant for
    fixing up on the Inventory page later, not filling in mid-entry."""
    name = request.form.get("name", "").strip()
    barcode = request.form.get("barcode", "").strip() or None
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    items = db.kiryana_list_items()
    if any(i["name"].lower() == name.lower() for i in items):
        return {"ok": False, "error": f"An item named '{name}' already exists."}, 400
    if barcode and any(i["barcode"] == barcode for i in items):
        return {"ok": False, "error": f"Barcode '{barcode}' is already used by another item."}, 400
    new_id = db.kiryana_add_item(name, request.form.get("unit", "").strip(), 0, 0, 0, barcode)
    return {"ok": True, "id": new_id, "name": name, "unit": "", "purchase_rate": 0, "sale_rate": 0, "barcode": barcode}


@app.route("/kiryana/items/by-barcode")
@company_required
def kiryana_item_by_barcode():
    """Looks up an item by scanned barcode (see static/js/barcode-scanner.js)
    - called from the Sale/Purchase forms' scan input, both the
    keyboard-wedge USB/Bluetooth scanner path and the camera-based one."""
    code = request.args.get("code", "").strip()
    if not code:
        return {"ok": False, "error": "No barcode given."}, 400
    item = db.kiryana_get_item_by_barcode(code)
    if not item:
        return {"ok": False, "error": f"No item found for barcode {code}."}, 404
    return {"ok": True, **item}


@app.route("/kiryana/inventory/<int:item_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def kiryana_edit_item(item_id):
    item = db.kiryana_get_item(item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("kiryana_inventory"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        barcode = request.form.get("barcode", "").strip() or None
        if not name:
            flash("Item name is required.", "error")
            return redirect(url_for("kiryana_edit_item", item_id=item_id))
        if barcode and any(i["barcode"] == barcode and i["id"] != item_id for i in db.kiryana_list_items()):
            flash(f"Barcode '{barcode}' is already used by another item.", "error")
            return redirect(url_for("kiryana_edit_item", item_id=item_id))
        db.kiryana_update_item(
            item_id, name, _resolve_kiryana_unit(request.form),
            float(request.form.get("purchase_rate") or 0), float(request.form.get("sale_rate") or 0),
            float(request.form.get("stock_qty") or 0), barcode,
            float(request.form.get("reorder_level") or 0),
            request.form.get("category", "").strip() or None,
            request.form.get("purchase_unit", "").strip() or None,
            float(request.form.get("conversion_factor") or 1),
        )
        flash("Item updated.", "success")
        return redirect(url_for("kiryana_inventory"))
    return render_template("app/kiryana/item_edit.html", item=item, standard_units=KIRYANA_STANDARD_UNITS,
                            categories=db.kiryana_list_categories())


@app.route("/kiryana/inventory/<int:item_id>/delete", methods=["POST"])
@company_required
def kiryana_delete_item(item_id):
    if db.kiryana_item_has_transactions(item_id):
        flash("Can't delete an item with sales or purchases recorded against it.", "error")
        return redirect(url_for("kiryana_inventory"))
    db.kiryana_delete_item(item_id)
    flash("Item removed.", "success")
    return redirect(url_for("kiryana_inventory"))


@app.route("/kiryana/sales", methods=["GET", "POST"])
@company_required
def kiryana_sales():
    if request.method == "POST":
        item_ids = request.form.getlist("item_id[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        if mode == "Credit" and not party_id:
            flash("Pick a customer for a credit sale.", "error")
            return redirect(url_for("kiryana_sales"))

        lines = []
        for item_id, qty, rate in zip_longest(item_ids, qtys, rates, fillvalue=""):
            if not item_id:
                continue
            qty = float(qty or 0)
            rate = float(rate or 0)
            if qty <= 0 or rate <= 0:
                flash("Every line needs an item, a valid quantity, and a valid rate.", "error")
                return redirect(url_for("kiryana_sales"))
            lines.append((int(item_id), qty, rate))
        if not lines:
            flash("Add at least one item line to the sale.", "error")
            return redirect(url_for("kiryana_sales"))

        invoice_no = db.kiryana_get_next_invoice_no("SALE")
        for item_id, qty, rate in lines:
            db.kiryana_record_sale(request.form.get("date"), party_id, item_id, qty, rate, mode,
                                    description, invoice_no)
        flash(f"Sale {db.kiryana_format_invoice_no('SALE', invoice_no)} recorded "
              f"({len(lines)} item{'s' if len(lines) != 1 else ''}).", "success")

        # server-side safety net for the stock warning shown in the UI -
        # catches it even if JS was off or the confirm dialog was bypassed
        oversold = [db.kiryana_get_item(item_id) for item_id, _, _ in lines]
        oversold = [i for i in oversold if i and i["stock_qty"] < 0]
        if oversold:
            names = ", ".join(f"{i['name']} ({i['stock_qty']:g})" for i in oversold)
            flash(f"This sale took stock below zero: {names}. Double-check the quantities.", "error")
        return redirect(url_for("kiryana_sales"))
    return render_template("app/kiryana/sales.html", items=db.kiryana_list_items(),
                            customers=db.kiryana_list_parties("Customer"),
                            invoices=db.kiryana_list_invoices("SALE"), today=date.today().isoformat())


@app.route("/kiryana/purchases", methods=["GET", "POST"])
@company_required
def kiryana_purchases():
    if request.method == "POST":
        item_ids = request.form.getlist("item_id[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        sale_rates = request.form.getlist("sale_rate[]")
        expiry_dates = request.form.getlist("expiry_date[]")
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        if mode == "Credit" and not party_id:
            flash("Pick a supplier for a credit purchase.", "error")
            return redirect(url_for("kiryana_purchases"))

        lines = []
        for item_id, qty, rate, sale_rate, expiry_date in zip_longest(item_ids, qtys, rates, sale_rates, expiry_dates, fillvalue=""):
            if not item_id:
                continue
            qty = float(qty or 0)
            rate = float(rate or 0)
            sale_rate = float(sale_rate or 0)
            if qty <= 0 or rate <= 0 or sale_rate <= 0:
                flash("Every line needs an item, a valid quantity, purchase rate, and sale rate.", "error")
                return redirect(url_for("kiryana_purchases"))
            lines.append((int(item_id), qty, rate, sale_rate, (expiry_date or "").strip() or None))
        if not lines:
            flash("Add at least one item line to the purchase.", "error")
            return redirect(url_for("kiryana_purchases"))

        invoice_no = db.kiryana_get_next_invoice_no("PURCHASE")
        for item_id, qty, rate, sale_rate, expiry_date in lines:
            db.kiryana_record_purchase(request.form.get("date"), party_id, item_id, qty, rate, mode,
                                        description, sale_rate, invoice_no, expiry_date)
        flash(f"Purchase {db.kiryana_format_invoice_no('PURCHASE', invoice_no)} recorded "
              f"({len(lines)} item{'s' if len(lines) != 1 else ''}).", "success")
        return redirect(url_for("kiryana_purchases"))
    return render_template("app/kiryana/purchases.html", items=db.kiryana_list_items(),
                            suppliers=db.kiryana_list_parties("Supplier"),
                            invoices=db.kiryana_list_invoices("PURCHASE"), today=date.today().isoformat())


@app.route("/kiryana/customers/add", methods=["POST"])
@company_required
def kiryana_add_customer():
    name = request.form.get("name", "").strip()
    if name:
        db.kiryana_add_party(name, request.form.get("phone", "").strip(), "Customer",
                              float(request.form.get("opening_balance") or 0))
        flash(f"Customer {name} added.", "success")
    else:
        flash("Customer name is required.", "error")
    return redirect(url_for("kiryana_sales"))


@app.route("/kiryana/customers/quick-add", methods=["POST"])
@company_required
def kiryana_customer_quick_add():
    """JSON counterpart to kiryana_add_customer - adds a customer without
    leaving the Sale Book form (see static/js/searchable-select.js)."""
    name = request.form.get("name", "").strip()
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    if any(p["name"].lower() == name.lower() for p in db.kiryana_list_parties("Customer")):
        return {"ok": False, "error": f"A customer named '{name}' already exists."}, 400
    new_id = db.kiryana_add_party(name, "", "Customer", 0)
    return {"ok": True, "id": new_id, "name": name}


@app.route("/kiryana/suppliers/quick-add", methods=["POST"])
@company_required
def kiryana_supplier_quick_add():
    """JSON counterpart to kiryana_add_supplier - adds a supplier without
    leaving the Purchase List form (see static/js/searchable-select.js)."""
    name = request.form.get("name", "").strip()
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    if any(p["name"].lower() == name.lower() for p in db.kiryana_list_parties("Supplier")):
        return {"ok": False, "error": f"A supplier named '{name}' already exists."}, 400
    new_id = db.kiryana_add_party(name, "", "Supplier", 0)
    return {"ok": True, "id": new_id, "name": name}


@app.route("/kiryana/suppliers/add", methods=["POST"])
@company_required
def kiryana_add_supplier():
    name = request.form.get("name", "").strip()
    if name:
        db.kiryana_add_party(name, request.form.get("phone", "").strip(), "Supplier", 0)
        flash(f"Supplier {name} added.", "success")
    else:
        flash("Supplier name is required.", "error")
    return redirect(url_for("kiryana_purchases"))


@app.route("/kiryana/print/<txn_type>/<int:txn_id>")
@company_required
def kiryana_print_bill(txn_type, txn_id):
    """Printable receipt for one Sale/Purchase/Return bill - txn_id can be
    any line item belonging to it, the rest are resolved via invoice_no
    (see db.kiryana_get_bill). Opened from the per-invoice Print button on
    the Recent Sales/Purchases/Returns lists."""
    txn_type = txn_type.upper()
    fallback_route = {"SALE": "kiryana_sales", "PURCHASE": "kiryana_purchases",
                       "SALE_RETURN": "kiryana_returns", "PURCHASE_RETURN": "kiryana_returns"}
    if txn_type not in fallback_route:
        flash("Invalid print request.", "error")
        return redirect(url_for("kiryana_dashboard"))
    bill = db.kiryana_get_bill(txn_type, txn_id)
    if not bill:
        flash("Entry not found.", "error")
        return redirect(url_for(fallback_route[txn_type]))
    if retail_pdf is not None:
        try:
            path = retail_pdf.generate_kiryana_bill_pdf(bill, txn_type)
            return send_file(path, as_attachment=False)
        except Exception as exc:
            flash(f"Couldn't generate PDF, showing print view instead: {exc}", "error")
    return render_template("app/kiryana/print_bill.html", bill=bill, txn_type=txn_type,
                            company_name=settings.get_company_name(), hide_shell=True)


@app.route("/kiryana/returns", methods=["GET", "POST"])
@company_required
def kiryana_returns():
    if request.method == "POST":
        return_type = request.form.get("return_type") if request.form.get("return_type") in ("Sale", "Purchase") else "Sale"
        item_id = request.form.get("item_id")
        qty = float(request.form.get("qty") or 0)
        rate = float(request.form.get("rate") or 0)
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        if not item_id or qty <= 0 or rate <= 0:
            flash("Pick an item and enter a valid quantity and rate.", "error")
            return redirect(url_for("kiryana_returns", type=return_type))
        who = "customer" if return_type == "Sale" else "supplier"
        if mode == "Credit" and not party_id:
            flash(f"Pick a {who} for a credit-note return.", "error")
            return redirect(url_for("kiryana_returns", type=return_type))

        txn_type = "SALE_RETURN" if return_type == "Sale" else "PURCHASE_RETURN"
        invoice_no = db.kiryana_get_next_invoice_no(txn_type)
        if return_type == "Sale":
            db.kiryana_record_sale_return(request.form.get("date"), party_id, int(item_id), qty, rate, mode,
                                           description, invoice_no)
        else:
            db.kiryana_record_purchase_return(request.form.get("date"), party_id, int(item_id), qty, rate, mode,
                                               description, invoice_no)
        flash(f"{return_type} Return {db.kiryana_format_invoice_no(txn_type, invoice_no)} recorded.", "success")
        return redirect(url_for("kiryana_returns", type=return_type))

    return_type = request.args.get("type") if request.args.get("type") in ("Sale", "Purchase") else "Sale"
    txn_type = "SALE_RETURN" if return_type == "Sale" else "PURCHASE_RETURN"
    source_type = "SALE" if return_type == "Sale" else "PURCHASE"
    return render_template("app/kiryana/returns.html", return_type=return_type,
                            items=db.kiryana_list_items(),
                            customers=db.kiryana_list_parties("Customer"),
                            suppliers=db.kiryana_list_parties("Supplier"),
                            invoices=db.kiryana_list_invoices(txn_type),
                            source_bills=db.kiryana_list_invoices(source_type, limit=200),
                            today=date.today().isoformat())


@app.route("/kiryana/cashbook")
@company_required
def kiryana_cashbook():
    events = db.kiryana_cash_book()
    return render_template("app/kiryana/cashbook.html", events=events,
                            closing_balance=events[-1]["balance"] if events else 0)


@app.route("/kiryana/ledger")
@company_required
def kiryana_ledger():
    party_type = request.args.get("type") if request.args.get("type") in ("Customer", "Supplier") else "Customer"
    party_id = request.args.get("party_id", type=int)
    ledger = db.kiryana_party_ledger(party_id) if party_id else None
    return render_template("app/kiryana/ledger.html", party_type=party_type,
                            parties=db.kiryana_list_parties(party_type),
                            party_id=party_id, ledger=ledger, today=date.today().isoformat())


@app.route("/kiryana/ledger/payment", methods=["POST"])
@company_required
def kiryana_ledger_payment():
    party_id = int(request.form.get("party_id"))
    amount = float(request.form.get("amount") or 0)
    party = db.kiryana_get_party(party_id)
    party_type = party["party_type"] if party else "Customer"
    if amount <= 0:
        flash("Enter a valid payment amount.", "error")
    else:
        db.kiryana_record_payment(request.form.get("date"), party_id, amount,
                                   request.form.get("description", "").strip())
        flash("Payment recorded.", "success")
    return redirect(url_for("kiryana_ledger", party_id=party_id, type=party_type))


@app.route("/kiryana/ledger/payment/<int:payment_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def kiryana_ledger_payment_edit(payment_id):
    payment = db.kiryana_get_payment(payment_id)
    if not payment:
        flash("Payment not found.", "error")
        return redirect(url_for("kiryana_ledger"))
    party = db.kiryana_get_party(payment["party_id"])
    default_return = url_for("kiryana_ledger", party_id=payment["party_id"],
                              type=party["party_type"] if party else "Customer")
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid payment amount.", "error")
            return redirect(url_for("kiryana_ledger_payment_edit", payment_id=payment_id,
                                     return_to=request.form.get("return_to", "")))
        db.kiryana_update_payment(payment_id, request.form.get("date"), amount,
                                   request.form.get("description", "").strip())
        flash("Payment updated.", "success")
        return redirect(request.form.get("return_to") or default_return)
    return render_template("app/kiryana/payment_edit.html", payment=payment, party=party,
                            return_to=request.args.get("return_to", default_return))


@app.route("/kiryana/ledger/payment/<int:payment_id>/delete", methods=["POST"])
@delete_permission_required
def kiryana_ledger_payment_delete(payment_id):
    payment = db.kiryana_get_payment(payment_id)
    if not payment:
        flash("Payment not found.", "error")
        return redirect(url_for("kiryana_ledger"))
    party = db.kiryana_get_party(payment["party_id"])
    db.kiryana_delete_payment(payment_id)
    flash("Payment deleted.", "success")
    return redirect(request.referrer or url_for("kiryana_ledger", party_id=payment["party_id"],
                                                 type=party["party_type"] if party else "Customer"))


@app.route("/kiryana/ledger/transaction/<int:txn_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def kiryana_ledger_transaction_edit(txn_id):
    txn = db.kiryana_get_transaction(txn_id)
    if not txn:
        flash("Entry not found.", "error")
        return redirect(url_for("kiryana_ledger"))
    party = db.kiryana_get_party(txn["party_id"]) if txn["party_id"] else None
    default_return = url_for("kiryana_ledger", party_id=txn["party_id"],
                              type=party["party_type"] if party else "Customer")
    if request.method == "POST":
        qty = float(request.form.get("qty") or 0)
        rate = float(request.form.get("rate") or 0)
        if qty <= 0 or rate <= 0:
            flash("Enter a valid quantity and rate.", "error")
            return redirect(url_for("kiryana_ledger_transaction_edit", txn_id=txn_id,
                                     return_to=request.form.get("return_to", "")))
        db.kiryana_update_transaction(txn_id, request.form.get("date"), qty, rate,
                                       request.form.get("description", "").strip())
        flash("Entry updated.", "success")
        return redirect(request.form.get("return_to") or default_return)
    return render_template("app/kiryana/transaction_edit.html", txn=txn, party=party,
                            return_to=request.args.get("return_to", default_return))


@app.route("/kiryana/ledger/transaction/<int:txn_id>/delete", methods=["POST"])
@delete_permission_required
def kiryana_ledger_transaction_delete(txn_id):
    txn = db.kiryana_get_transaction(txn_id)
    if not txn:
        flash("Entry not found.", "error")
        return redirect(url_for("kiryana_ledger"))
    party = db.kiryana_get_party(txn["party_id"]) if txn["party_id"] else None
    db.kiryana_delete_transaction(txn_id)
    flash("Entry deleted.", "success")
    return redirect(request.referrer or url_for("kiryana_ledger", party_id=txn["party_id"],
                                                 type=party["party_type"] if party else "Customer"))


@app.route("/kiryana/expenses", methods=["GET", "POST"])
@company_required
def kiryana_expenses():
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid expense amount.", "error")
            return redirect(url_for("kiryana_expenses"))
        db.kiryana_add_expense(request.form.get("date"), request.form.get("category", "").strip(),
                                request.form.get("description", "").strip(), amount)
        flash("Expense recorded.", "success")
        return redirect(url_for("kiryana_expenses"))
    expenses = db.kiryana_list_expenses()
    total_expenses = db.kiryana_total_expenses()
    total_sales = db.kiryana_total_sales()
    return render_template("app/kiryana/expenses.html", expenses=expenses, total_expenses=total_expenses,
                            total_sales=total_sales, net_profit=total_sales - total_expenses,
                            today=date.today().isoformat())


@app.route("/kiryana/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def kiryana_edit_expense(expense_id):
    expense = db.kiryana_get_expense(expense_id)
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("kiryana_expenses"))
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid expense amount.", "error")
            return redirect(url_for("kiryana_edit_expense", expense_id=expense_id))
        db.kiryana_update_expense(expense_id, request.form.get("date"), request.form.get("category", "").strip(),
                                   request.form.get("description", "").strip(), amount)
        flash("Expense updated.", "success")
        return redirect(url_for("kiryana_expenses"))
    return render_template("app/kiryana/expense_edit.html", expense=expense)


@app.route("/kiryana/expenses/<int:expense_id>/delete", methods=["POST"])
@delete_permission_required
def kiryana_expense_delete(expense_id):
    db.kiryana_delete_expense(expense_id)
    flash("Expense deleted.", "success")
    return redirect(url_for("kiryana_expenses"))


# =======================================================================
# HARDWARE MODULE — hardware-store business type: Inventory, Sale Book,
# Purchase List, Returns, Cash Book, Ledger, Expenses. Separate engine
# from both Yarn and Kiryana above (see db.py's Hardware section for why),
# reachable once a company picks "Hardware" from the business-type picker
# (business_select).
# =======================================================================
HARDWARE_STANDARD_UNITS = ["pcs", "box", "set", "pair", "roll", "meter", "kg", "carton", "packet", "bundle"]


def _resolve_hardware_unit(form):
    """The Unit field is a dropdown of common units plus an 'Other' option
    that reveals a free-text box (see inventory.html/item_edit.html) -
    this resolves whichever one the user actually meant."""
    unit = form.get("unit", "").strip()
    if unit == "__other__":
        unit = form.get("unit_other", "").strip()
    return unit


@app.route("/hardware")
@company_required
def hardware_dashboard():
    today = date.today().isoformat()
    stock = db.hardware_stock_summary()
    receivable = db.hardware_balance_summary("Customer")
    payable = db.hardware_balance_summary("Supplier")
    sales_today_total = sum(t["amount"] for t in db.hardware_list_transactions("SALE", limit=1000) if t["date"] == today)
    total_sales = db.hardware_total_sales()
    total_expenses = db.hardware_total_expenses()
    cash_events = db.hardware_cash_book()
    cash_balance = cash_events[-1]["balance"] if cash_events else 0
    low_stock = db.hardware_low_stock_summary()
    expiring = db.hardware_expiring_batches()
    open_quotations = db.hardware_list_invoices("QUOTATION", limit=10)
    return render_template("app/hardware/dashboard.html", stock=stock, receivable=receivable, payable=payable,
                            sales_today_total=sales_today_total, total_sales=total_sales,
                            net_profit=total_sales - total_expenses, cash_balance=cash_balance,
                            low_stock=low_stock, expiring=expiring, open_quotations_count=len(open_quotations),
                            tax_rate=settings.get_hardware_tax_rate(), gst_number=settings.get_hardware_gst_number())


@app.route("/hardware/settings/tax", methods=["POST"])
@company_admin_required
def hardware_tax_settings():
    settings.set_hardware_tax_rate(float(request.form.get("tax_rate") or 0))
    settings.set_hardware_gst_number(request.form.get("gst_number", "").strip())
    flash("Tax settings updated.", "success")
    return redirect(url_for("hardware_dashboard"))


@app.route("/hardware/inventory", methods=["GET", "POST"])
@company_required
def hardware_inventory():
    if request.method == "POST":
        names = request.form.getlist("name[]")
        units = request.form.getlist("unit[]")
        unit_others = request.form.getlist("unit_other[]")
        categories_in = request.form.getlist("category[]")
        barcodes_in = request.form.getlist("barcode[]")
        purchase_rates = request.form.getlist("purchase_rate[]")
        sale_rates = request.form.getlist("sale_rate[]")
        opening_qtys = request.form.getlist("opening_qty[]")
        reorder_levels = request.form.getlist("reorder_level[]")
        purchase_units = request.form.getlist("purchase_unit[]")
        conversion_factors = request.form.getlist("conversion_factor[]")
        parent_item_ids = request.form.getlist("parent_item_id[]")
        variant_names = request.form.getlist("variant_name[]")

        existing_barcodes = {i["barcode"] for i in db.hardware_list_items() if i["barcode"]}
        seen_barcodes = set()
        rows = []
        for (name, unit, unit_other, category, barcode, p_rate, s_rate, opening_qty, reorder, p_unit, factor,
             parent_item_id, variant_name) in zip_longest(
            names, units, unit_others, categories_in, barcodes_in, purchase_rates, sale_rates,
            opening_qtys, reorder_levels, purchase_units, conversion_factors, parent_item_ids, variant_names,
            fillvalue="",
        ):
            name = (name or "").strip()
            if not name:
                continue
            barcode = (barcode or "").strip() or None
            if barcode and (barcode in existing_barcodes or barcode in seen_barcodes):
                flash(f"Barcode '{barcode}' is already used by another item.", "error")
                return redirect(url_for("hardware_inventory"))
            if barcode:
                seen_barcodes.add(barcode)
            resolved_unit = unit_other.strip() if unit == "__other__" else unit.strip()
            rows.append((
                name, resolved_unit, float(p_rate or 0), float(s_rate or 0), float(opening_qty or 0),
                barcode, float(reorder or 0), category.strip() or None, p_unit.strip() or None,
                float(factor or 1), int(parent_item_id) if parent_item_id else None,
                variant_name.strip() or None,
            ))
        if not rows:
            flash("Add at least one item (a name is required).", "error")
            return redirect(url_for("hardware_inventory"))

        for row in rows:
            db.hardware_add_item(*row)
        if len(rows) == 1:
            flash(f"{rows[0][0]} added to inventory.", "success")
        else:
            flash(f"{len(rows)} items added to inventory.", "success")
        return redirect(url_for("hardware_inventory"))
    return render_template("app/hardware/inventory.html", items=db.hardware_list_items(),
                            standard_units=HARDWARE_STANDARD_UNITS, categories=db.hardware_list_categories(),
                            parent_items=db.hardware_list_parent_items())


@app.route("/hardware/items/quick-add", methods=["POST"])
@company_required
def hardware_item_quick_add():
    """Adds a new inventory item without leaving the Sale/Purchase form -
    called via JS (see static/js/searchable-select.js's quick-add
    support, and static/js/barcode-scanner.js for the barcode-not-found
    flow), returns JSON so the new item can be dropped straight into
    that page's Item dropdown, already selected, with everything else on
    the form left untouched. Rate/unit start at 0/blank - meant for
    fixing up on the Inventory page later, not filling in mid-entry."""
    name = request.form.get("name", "").strip()
    barcode = request.form.get("barcode", "").strip() or None
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    items = db.hardware_list_items()
    if any(i["name"].lower() == name.lower() for i in items):
        return {"ok": False, "error": f"An item named '{name}' already exists."}, 400
    if barcode and any(i["barcode"] == barcode for i in items):
        return {"ok": False, "error": f"Barcode '{barcode}' is already used by another item."}, 400
    new_id = db.hardware_add_item(name, request.form.get("unit", "").strip(), 0, 0, 0, barcode)
    return {"ok": True, "id": new_id, "name": name, "unit": "", "purchase_rate": 0, "sale_rate": 0, "barcode": barcode}


@app.route("/hardware/items/by-barcode")
@company_required
def hardware_item_by_barcode():
    """Looks up an item by scanned barcode (see static/js/barcode-scanner.js)
    - called from the Sale/Purchase forms' scan input, both the
    keyboard-wedge USB/Bluetooth scanner path and the camera-based one."""
    code = request.args.get("code", "").strip()
    if not code:
        return {"ok": False, "error": "No barcode given."}, 400
    item = db.hardware_get_item_by_barcode(code)
    if not item:
        return {"ok": False, "error": f"No item found for barcode {code}."}, 404
    return {"ok": True, **item}


@app.route("/hardware/inventory/<int:item_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def hardware_edit_item(item_id):
    item = db.hardware_get_item(item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("hardware_inventory"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        barcode = request.form.get("barcode", "").strip() or None
        if not name:
            flash("Item name is required.", "error")
            return redirect(url_for("hardware_edit_item", item_id=item_id))
        if barcode and any(i["barcode"] == barcode and i["id"] != item_id for i in db.hardware_list_items()):
            flash(f"Barcode '{barcode}' is already used by another item.", "error")
            return redirect(url_for("hardware_edit_item", item_id=item_id))
        parent_item_id = request.form.get("parent_item_id") or None
        if parent_item_id and int(parent_item_id) == item_id:
            flash("An item can't be its own variant parent.", "error")
            return redirect(url_for("hardware_edit_item", item_id=item_id))
        db.hardware_update_item(
            item_id, name, _resolve_hardware_unit(request.form),
            float(request.form.get("purchase_rate") or 0), float(request.form.get("sale_rate") or 0),
            float(request.form.get("stock_qty") or 0), barcode,
            float(request.form.get("reorder_level") or 0),
            request.form.get("category", "").strip() or None,
            request.form.get("purchase_unit", "").strip() or None,
            float(request.form.get("conversion_factor") or 1),
            int(parent_item_id) if parent_item_id else None,
            request.form.get("variant_name", "").strip() or None,
        )
        flash("Item updated.", "success")
        return redirect(url_for("hardware_inventory"))
    parent_items = [i for i in db.hardware_list_parent_items() if i["id"] != item_id]
    return render_template("app/hardware/item_edit.html", item=item, standard_units=HARDWARE_STANDARD_UNITS,
                            categories=db.hardware_list_categories(), parent_items=parent_items)


@app.route("/hardware/inventory/<int:item_id>/delete", methods=["POST"])
@company_required
def hardware_delete_item(item_id):
    if db.hardware_item_has_transactions(item_id):
        flash("Can't delete an item with sales or purchases recorded against it.", "error")
        return redirect(url_for("hardware_inventory"))
    db.hardware_delete_item(item_id)
    flash("Item removed.", "success")
    return redirect(url_for("hardware_inventory"))


@app.route("/hardware/sales", methods=["GET", "POST"])
@company_required
def hardware_sales():
    if request.method == "POST":
        item_ids = request.form.getlist("item_id[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()
        amount_paid_now = float(request.form.get("amount_paid_now") or 0)

        if mode == "Credit" and not party_id:
            flash("Pick a customer for a credit sale.", "error")
            return redirect(url_for("hardware_sales"))

        lines = []
        for item_id, qty, rate in zip_longest(item_ids, qtys, rates, fillvalue=""):
            if not item_id:
                continue
            qty = float(qty or 0)
            rate = float(rate or 0)
            if qty <= 0 or rate <= 0:
                flash("Every line needs an item, a valid quantity, and a valid rate.", "error")
                return redirect(url_for("hardware_sales"))
            lines.append((int(item_id), qty, rate))
        if not lines:
            flash("Add at least one item line to the sale.", "error")
            return redirect(url_for("hardware_sales"))

        invoice_no = db.hardware_get_next_invoice_no("SALE")
        for item_id, qty, rate in lines:
            db.hardware_record_sale(request.form.get("date"), party_id, item_id, qty, rate, mode,
                                    description, invoice_no)

        # split payment: a Credit sale can still be partly paid on the
        # spot (e.g. Rs 5,000 cash now, the rest on account) - recorded as
        # an ordinary payment against the same party right after the sale,
        # reusing the existing Ledger payment machinery rather than a new
        # "part cash, part credit" mode of its own
        if mode == "Credit" and party_id and amount_paid_now > 0:
            db.hardware_record_payment(request.form.get("date"), party_id, amount_paid_now,
                                        "Paid at time of sale")

        flash(f"Sale {db.hardware_format_invoice_no('SALE', invoice_no)} recorded "
              f"({len(lines)} item{'s' if len(lines) != 1 else ''}).", "success")

        # server-side safety net for the stock warning shown in the UI -
        # catches it even if JS was off or the confirm dialog was bypassed
        oversold = [db.hardware_get_item(item_id) for item_id, _, _ in lines]
        oversold = [i for i in oversold if i and i["stock_qty"] < 0]
        if oversold:
            names = ", ".join(f"{i['name']} ({i['stock_qty']:g})" for i in oversold)
            flash(f"This sale took stock below zero: {names}. Double-check the quantities.", "error")

        # server-side safety net for the credit-limit warning shown in the
        # UI - same non-blocking pattern as the oversell check above
        if mode == "Credit" and party_id:
            party = db.hardware_get_party(party_id)
            if party and party["credit_limit"] > 0:
                balance = db.hardware_party_balance(party_id)
                if balance > party["credit_limit"]:
                    flash(f"{party['name']}'s balance (Rs. {balance:,.2f}) is now over their credit limit "
                          f"(Rs. {party['credit_limit']:,.2f}).", "error")
        return redirect(url_for("hardware_sales"))

    customers = db.hardware_list_parties("Customer")
    for c in customers:
        c["balance"] = db.hardware_party_balance(c["id"])
    return render_template("app/hardware/sales.html", items=db.hardware_list_items(),
                            customers=customers, customer_prices=db.hardware_all_customer_prices_map(),
                            invoices=db.hardware_list_invoices("SALE"), today=date.today().isoformat())


@app.route("/hardware/purchases", methods=["GET", "POST"])
@company_required
def hardware_purchases():
    if request.method == "POST":
        item_ids = request.form.getlist("item_id[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        sale_rates = request.form.getlist("sale_rate[]")
        expiry_dates = request.form.getlist("expiry_date[]")
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        if mode == "Credit" and not party_id:
            flash("Pick a supplier for a credit purchase.", "error")
            return redirect(url_for("hardware_purchases"))

        lines = []
        for item_id, qty, rate, sale_rate, expiry_date in zip_longest(item_ids, qtys, rates, sale_rates, expiry_dates, fillvalue=""):
            if not item_id:
                continue
            qty = float(qty or 0)
            rate = float(rate or 0)
            sale_rate = float(sale_rate or 0)
            if qty <= 0 or rate <= 0 or sale_rate <= 0:
                flash("Every line needs an item, a valid quantity, purchase rate, and sale rate.", "error")
                return redirect(url_for("hardware_purchases"))
            lines.append((int(item_id), qty, rate, sale_rate, (expiry_date or "").strip() or None))
        if not lines:
            flash("Add at least one item line to the purchase.", "error")
            return redirect(url_for("hardware_purchases"))

        invoice_no = db.hardware_get_next_invoice_no("PURCHASE")
        for item_id, qty, rate, sale_rate, expiry_date in lines:
            db.hardware_record_purchase(request.form.get("date"), party_id, item_id, qty, rate, mode,
                                        description, sale_rate, invoice_no, expiry_date)
        flash(f"Purchase {db.hardware_format_invoice_no('PURCHASE', invoice_no)} recorded "
              f"({len(lines)} item{'s' if len(lines) != 1 else ''}).", "success")
        return redirect(url_for("hardware_purchases"))
    return render_template("app/hardware/purchases.html", items=db.hardware_list_items(),
                            suppliers=db.hardware_list_parties("Supplier"),
                            invoices=db.hardware_list_invoices("PURCHASE"), today=date.today().isoformat())


@app.route("/hardware/customers/add", methods=["POST"])
@company_required
def hardware_add_customer():
    name = request.form.get("name", "").strip()
    if name:
        db.hardware_add_party(name, request.form.get("phone", "").strip(), "Customer",
                              float(request.form.get("opening_balance") or 0))
        flash(f"Customer {name} added.", "success")
    else:
        flash("Customer name is required.", "error")
    return redirect(url_for("hardware_sales"))


@app.route("/hardware/customers/quick-add", methods=["POST"])
@company_required
def hardware_customer_quick_add():
    """JSON counterpart to hardware_add_customer - adds a customer without
    leaving the Sale Book form (see static/js/searchable-select.js)."""
    name = request.form.get("name", "").strip()
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    if any(p["name"].lower() == name.lower() for p in db.hardware_list_parties("Customer")):
        return {"ok": False, "error": f"A customer named '{name}' already exists."}, 400
    new_id = db.hardware_add_party(name, "", "Customer", 0)
    return {"ok": True, "id": new_id, "name": name}


@app.route("/hardware/suppliers/quick-add", methods=["POST"])
@company_required
def hardware_supplier_quick_add():
    """JSON counterpart to hardware_add_supplier - adds a supplier without
    leaving the Purchase List form (see static/js/searchable-select.js)."""
    name = request.form.get("name", "").strip()
    if not name:
        return {"ok": False, "error": "Name is required."}, 400
    if any(p["name"].lower() == name.lower() for p in db.hardware_list_parties("Supplier")):
        return {"ok": False, "error": f"A supplier named '{name}' already exists."}, 400
    new_id = db.hardware_add_party(name, "", "Supplier", 0)
    return {"ok": True, "id": new_id, "name": name}


@app.route("/hardware/suppliers/add", methods=["POST"])
@company_required
def hardware_add_supplier():
    name = request.form.get("name", "").strip()
    if name:
        db.hardware_add_party(name, request.form.get("phone", "").strip(), "Supplier", 0)
        flash(f"Supplier {name} added.", "success")
    else:
        flash("Supplier name is required.", "error")
    return redirect(url_for("hardware_purchases"))


@app.route("/hardware/parties")
@company_required
def hardware_parties():
    party_type = request.args.get("type") if request.args.get("type") in ("Customer", "Supplier") else "Customer"
    parties = db.hardware_list_parties(party_type)
    for p in parties:
        p["balance"] = db.hardware_party_balance(p["id"])
    return render_template("app/hardware/parties.html", party_type=party_type, parties=parties)


@app.route("/hardware/parties/<int:party_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def hardware_edit_party(party_id):
    party = db.hardware_get_party(party_id)
    if not party:
        flash("Party not found.", "error")
        return redirect(url_for("hardware_parties"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("hardware_edit_party", party_id=party_id))
        db.hardware_update_party(
            party_id, name, request.form.get("phone", "").strip(),
            float(request.form.get("opening_balance") or 0),
            float(request.form.get("credit_limit") or 0),
            request.form.get("gst_number", "").strip(),
        )
        flash("Party updated.", "success")
        return redirect(url_for("hardware_parties", type=party["party_type"]))
    prices = db.hardware_list_customer_prices(party_id) if party["party_type"] == "Customer" else []
    return render_template("app/hardware/party_edit.html", party=party, prices=prices,
                            items=db.hardware_list_items(), balance=db.hardware_party_balance(party_id))


@app.route("/hardware/parties/<int:party_id>/delete", methods=["POST"])
@delete_permission_required
def hardware_delete_party(party_id):
    party = db.hardware_get_party(party_id)
    if not party:
        flash("Party not found.", "error")
        return redirect(url_for("hardware_parties"))
    if db.hardware_party_has_activity(party_id):
        flash("Can't delete a party with sales, purchases, or payments recorded against them.", "error")
        return redirect(url_for("hardware_parties", type=party["party_type"]))
    db.hardware_delete_party(party_id)
    flash("Party deleted.", "success")
    return redirect(url_for("hardware_parties", type=party["party_type"]))


@app.route("/hardware/parties/<int:party_id>/prices/add", methods=["POST"])
@edit_permission_required
def hardware_add_customer_price(party_id):
    item_id = request.form.get("item_id")
    rate = float(request.form.get("rate") or 0)
    if not item_id or rate <= 0:
        flash("Pick an item and enter a valid rate.", "error")
    else:
        db.hardware_set_customer_price(party_id, int(item_id), rate)
        flash("Special price saved.", "success")
    return redirect(url_for("hardware_edit_party", party_id=party_id))


@app.route("/hardware/parties/<int:party_id>/prices/<int:price_id>/delete", methods=["POST"])
@edit_permission_required
def hardware_delete_customer_price(party_id, price_id):
    db.hardware_delete_customer_price(price_id)
    flash("Special price removed.", "success")
    return redirect(url_for("hardware_edit_party", party_id=party_id))


@app.route("/hardware/print/<txn_type>/<int:txn_id>")
@company_required
def hardware_print_bill(txn_type, txn_id):
    """Printable receipt for one Sale/Purchase/Return bill - txn_id can be
    any line item belonging to it, the rest are resolved via invoice_no
    (see db.hardware_get_bill). Opened from the per-invoice Print button on
    the Recent Sales/Purchases/Returns lists."""
    txn_type = txn_type.upper()
    fallback_route = {"SALE": "hardware_sales", "PURCHASE": "hardware_purchases",
                       "SALE_RETURN": "hardware_returns", "PURCHASE_RETURN": "hardware_returns",
                       "QUOTATION": "hardware_quotations", "QUOTATION_CONVERTED": "hardware_quotations"}
    if txn_type not in fallback_route:
        flash("Invalid print request.", "error")
        return redirect(url_for("hardware_dashboard"))
    bill = db.hardware_get_bill(txn_type, txn_id)
    if not bill:
        flash("Entry not found.", "error")
        return redirect(url_for(fallback_route[txn_type]))
    tax_rate = settings.get_hardware_tax_rate()
    tax_amount = round(bill["total"] * tax_rate / 100, 2) if tax_rate else 0
    gst_number = settings.get_hardware_gst_number()
    if retail_pdf is not None:
        try:
            path = retail_pdf.generate_hardware_bill_pdf(bill, txn_type, tax_rate=tax_rate,
                                                           tax_amount=tax_amount, gst_number=gst_number)
            return send_file(path, as_attachment=False)
        except Exception as exc:
            flash(f"Couldn't generate PDF, showing print view instead: {exc}", "error")
    return render_template("app/hardware/print_bill.html", bill=bill, txn_type=txn_type,
                            company_name=settings.get_company_name(), hide_shell=True,
                            tax_rate=tax_rate, tax_amount=tax_amount, gst_number=gst_number)


@app.route("/hardware/quotations", methods=["GET", "POST"])
@company_required
def hardware_quotations():
    if request.method == "POST":
        item_ids = request.form.getlist("item_id[]")
        qtys = request.form.getlist("qty[]")
        rates = request.form.getlist("rate[]")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        lines = []
        for item_id, qty, rate in zip_longest(item_ids, qtys, rates, fillvalue=""):
            if not item_id:
                continue
            qty = float(qty or 0)
            rate = float(rate or 0)
            if qty <= 0 or rate <= 0:
                flash("Every line needs an item, a valid quantity, and a valid rate.", "error")
                return redirect(url_for("hardware_quotations"))
            lines.append((int(item_id), qty, rate))
        if not lines:
            flash("Add at least one item line to the quotation.", "error")
            return redirect(url_for("hardware_quotations"))

        invoice_no = db.hardware_get_next_invoice_no("QUOTATION")
        for item_id, qty, rate in lines:
            db.hardware_record_quotation_line(request.form.get("date"), party_id, item_id, qty, rate,
                                               description, invoice_no)
        flash(f"Quotation {db.hardware_format_invoice_no('QUOTATION', invoice_no)} saved "
              f"({len(lines)} item{'s' if len(lines) != 1 else ''}). It won't affect stock or the ledger "
              f"unless you convert it to a Sale.", "success")
        return redirect(url_for("hardware_quotations"))
    return render_template("app/hardware/quotations.html", items=db.hardware_list_items(),
                            customers=db.hardware_list_parties("Customer"),
                            open_quotations=db.hardware_list_invoices("QUOTATION"),
                            today=date.today().isoformat())


@app.route("/hardware/quotations/<int:invoice_no>/convert", methods=["POST"])
@edit_permission_required
def hardware_convert_quotation(invoice_no):
    sale_invoice_no = db.hardware_convert_quotation(invoice_no, date.today().isoformat())
    if sale_invoice_no is None:
        flash("Quotation not found or already converted.", "error")
    else:
        flash(f"Converted to Sale {db.hardware_format_invoice_no('SALE', sale_invoice_no)}.", "success")
    return redirect(url_for("hardware_quotations"))


@app.route("/hardware/returns", methods=["GET", "POST"])
@company_required
def hardware_returns():
    if request.method == "POST":
        return_type = request.form.get("return_type") if request.form.get("return_type") in ("Sale", "Purchase") else "Sale"
        item_id = request.form.get("item_id")
        qty = float(request.form.get("qty") or 0)
        rate = float(request.form.get("rate") or 0)
        mode = request.form.get("mode", "Cash")
        party_id = request.form.get("party_id") or None
        party_id = int(party_id) if party_id else None
        description = request.form.get("description", "").strip()

        if not item_id or qty <= 0 or rate <= 0:
            flash("Pick an item and enter a valid quantity and rate.", "error")
            return redirect(url_for("hardware_returns", type=return_type))
        who = "customer" if return_type == "Sale" else "supplier"
        if mode == "Credit" and not party_id:
            flash(f"Pick a {who} for a credit-note return.", "error")
            return redirect(url_for("hardware_returns", type=return_type))

        txn_type = "SALE_RETURN" if return_type == "Sale" else "PURCHASE_RETURN"
        invoice_no = db.hardware_get_next_invoice_no(txn_type)
        if return_type == "Sale":
            db.hardware_record_sale_return(request.form.get("date"), party_id, int(item_id), qty, rate, mode,
                                           description, invoice_no)
        else:
            db.hardware_record_purchase_return(request.form.get("date"), party_id, int(item_id), qty, rate, mode,
                                               description, invoice_no)
        flash(f"{return_type} Return {db.hardware_format_invoice_no(txn_type, invoice_no)} recorded.", "success")
        return redirect(url_for("hardware_returns", type=return_type))

    return_type = request.args.get("type") if request.args.get("type") in ("Sale", "Purchase") else "Sale"
    txn_type = "SALE_RETURN" if return_type == "Sale" else "PURCHASE_RETURN"
    source_type = "SALE" if return_type == "Sale" else "PURCHASE"
    return render_template("app/hardware/returns.html", return_type=return_type,
                            items=db.hardware_list_items(),
                            customers=db.hardware_list_parties("Customer"),
                            suppliers=db.hardware_list_parties("Supplier"),
                            invoices=db.hardware_list_invoices(txn_type),
                            source_bills=db.hardware_list_invoices(source_type, limit=200),
                            today=date.today().isoformat())


@app.route("/hardware/cashbook")
@company_required
def hardware_cashbook():
    events = db.hardware_cash_book()
    return render_template("app/hardware/cashbook.html", events=events,
                            closing_balance=events[-1]["balance"] if events else 0)


@app.route("/hardware/ledger")
@company_required
def hardware_ledger():
    party_type = request.args.get("type") if request.args.get("type") in ("Customer", "Supplier") else "Customer"
    party_id = request.args.get("party_id", type=int)
    ledger = db.hardware_party_ledger(party_id) if party_id else None
    return render_template("app/hardware/ledger.html", party_type=party_type,
                            parties=db.hardware_list_parties(party_type),
                            party_id=party_id, ledger=ledger, today=date.today().isoformat())


@app.route("/hardware/ledger/payment", methods=["POST"])
@company_required
def hardware_ledger_payment():
    party_id = int(request.form.get("party_id"))
    amount = float(request.form.get("amount") or 0)
    party = db.hardware_get_party(party_id)
    party_type = party["party_type"] if party else "Customer"
    if amount <= 0:
        flash("Enter a valid payment amount.", "error")
    else:
        db.hardware_record_payment(request.form.get("date"), party_id, amount,
                                   request.form.get("description", "").strip())
        flash("Payment recorded.", "success")
    return redirect(url_for("hardware_ledger", party_id=party_id, type=party_type))


@app.route("/hardware/ledger/payment/<int:payment_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def hardware_ledger_payment_edit(payment_id):
    payment = db.hardware_get_payment(payment_id)
    if not payment:
        flash("Payment not found.", "error")
        return redirect(url_for("hardware_ledger"))
    party = db.hardware_get_party(payment["party_id"])
    default_return = url_for("hardware_ledger", party_id=payment["party_id"],
                              type=party["party_type"] if party else "Customer")
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid payment amount.", "error")
            return redirect(url_for("hardware_ledger_payment_edit", payment_id=payment_id,
                                     return_to=request.form.get("return_to", "")))
        db.hardware_update_payment(payment_id, request.form.get("date"), amount,
                                   request.form.get("description", "").strip())
        flash("Payment updated.", "success")
        return redirect(request.form.get("return_to") or default_return)
    return render_template("app/hardware/payment_edit.html", payment=payment, party=party,
                            return_to=request.args.get("return_to", default_return))


@app.route("/hardware/ledger/payment/<int:payment_id>/delete", methods=["POST"])
@delete_permission_required
def hardware_ledger_payment_delete(payment_id):
    payment = db.hardware_get_payment(payment_id)
    if not payment:
        flash("Payment not found.", "error")
        return redirect(url_for("hardware_ledger"))
    party = db.hardware_get_party(payment["party_id"])
    db.hardware_delete_payment(payment_id)
    flash("Payment deleted.", "success")
    return redirect(request.referrer or url_for("hardware_ledger", party_id=payment["party_id"],
                                                 type=party["party_type"] if party else "Customer"))


@app.route("/hardware/ledger/transaction/<int:txn_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def hardware_ledger_transaction_edit(txn_id):
    txn = db.hardware_get_transaction(txn_id)
    if not txn:
        flash("Entry not found.", "error")
        return redirect(url_for("hardware_ledger"))
    party = db.hardware_get_party(txn["party_id"]) if txn["party_id"] else None
    default_return = url_for("hardware_ledger", party_id=txn["party_id"],
                              type=party["party_type"] if party else "Customer")
    if request.method == "POST":
        qty = float(request.form.get("qty") or 0)
        rate = float(request.form.get("rate") or 0)
        if qty <= 0 or rate <= 0:
            flash("Enter a valid quantity and rate.", "error")
            return redirect(url_for("hardware_ledger_transaction_edit", txn_id=txn_id,
                                     return_to=request.form.get("return_to", "")))
        db.hardware_update_transaction(txn_id, request.form.get("date"), qty, rate,
                                       request.form.get("description", "").strip())
        flash("Entry updated.", "success")
        return redirect(request.form.get("return_to") or default_return)
    return render_template("app/hardware/transaction_edit.html", txn=txn, party=party,
                            return_to=request.args.get("return_to", default_return))


@app.route("/hardware/ledger/transaction/<int:txn_id>/delete", methods=["POST"])
@delete_permission_required
def hardware_ledger_transaction_delete(txn_id):
    txn = db.hardware_get_transaction(txn_id)
    if not txn:
        flash("Entry not found.", "error")
        return redirect(url_for("hardware_ledger"))
    party = db.hardware_get_party(txn["party_id"]) if txn["party_id"] else None
    db.hardware_delete_transaction(txn_id)
    flash("Entry deleted.", "success")
    return redirect(request.referrer or url_for("hardware_ledger", party_id=txn["party_id"],
                                                 type=party["party_type"] if party else "Customer"))


@app.route("/hardware/expenses", methods=["GET", "POST"])
@company_required
def hardware_expenses():
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid expense amount.", "error")
            return redirect(url_for("hardware_expenses"))
        db.hardware_add_expense(request.form.get("date"), request.form.get("category", "").strip(),
                                request.form.get("description", "").strip(), amount)
        flash("Expense recorded.", "success")
        return redirect(url_for("hardware_expenses"))
    expenses = db.hardware_list_expenses()
    total_expenses = db.hardware_total_expenses()
    total_sales = db.hardware_total_sales()
    return render_template("app/hardware/expenses.html", expenses=expenses, total_expenses=total_expenses,
                            total_sales=total_sales, net_profit=total_sales - total_expenses,
                            today=date.today().isoformat())


@app.route("/hardware/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def hardware_edit_expense(expense_id):
    expense = db.hardware_get_expense(expense_id)
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("hardware_expenses"))
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        if amount <= 0:
            flash("Enter a valid expense amount.", "error")
            return redirect(url_for("hardware_edit_expense", expense_id=expense_id))
        db.hardware_update_expense(expense_id, request.form.get("date"), request.form.get("category", "").strip(),
                                   request.form.get("description", "").strip(), amount)
        flash("Expense updated.", "success")
        return redirect(url_for("hardware_expenses"))
    return render_template("app/hardware/expense_edit.html", expense=expense)


@app.route("/hardware/expenses/<int:expense_id>/delete", methods=["POST"])
@delete_permission_required
def hardware_expense_delete(expense_id):
    db.hardware_delete_expense(expense_id)
    flash("Expense deleted.", "success")
    return redirect(url_for("hardware_expenses"))

# --- Parties ---
@app.route("/data-import")
@company_admin_required
def data_import_page():
    return render_template("app/data_import.html")


@app.route("/data-import/template/<kind>")
@company_admin_required
def data_import_template(kind):
    if data_import is None:
        flash("Import isn't available.", "error")
        return redirect(url_for("data_import_page"))
    tmp_dir = tempfile.mkdtemp(prefix="import_template_")
    if kind == "parties":
        path = data_import.generate_party_template(os.path.join(tmp_dir, "Parties_Import_Template.xlsx"))
    elif kind == "quality":
        path = data_import.generate_quality_template(os.path.join(tmp_dir, "Items_Import_Template.xlsx"))
    elif kind == "opening_entries":
        path = data_import.generate_opening_entries_template(os.path.join(tmp_dir, "Outstanding_Invoices_Template.xlsx"))
    else:
        flash("Unknown template.", "error")
        return redirect(url_for("data_import_page"))
    return send_file(path, as_attachment=True)


@app.route("/data-import/parties", methods=["POST"])
@company_admin_required
def data_import_parties():
    if data_import is None:
        flash("Import isn't available.", "error")
        return redirect(url_for("data_import_page"))
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a file to upload first.", "error")
        return redirect(url_for("data_import_page"))
    conn = db.get_connection()
    result = data_import.import_parties(f, conn)
    conn.close()
    msg = f"Imported {result['created']} new part{'y' if result['created'] == 1 else 'ies'}."
    if result["skipped_duplicate"]:
        msg += f" Skipped {result['skipped_duplicate']} (name already existed)."
    flash(msg, "success" if result["created"] else "error")
    for e in result["errors"][:10]:
        flash(e, "error")
    return redirect(url_for("parties"))


@app.route("/data-import/quality", methods=["POST"])
@company_admin_required
def data_import_quality():
    if data_import is None:
        flash("Import isn't available.", "error")
        return redirect(url_for("data_import_page"))
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a file to upload first.", "error")
        return redirect(url_for("data_import_page"))
    conn = db.get_connection()
    result = data_import.import_quality(f, conn)
    conn.close()
    msg = f"Imported {result['created']} new item{'s' if result['created'] != 1 else ''}."
    if result["skipped_duplicate"]:
        msg += f" Skipped {result['skipped_duplicate']} (name already existed)."
    flash(msg, "success" if result["created"] else "error")
    for e in result["errors"][:10]:
        flash(e, "error")
    return redirect(url_for("quality"))


@app.route("/data-import/opening-entries", methods=["POST"])
@company_admin_required
def data_import_opening_entries():
    if data_import is None:
        flash("Import isn't available.", "error")
        return redirect(url_for("data_import_page"))
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a file to upload first.", "error")
        return redirect(url_for("data_import_page"))
    conn = db.get_connection()
    result = data_import.import_opening_entries(f, conn)
    conn.close()
    msg = f"Imported {result['created']} outstanding invoice{'s' if result['created'] != 1 else ''}."
    flash(msg, "success" if result["created"] else "error")
    for e in result["errors"][:15]:
        flash(e, "error")
    return redirect(url_for("data_import_page"))


@app.route("/parties", methods=["GET", "POST"])
@company_required
def parties():
    if request.method == "POST":
        conn = db.get_connection()
        cur = conn.cursor()
        party_type = request.form.get("party_type", "Customer")
        brokerage_type = request.form.get("brokerage_type") if party_type == "Broker" else None
        brokerage_rate = float(request.form.get("brokerage_rate") or 0) if party_type == "Broker" else None
        cur.execute(
            """INSERT INTO parties (name, city, phone, ntn, stn, address,
               credit_limit, opening_balance, party_type, is_gl, brokerage_type, brokerage_rate, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,0,?,?,?)""",
            (request.form.get("name", "").strip(), request.form.get("city", "").strip(),
             request.form.get("phone", "").strip(), request.form.get("ntn", "").strip(),
             request.form.get("stn", "").strip(), request.form.get("address", "").strip(),
             float(request.form.get("credit_limit") or 0), float(request.form.get("opening_balance") or 0),
             party_type, brokerage_type, brokerage_rate, db.now_iso()),
        )
        conn.commit()
        conn.close()
        flash("Party added.", "success")
        return redirect(url_for("parties"))

    conn = db.get_connection()
    cur = conn.cursor()
    search_q = request.args.get("q", "").strip()
    query = "SELECT id, name, city, phone, party_type FROM parties WHERE is_gl = 0"
    params = []
    if search_q:
        query += " AND (name LIKE ? OR city LIKE ? OR phone LIKE ?)"
        like = f"%{search_q}%"
        params += [like, like, like]
    query += " ORDER BY name"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    parties_list = []
    for pid, name, city, phone, ptype in rows:
        balance = db.get_party_balance(pid)
        parties_list.append({
            "id": pid, "name": name, "city": city, "phone": phone, "party_type": ptype,
            "balance": abs(balance), "status": "Receivable" if balance > 0 else ("Payable" if balance < 0 else "Settled"),
        })
    return render_template("app/parties.html", parties=parties_list, search_q=search_q)


@app.route("/parties/<int:party_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def edit_party(party_id):
    conn = db.get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        party_type = request.form.get("party_type", "Customer")
        brokerage_type = request.form.get("brokerage_type") if party_type == "Broker" else None
        brokerage_rate = float(request.form.get("brokerage_rate") or 0) if party_type == "Broker" else None
        cur.execute(
            """UPDATE parties SET name=?, city=?, phone=?, ntn=?, stn=?, address=?,
               credit_limit=?, opening_balance=?, party_type=?, brokerage_type=?, brokerage_rate=?
               WHERE id=?""",
            (request.form.get("name", "").strip(), request.form.get("city", "").strip(),
             request.form.get("phone", "").strip(), request.form.get("ntn", "").strip(),
             request.form.get("stn", "").strip(), request.form.get("address", "").strip(),
             float(request.form.get("credit_limit") or 0), float(request.form.get("opening_balance") or 0),
             party_type, brokerage_type, brokerage_rate, party_id),
        )
        conn.commit()
        conn.close()
        flash("Party updated.", "success")
        return redirect(url_for("parties"))

    cur.execute("SELECT id, name, city, phone, ntn, stn, address, credit_limit, opening_balance, "
                "party_type, brokerage_type, brokerage_rate FROM parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        flash("Party not found.", "error")
        return redirect(url_for("parties"))
    cols = ["id", "name", "city", "phone", "ntn", "stn", "address", "credit_limit",
            "opening_balance", "party_type", "brokerage_type", "brokerage_rate"]
    party = dict(zip(cols, row))

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM opening_entries WHERE party_id = ?", (party_id,))
    opening_count, opening_total = cur.fetchone()
    conn.close()

    return render_template("app/edit_party.html", party=party,
                            opening_count=opening_count, opening_total=opening_total)


@app.route("/parties/<int:party_id>/delete", methods=["POST"])
@delete_permission_required
def delete_party(party_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE party_id = ?", (party_id,))
    if cur.fetchone()[0] > 0:
        conn.close()
        flash("Can't delete a party with transactions recorded against it.", "error")
        return redirect(url_for("parties"))
    cur.execute("SELECT COUNT(*) FROM opening_entries WHERE party_id = ?", (party_id,))
    if cur.fetchone()[0] > 0:
        conn.close()
        flash("Can't delete a party with imported outstanding invoices recorded against it. "
              "Settle or remove those first if you no longer need them.", "error")
        return redirect(url_for("parties"))
    cur.execute("DELETE FROM parties WHERE id = ?", (party_id,))
    conn.commit()
    conn.close()
    flash("Party deleted.", "success")
    return redirect(url_for("parties"))


@app.route("/parties/<int:party_id>/clear-opening-entries", methods=["POST"])
@delete_permission_required
def clear_opening_entries(party_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Party not found.", "error")
        return redirect(url_for("parties"))
    cur.execute("DELETE FROM opening_entries WHERE party_id = ?", (party_id,))
    removed = cur.rowcount
    conn.commit()
    conn.close()
    flash(f"Removed {removed} imported outstanding invoice{'s' if removed != 1 else ''} for '{row[0]}'. "
          f"You can now delete this party if you still want to, or re-import corrected data.", "success")
    return redirect(url_for("edit_party", party_id=party_id))


# --- Quality / Items ---
@app.route("/quality", methods=["GET", "POST"])
@company_required
def quality():
    if request.method == "POST":
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO quality (name, city_area, sale_rate, opening_balance, created_at) "
            "VALUES (?,?,?,?,?)",
            (request.form.get("name", "").strip(), request.form.get("city_area", "").strip(),
             float(request.form.get("sale_rate") or 0),
             float(request.form.get("opening_balance") or 0), db.now_iso()),
        )
        conn.commit()
        conn.close()
        flash("Item added.", "success")
        return redirect(url_for("quality"))

    conn = db.get_connection()
    cur = conn.cursor()
    search_q = request.args.get("q", "").strip()
    query = "SELECT id, name, city_area, sale_rate FROM quality"
    params = []
    if search_q:
        query += " WHERE name LIKE ? OR city_area LIKE ?"
        like = f"%{search_q}%"
        params += [like, like]
    query += " ORDER BY name"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    items = []
    for qid, name, area, srate in rows:
        items.append({"id": qid, "name": name, "area": area,
                       "purchase_rate": db.get_weighted_avg_purchase_rate(qid),
                       "sale_rate": srate, "stock": db.get_stock_qty(qid)})
    return render_template("app/quality.html", items=items, search_q=search_q)


@app.route("/quality/quick-add", methods=["POST"])
@company_required
def quality_quick_add():
    """Adds a new item without leaving whatever entry form the user is
    on (Purchase & Sale, Bookings) - called via JS, returns JSON so the
    new item can be added straight into that page's dropdown, already
    selected, with nothing else on the form lost."""
    name = request.form.get("name", "").strip()
    if not name:
        return {"ok": False, "error": "Name is required."}, 400

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE LOWER(name) = LOWER(?)", (name,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return {"ok": False, "error": f"An item named '{name}' already exists."}, 400

    cur.execute(
        "INSERT INTO quality (name, city_area, sale_rate, opening_balance, created_at) VALUES (?,?,?,?,?)",
        (name, request.form.get("city_area", "").strip(),
         float(request.form.get("sale_rate") or 0), float(request.form.get("opening_balance") or 0),
         db.now_iso()),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "id": new_id, "name": name}


@app.route("/quality/<int:item_id>/delete", methods=["POST"])
@company_required
def delete_quality(item_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE quality_id = ?", (item_id,))
    if cur.fetchone()[0] > 0:
        conn.close()
        flash("Can't delete an item with transactions recorded against it.", "error")
        return redirect(url_for("quality"))
    cur.execute("DELETE FROM quality WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    flash("Item deleted.", "success")
    return redirect(url_for("quality"))


# --- Purchase & Sale entry ---
@app.route("/transactions", methods=["GET", "POST"])
@company_required
def transactions():
    conn = db.get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        voucher_type = request.form.get("voucher_type")
        party_id = int(request.form.get("party_id"))
        quality_id = int(request.form.get("quality_id"))
        qty = float(request.form.get("qty") or 0)
        rate = float(request.form.get("rate") or 0)
        amount = qty * rate
        signature_data = request.form.get("signature_data", "").strip() or None
        broker_party_id = request.form.get("broker_party_id") or None
        broker_party_id = int(broker_party_id) if broker_party_id else None
        broker_name = ""
        if broker_party_id:
            cur.execute("SELECT name FROM parties WHERE id = ?", (broker_party_id,))
            row = cur.fetchone()
            broker_name = row[0] if row else ""
        voucher_no = db.get_next_voucher_no(voucher_type, conn)
        cur.execute(
            """INSERT INTO transactions
               (date, voucher_type, voucher_no, do_no, party_id, broker, broker_party_id, quality_id,
                qty, rate, amount, cash_or_cheque, cheque_no, description, credit_days, signature_data, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request.form.get("date"), voucher_type, voucher_no, request.form.get("do_no", "").strip(),
             party_id, broker_name, broker_party_id, quality_id, qty, rate, amount,
             request.form.get("mode", "Cash"), request.form.get("cheque_no", "").strip(),
             request.form.get("description", "").strip(), int(request.form.get("credit_days") or 0),
             signature_data, db.now_iso()),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        voucher_str = db.format_voucher_no(voucher_type, voucher_no)
        flash(f"{voucher_type.title()} saved as {voucher_str}.", "success")
        # Back to a fresh entry form, not straight to the PDF - printing
        # is now an explicit choice from the banner/recent list, not
        # something that happens automatically on every save.
        return redirect(url_for("transactions", saved=new_id))

    cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM parties WHERE party_type = 'Broker' ORDER BY name")
    brokers = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    cur.execute("SELECT id, name, sale_rate FROM quality ORDER BY name")
    items = [{"id": r[0], "name": r[1], "sale_rate": r[2]} for r in cur.fetchall()]

    # Search by invoice/voucher number (e.g. "INV-000005", "5", "000005")
    # or D.O. number - matches across ALL Sale/Purchase entries, not just
    # the usual recent-40, so an old entry can always be found again.
    search_q = request.args.get("q", "").strip()
    if search_q:
        digits = re.sub(r"\D", "", search_q)
        query = """SELECT t.id, t.voucher_no, t.date, t.voucher_type, t.do_no, p.name, q.name, t.qty, t.rate, t.amount
                   FROM transactions t LEFT JOIN parties p ON p.id = t.party_id LEFT JOIN quality q ON q.id = t.quality_id
                   WHERE t.voucher_type IN ('SALE','PURCHASE')
                     AND (t.do_no LIKE ? OR (? != '' AND CAST(t.voucher_no AS TEXT) LIKE ?))
                   ORDER BY t.id DESC LIMIT 200"""
        cur.execute(query, (f"%{search_q}%", digits, f"%{digits}%" if digits else "%\x00no-match\x00%"))
    else:
        cur.execute(
            """SELECT t.id, t.voucher_no, t.date, t.voucher_type, t.do_no, p.name, q.name, t.qty, t.rate, t.amount
               FROM transactions t LEFT JOIN parties p ON p.id = t.party_id LEFT JOIN quality q ON q.id = t.quality_id
               WHERE t.voucher_type IN ('SALE','PURCHASE') ORDER BY t.id DESC LIMIT 40"""
        )
    recent = []
    for tid, vno, tdate, vtype, do_no, pname, iname, qty, rate, amount in cur.fetchall():
        recent.append({"id": tid, "voucher": db.format_voucher_no(vtype, vno), "date": tdate, "type": vtype,
                        "do_no": do_no, "party": pname, "item": iname, "qty": qty, "rate": rate, "amount": amount})
    conn.close()

    saved_id = request.args.get("saved", type=int)
    saved_voucher = None
    if saved_id:
        saved_voucher = next((r for r in recent if r["id"] == saved_id), None)
        if not saved_voucher:
            # the saved entry might not be in a filtered search's results -
            # look it up separately so the banner still shows correctly
            conn2 = db.get_connection()
            cur2 = conn2.cursor()
            cur2.execute("SELECT voucher_type, voucher_no FROM transactions WHERE id = ?", (saved_id,))
            row = cur2.fetchone()
            conn2.close()
            if row:
                saved_voucher = {"id": saved_id, "voucher": db.format_voucher_no(row[0], row[1])}

    suggested_do_sale = db.suggest_next_do_no("SALE")
    suggested_do_purchase = db.suggest_next_do_no("PURCHASE")
    return render_template("app/transactions.html", parties=parties_list, items=items, recent=recent,
                            today=date.today().isoformat(), suggested_do_sale=suggested_do_sale,
                            suggested_do_purchase=suggested_do_purchase, saved_voucher=saved_voucher,
                            search_q=search_q, brokers=brokers)


# --- Purchase & Sale Booking (forward contract, delivered later) ---
@app.route("/bookings", methods=["GET", "POST"])
@company_required
def bookings():
    if request.method == "POST":
        try:
            qty = float(request.form.get("qty") or 0)
            rate = float(request.form.get("rate") or 0)
            if qty <= 0 or rate <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity and rate must be positive numbers.", "error")
            return redirect(url_for("bookings"))

        db.create_booking(
            request.form.get("voucher_type"), request.form.get("date"),
            int(request.form.get("party_id")), int(request.form.get("quality_id")),
            qty, rate, request.form.get("delivery_terms", "").strip(),
        )
        flash("Booking created.", "success")
        return redirect(url_for("bookings"))

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT id, name FROM quality ORDER BY name")
    items = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()

    status_filter = request.args.get("status", "Open")
    all_bookings = db.list_bookings(status_filter if status_filter != "All" else None)

    search_q = request.args.get("q", "").strip()
    if search_q:
        q_lower = search_q.lower()
        all_bookings = [
            b for b in all_bookings
            if q_lower in b["booking_display"].lower() or q_lower in (b["party_name"] or "").lower()
            or q_lower in (b["item_name"] or "").lower() or q_lower in (b["delivery_terms"] or "").lower()
        ]

    saved_id = request.args.get("saved", type=int)
    saved_voucher = None
    if saved_id:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT voucher_type, voucher_no FROM transactions WHERE id = ?", (saved_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            saved_voucher = {"id": saved_id, "voucher": db.format_voucher_no(row[0], row[1])}

    return render_template("app/bookings.html", parties=parties_list, items=items, bookings=all_bookings,
                            today=date.today().isoformat(), status_filter=status_filter,
                            saved_voucher=saved_voucher, search_q=search_q)


@app.route("/bookings/<int:booking_id>")
@company_required
def booking_detail(booking_id):
    booking = db.get_booking(booking_id)
    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for("bookings"))
    deliveries = db.get_booking_deliveries(booking_id)
    return render_template("app/booking_detail.html", booking=booking, deliveries=deliveries)


@app.route("/bookings/<int:booking_id>/deliver", methods=["POST"])
@company_required
def deliver_booking(booking_id):
    try:
        deliver_qty = float(request.form.get("deliver_qty") or 0)
        new_id = db.deliver_booking(
            booking_id, deliver_qty,
            do_no=request.form.get("do_no", "").strip(),
            credit_days=int(request.form.get("credit_days") or 0),
            mode=request.form.get("mode", "Cash"),
            cheque_no=request.form.get("cheque_no", "").strip(),
            delivery_date=request.form.get("delivery_date") or None,
        )
        flash("Delivery recorded and posted to the ledger.", "success")
        return redirect(url_for("bookings", saved=new_id, status=request.args.get("status", "Open")))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("bookings"))


@app.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@company_required
def cancel_booking(booking_id):
    if db.cancel_booking(booking_id):
        flash("Booking cancelled.", "success")
    else:
        flash("Can't cancel a booking that already has deliveries against it.", "error")
    return redirect(url_for("bookings"))


# --- Receipt & Payment entry ---
@app.route("/recovery", methods=["GET", "POST"])
@company_required
def recovery():
    conn = db.get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        voucher_type = request.form.get("voucher_type")
        party_id = int(request.form.get("party_id"))
        mode = request.form.get("mode", "Cash")

        cheque_dates = request.form.getlist("cheque_date[]")
        cheque_banks = request.form.getlist("cheque_bank[]")
        cheque_nos = request.form.getlist("cheque_no[]")
        cheque_amounts = request.form.getlist("cheque_amount[]")
        cheque_rows = []
        if mode == "Cheque":
            for d, b, n, a in zip(cheque_dates, cheque_banks, cheque_nos, cheque_amounts):
                try:
                    amt = float(a)
                except (TypeError, ValueError):
                    continue
                if amt > 0:
                    cheque_rows.append({"date": d, "bank": b, "cheque_no": n, "amount": amt})

        if mode == "Cheque" and cheque_rows:
            # cheques are always written for a positive amount - the
            # direction (Receipt vs Payment) is the explicit choice
            # made in the Type dropdown for this mode
            amount = sum(r["amount"] for r in cheque_rows)
            first_cheque_no = cheque_rows[0]["cheque_no"]
        else:
            # Cash mode: the sign of the amount IS the direction - type
            # positive for a Receipt, negative for a Payment, and the
            # Type dropdown is ignored/overridden here, matching what
            # was actually typed rather than what happened to be
            # selected in the dropdown
            raw_amount = float(request.form.get("amount") or 0)
            if raw_amount == 0:
                flash("Amount can't be zero.", "error")
                conn.close()
                return redirect(url_for("recovery"))
            voucher_type = "RECEIPT" if raw_amount > 0 else "PAYMENT"
            amount = abs(raw_amount)
            first_cheque_no = request.form.get("cheque_no", "").strip()

        if amount <= 0:
            flash("Amount must not be zero.", "error")
            conn.close()
            return redirect(url_for("recovery"))

        voucher_no = db.get_next_voucher_no(voucher_type, conn)
        cur.execute(
            """INSERT INTO transactions
               (date, voucher_type, voucher_no, do_no, party_id, broker, quality_id, qty, rate, amount,
                cash_or_cheque, cheque_no, description, credit_days, created_at)
               VALUES (?,?,?,NULL,?,NULL,NULL,NULL,NULL,?,?,?,?,NULL,?)""",
            (request.form.get("date"), voucher_type, voucher_no, party_id, amount,
             mode, first_cheque_no,
             request.form.get("description", "").strip(), db.now_iso()),
        )
        new_id = cur.lastrowid
        if mode == "Cheque" and cheque_rows:
            db.save_cheques(new_id, cheque_rows, conn)
        conn.commit()
        conn.close()
        voucher_str = db.format_voucher_no(voucher_type, voucher_no)
        flash(f"{voucher_type.title()} saved as {voucher_str}.", "success")
        return redirect(url_for("recovery", saved=new_id))

    cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]

    search_q = request.args.get("q", "").strip()
    if search_q:
        digits = re.sub(r"\D", "", search_q)
        query = """SELECT t.id, t.voucher_no, t.date, t.voucher_type, p.name, t.cash_or_cheque, t.amount, t.description
                   FROM transactions t LEFT JOIN parties p ON p.id = t.party_id
                   WHERE t.voucher_type IN ('RECEIPT','PAYMENT')
                     AND (p.name LIKE ? OR t.description LIKE ? OR (? != '' AND CAST(t.voucher_no AS TEXT) LIKE ?))
                   ORDER BY t.id DESC LIMIT 200"""
        cur.execute(query, (f"%{search_q}%", f"%{search_q}%", digits, f"%{digits}%" if digits else "%\x00no-match%"))
    else:
        cur.execute(
            """SELECT t.id, t.voucher_no, t.date, t.voucher_type, p.name, t.cash_or_cheque, t.amount, t.description
               FROM transactions t LEFT JOIN parties p ON p.id = t.party_id
               WHERE t.voucher_type IN ('RECEIPT','PAYMENT') ORDER BY t.id DESC LIMIT 40"""
        )
    recent = []
    for tid, vno, tdate, vtype, pname, mode, amount, desc in cur.fetchall():
        n_cheques = len(db.get_cheques_for_transaction(tid))
        mode_display = f"{n_cheques} cheque(s)" if n_cheques else (mode or "Cash")
        recent.append({"id": tid, "voucher": db.format_voucher_no(vtype, vno), "date": tdate, "type": vtype,
                        "party": pname, "mode": mode_display, "amount": amount, "description": desc})
    conn.close()

    saved_id = request.args.get("saved", type=int)
    saved_voucher = next((r for r in recent if r["id"] == saved_id), None) if saved_id else None
    return render_template("app/recovery.html", parties=parties_list, recent=recent,
                            today=date.today().isoformat(), saved_voucher=saved_voucher, search_q=search_q)


# --- Capital & Expense entry ---
@app.route("/capital-expense", methods=["GET", "POST"])
@company_required
def capital_expense():
    conn = db.get_connection()
    cur = conn.cursor()

    if request.method == "POST":
        kind = request.form.get("kind")  # 'expense' or 'capital'
        amount = float(request.form.get("amount") or 0)
        if kind == "expense":
            category = request.form.get("category", "Home")
            gl_name = {"Home": db.GL_HOME_EXPENSE, "Office": db.GL_OFFICE_EXPENSE,
                       "Zakat": db.GL_ZAKAT}.get(category, db.GL_HOME_EXPENSE)
            party_id = db.get_gl_party_id(gl_name, conn)
            voucher_type = "EXPENSE"
        else:
            direction = request.form.get("direction", "CAPITAL_IN")
            party_id = db.get_gl_party_id(db.GL_CAPITAL, conn)
            voucher_type = direction

        voucher_no = db.get_next_voucher_no(voucher_type, conn)
        cur.execute(
            """INSERT INTO transactions
               (date, voucher_type, voucher_no, party_id, amount, description, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (request.form.get("date"), voucher_type, voucher_no, party_id, amount,
             request.form.get("description", "").strip(), db.now_iso()),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash(f"{voucher_type.replace('_', ' ').title()} saved.", "success")
        return redirect(url_for("capital_expense", saved=new_id))

    home_id = db.get_gl_party_id(db.GL_HOME_EXPENSE, conn)
    office_id = db.get_gl_party_id(db.GL_OFFICE_EXPENSE, conn)
    zakat_id = db.get_gl_party_id(db.GL_ZAKAT, conn)
    cur.execute(
        """SELECT t.id, t.voucher_no, t.date, t.party_id, t.amount, t.description FROM transactions t
           WHERE t.voucher_type = 'EXPENSE' AND t.party_id IN (?, ?, ?) ORDER BY t.id DESC LIMIT 20""",
        (home_id, office_id, zakat_id),
    )
    category_by_pid = {home_id: "Home", office_id: "Office", zakat_id: "Zakat"}
    expenses = []
    for tid, vno, tdate, pid, amount, desc in cur.fetchall():
        expenses.append({"id": tid, "voucher": db.format_voucher_no("EXPENSE", vno), "date": tdate,
                          "category": category_by_pid.get(pid, "Home"), "amount": amount, "description": desc})
    conn.close()

    capital = db.get_capital_summary()
    capital_entries = [
        {"id": r[0], "voucher": db.format_voucher_no(r[3], r[1]), "date": r[2],
         "direction": "In" if r[3] == "CAPITAL_IN" else "Out", "amount": r[4], "description": r[5]}
        for r in capital["entries"]
    ]

    saved_id = request.args.get("saved", type=int)
    saved_voucher = None
    if saved_id:
        saved_voucher = next((e for e in expenses if e["id"] == saved_id), None) or \
            next((c for c in capital_entries if c["id"] == saved_id), None)

    return render_template("app/capital_expense.html", expenses=expenses, capital=capital,
                            capital_entries=capital_entries, today=date.today().isoformat(),
                            saved_voucher=saved_voucher)


# --- print/delete a transaction ---
@app.route("/transaction/<int:transaction_id>/print")
@company_required
def print_voucher(transaction_id):
    if voucher_print is None:
        flash("PDF generation isn't available.", "error")
        return redirect(url_for("dashboard"))
    try:
        path = voucher_print.generate_voucher_pdf(transaction_id)
        return send_file(path, as_attachment=False)
    except Exception as exc:
        flash(f"Couldn't generate PDF: {exc}", "error")
        return redirect(url_for("dashboard"))


@app.route("/transaction/<int:transaction_id>/edit", methods=["GET", "POST"])
@edit_permission_required
def edit_transaction(transaction_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    col_names = [d[0] for d in cur.description]
    row = cur.fetchone()
    if not row:
        conn.close()
        flash("Entry not found.", "error")
        return redirect(url_for("dashboard"))
    txn = dict(zip(col_names, row))
    v_type = txn["voucher_type"]

    if request.method == "POST":
        if v_type in ("SALE", "PURCHASE"):
            qty = float(request.form.get("qty") or 0)
            rate = float(request.form.get("rate") or 0)
            amount = qty * rate
            cur.execute(
                """UPDATE transactions SET date=?, do_no=?, party_id=?, broker=?, quality_id=?,
                   qty=?, rate=?, amount=?, cash_or_cheque=?, cheque_no=?, description=?, credit_days=?
                   WHERE id=?""",
                (request.form.get("date"), request.form.get("do_no", "").strip(),
                 int(request.form.get("party_id")), request.form.get("broker", "").strip(),
                 int(request.form.get("quality_id")), qty, rate, amount,
                 request.form.get("mode", "Cash"), request.form.get("cheque_no", "").strip(),
                 request.form.get("description", "").strip(), int(request.form.get("credit_days") or 0),
                 transaction_id),
            )
        elif v_type in ("RECEIPT", "PAYMENT"):
            amount = float(request.form.get("amount") or 0)
            cur.execute(
                """UPDATE transactions SET date=?, party_id=?, amount=?, cash_or_cheque=?,
                   cheque_no=?, description=? WHERE id=?""",
                (request.form.get("date"), int(request.form.get("party_id")), amount,
                 request.form.get("mode", "Cash"), request.form.get("cheque_no", "").strip(),
                 request.form.get("description", "").strip(), transaction_id),
            )
        else:  # EXPENSE, CAPITAL_IN, CAPITAL_OUT
            amount = float(request.form.get("amount") or 0)
            cur.execute(
                "UPDATE transactions SET date=?, amount=?, description=? WHERE id=?",
                (request.form.get("date"), amount, request.form.get("description", "").strip(), transaction_id),
            )
        conn.commit()
        conn.close()
        flash("Entry updated.", "success")
        return redirect(request.form.get("return_to") or url_for("dashboard"))

    parties_list, items = [], []
    if v_type in ("SALE", "PURCHASE", "RECEIPT", "PAYMENT"):
        cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
        parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]
    if v_type in ("SALE", "PURCHASE"):
        cur.execute("SELECT id, name FROM quality ORDER BY name")
        items = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()

    return render_template("app/edit_transaction.html", txn=txn, v_type=v_type,
                            parties=parties_list, items=items,
                            return_to=request.args.get("return_to", ""))


@app.route("/transaction/<int:transaction_id>/delete", methods=["POST"])
@delete_permission_required
def delete_transaction(transaction_id):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    flash("Entry deleted.", "success")
    return redirect(request.referrer or url_for("dashboard"))


# --- Reports ---
@app.route("/reports/receivable")
@company_required
def report_receivable():
    as_of = request.args.get("as_of") or date.today().isoformat()
    rows = db.get_receivable_aging(as_of)
    by_party = {}
    order = []
    for r in rows:
        if r["party_id"] not in by_party:
            by_party[r["party_id"]] = []
            order.append(r["party_id"])
        by_party[r["party_id"]].append(r)
    groups = [{"party_name": by_party[pid][0]["party_name"], "rows": by_party[pid],
               "subtotal": sum(x["outstanding"] for x in by_party[pid])} for pid in order]
    total = sum(g["subtotal"] for g in groups)
    overdue = sum(r["outstanding"] for r in rows if r["is_overdue"])
    return render_template("app/receivable.html", groups=groups, total=total, overdue=overdue, as_of=as_of)


@app.route("/reports/payable")
@company_required
def report_payable():
    as_of = request.args.get("as_of") or date.today().isoformat()
    rows = db.get_payable_aging(as_of)
    by_party = {}
    order = []
    for r in rows:
        if r["party_id"] not in by_party:
            by_party[r["party_id"]] = []
            order.append(r["party_id"])
        by_party[r["party_id"]].append(r)
    groups = [{"party_name": by_party[pid][0]["party_name"], "rows": by_party[pid],
               "subtotal": sum(x["outstanding"] for x in by_party[pid])} for pid in order]
    total = sum(g["subtotal"] for g in groups)
    overdue = sum(r["outstanding"] for r in rows if r["is_overdue"])
    return render_template("app/payable.html", groups=groups, total=total, overdue=overdue, as_of=as_of)


@app.route("/reports/cashbook")
@company_required
def report_cashbook():
    date_from = request.args.get("from") or date.today().replace(day=1).isoformat()
    date_to = request.args.get("to") or date.today().isoformat()
    t = db.get_cash_taccount(date_from, date_to)
    return render_template("app/cashbook.html", t=t, date_from=date_from, date_to=date_to)


@app.route("/reports/profit")
@company_required
def report_profit():
    date_from = request.args.get("from") or date.today().replace(month=1, day=1).isoformat()
    date_to = request.args.get("to") or date.today().isoformat()
    profit = db.get_profit_summary(date_from, date_to)
    capital = db.get_capital_summary()
    return render_template("app/profit.html", profit=profit, capital=capital, date_from=date_from, date_to=date_to)


@app.route("/reports/brokerage")
@company_required
def report_brokerage():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM parties WHERE party_type = 'Broker' ORDER BY name")
    brokers = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()

    broker_filter = request.args.get("broker_id", type=int)
    search_q = request.args.get("q", "").strip()
    rows = db.get_brokerage_report(broker_party_id=broker_filter)

    if search_q:
        q_lower = search_q.lower()
        rows = [r for r in rows if q_lower in (r["broker_name"] or "").lower()
                or q_lower in (r["party_name"] or "").lower()
                or q_lower in (r["do_no"] or "").lower()
                or q_lower in r["voucher_display"].lower()]

    by_broker = {}
    order = []
    for r in rows:
        key = r["broker_party_id"]
        if key not in by_broker:
            by_broker[key] = []
            order.append(key)
        by_broker[key].append(r)
    groups = [{"broker_name": by_broker[k][0]["broker_name"], "rows": by_broker[k],
               "subtotal": sum(x["brokerage"] for x in by_broker[k])} for k in order]
    total = sum(g["subtotal"] for g in groups)

    return render_template("app/brokerage.html", groups=groups, total=total, brokers=brokers,
                            broker_filter=broker_filter, search_q=search_q)


@app.route("/contra", methods=["GET", "POST"])
@company_required
def contra():
    if request.method == "POST":
        try:
            legs = []
            party_ids = request.form.getlist("party_id[]")
            directions = request.form.getlist("direction[]")
            amounts = request.form.getlist("amount[]")
            for pid, direction, amt in zip(party_ids, directions, amounts):
                if not pid or not amt:
                    continue
                legs.append({"party_id": int(pid), "direction": direction, "amount": float(amt)})
            voucher_no = db.create_contra_entry(request.form.get("date"), legs,
                                                 request.form.get("description", "").strip())
            flash(f"Contra entry saved as {db.format_voucher_no('CONTRA_DR', voucher_no)}.", "success")
        except ValueError as exc:
            flash(str(exc), "error")
        return redirect(url_for("contra"))

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]
    conn.close()

    entries = db.list_contra_entries()
    return render_template("app/contra.html", parties=parties_list, entries=entries,
                            today=date.today().isoformat())


@app.route("/reports/trial-balance")
@company_required
def report_trial_balance():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, opening_balance FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_rows = cur.fetchall()
    conn.close()

    rows = []
    total_debit = total_credit = 0.0
    for party_id, name, opening_balance in parties_rows:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT voucher_type, SUM(amount) FROM transactions WHERE party_id = ? GROUP BY voucher_type",
                     (party_id,))
        sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
        conn.close()
        opening_balance = opening_balance or 0.0
        debit = (opening_balance if opening_balance > 0 else 0) + sums.get("SALE", 0) + sums.get("PAYMENT", 0)
        credit = (abs(opening_balance) if opening_balance < 0 else 0) + sums.get("PURCHASE", 0) + sums.get("RECEIPT", 0)
        balance = opening_balance + sums.get("SALE", 0) + sums.get("PAYMENT", 0) \
            - sums.get("PURCHASE", 0) - sums.get("RECEIPT", 0)
        if debit == 0 and credit == 0 and opening_balance == 0:
            continue
        total_debit += debit
        total_credit += credit
        rows.append({"name": name, "debit": debit, "credit": credit, "balance": balance})

    return render_template("app/trial_balance.html", rows=rows, total_debit=total_debit, total_credit=total_credit)


@app.route("/reports/stock")
@company_required
def report_stock():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, city_area, sale_rate, opening_balance FROM quality ORDER BY name")
    items = []
    for qid, name, area, srate, opening in cur.fetchall():
        items.append({"name": name, "area": area, "sale_rate": srate,
                       "purchase_rate": db.get_weighted_avg_purchase_rate(qid),
                       "stock": db.get_stock_qty(qid)})
    conn.close()
    return render_template("app/stock.html", items=items)


@app.route("/reports/quality-ledger")
@company_required
def report_quality_ledger():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM quality ORDER BY name")
    items_list = [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
    conn.close()

    quality_id = request.args.get("quality_id", type=int)
    ledger = db.get_quality_ledger(quality_id) if quality_id else None
    if quality_id and not ledger:
        flash("Item not found.", "error")

    return render_template("app/quality_ledger.html", items=items_list, quality_id=quality_id, ledger=ledger)


@app.route("/reports/ledger")
@company_required
def report_ledger():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties_list = [{"id": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]

    party_id = request.args.get("party_id", type=int)
    rows = []
    party = None
    closing_balance = 0.0
    total_debit = total_credit = 0.0

    if party_id:
        cur.execute("SELECT name, city, phone, ntn, stn, opening_balance FROM parties WHERE id = ?", (party_id,))
        prow = cur.fetchone()
        if prow:
            party = {"name": prow[0], "city": prow[1], "phone": prow[2], "ntn": prow[3],
                     "stn": prow[4], "opening_balance": prow[5] or 0.0}

            # detailed imported opening entries (if any) replace the
            # single lump-sum opening_balance line, same logic as the
            # Receivable/Payable Ledger - each shows as its own row
            # with its real date, reference, and item, sorted in with
            # the real transactions rather than one opaque total
            cur.execute(
                "SELECT date, entry_type, reference, item_name, qty, amount FROM opening_entries "
                "WHERE party_id = ? ORDER BY date, id", (party_id,)
            )
            opening_rows = cur.fetchall()

            cur.execute(
                """SELECT t.date, t.voucher_type, t.voucher_no, t.do_no, q.name, t.qty, t.amount, t.description
                   FROM transactions t LEFT JOIN quality q ON q.id = t.quality_id
                   WHERE t.party_id = ? ORDER BY t.date, t.id""",
                (party_id,),
            )
            txn_rows = cur.fetchall()

            balance = 0.0 if opening_rows else party["opening_balance"]

            combined = []
            for oe_date, entry_type, reference, item_name, qty, amount in opening_rows:
                combined.append({"date": oe_date, "sort_key": (oe_date, -1), "kind": "opening",
                                  "entry_type": entry_type, "reference": reference,
                                  "item_name": item_name, "qty": qty, "amount": amount or 0.0})
            for i, (t_date, v_type, voucher_no, do_no, item_name, qty, amount, desc) in enumerate(txn_rows):
                combined.append({"date": t_date, "sort_key": (t_date, i), "kind": "txn",
                                  "voucher_type": v_type, "voucher_no": voucher_no, "do_no": do_no,
                                  "item_name": item_name, "qty": qty, "amount": amount, "description": desc})
            combined.sort(key=lambda r: r["sort_key"])

            for entry in combined:
                if entry["kind"] == "opening":
                    amount = entry["amount"]
                    ref = entry["reference"] or "Opening"
                    v_type_display = "Opening (Receivable)" if entry["entry_type"] == "receivable" else "Opening (Payable)"
                    if entry["entry_type"] == "receivable":
                        debit, credit = amount, 0
                        balance += amount
                        total_debit += amount
                    else:
                        debit, credit = 0, amount
                        balance -= amount
                        total_credit += amount
                    rows.append({"date": entry["date"], "ref": ref, "type": v_type_display, "do_no": ref,
                                 "item": entry["item_name"], "qty": entry["qty"], "debit": debit, "credit": credit,
                                 "balance": balance, "description": ""})
                else:
                    amount = entry["amount"] or 0
                    ref = db.format_voucher_no(entry["voucher_type"], entry["voucher_no"])
                    if entry["voucher_type"] in ("SALE", "PAYMENT"):
                        debit, credit = amount, 0
                        balance += amount
                        total_debit += amount
                    else:
                        debit, credit = 0, amount
                        balance -= amount
                        total_credit += amount
                    rows.append({"date": entry["date"], "ref": ref, "type": entry["voucher_type"], "do_no": entry["do_no"],
                                 "item": entry["item_name"], "qty": entry["qty"], "debit": debit, "credit": credit,
                                 "balance": balance, "description": entry["description"]})
            closing_balance = balance
    conn.close()

    return render_template("app/ledger.html", parties=parties_list, party=party, party_id=party_id,
                            rows=rows, closing_balance=closing_balance,
                            total_debit=total_debit, total_credit=total_credit)


@app.route("/reports/pdf/<report_name>")
@company_required
def report_pdf(report_name):
    if pdf_export is None:
        flash("PDF generation isn't available.", "error")
        return redirect(url_for("dashboard"))
    try:
        if report_name == "receivable":
            path = pdf_export.generate_receivable_ledger_pdf(request.args.get("as_of"))
        elif report_name == "payable":
            path = pdf_export.generate_payable_ledger_pdf(request.args.get("as_of"))
        elif report_name == "ledger":
            party_id = request.args.get("party_id", type=int)
            if not party_id:
                flash("Select a party first.", "error")
                return redirect(url_for("report_ledger"))
            path = pdf_export.generate_party_ledger_pdf(party_id)
        elif report_name == "cashbook":
            path = pdf_export.generate_cash_book_pdf(request.args.get("from"), request.args.get("to"))
        elif report_name == "profit":
            path = pdf_export.generate_profit_report_pdf(request.args.get("from"), request.args.get("to"))
        elif report_name == "stock":
            path = pdf_export.generate_stock_report_pdf()
        elif report_name == "trial_balance":
            path = pdf_export.generate_trial_balance_pdf()
        else:
            flash("Unknown report.", "error")
            return redirect(url_for("dashboard"))
        return send_file(path, as_attachment=False)
    except Exception as exc:
        flash(f"Couldn't generate PDF: {exc}", "error")
        return redirect(url_for("dashboard"))


@app.route("/reports/excel/<report_name>")
@company_required
def report_excel(report_name):
    if excel_export is None:
        flash("Excel export isn't available.", "error")
        return redirect(url_for("dashboard"))
    try:
        if report_name == "receivable":
            path = excel_export.generate_receivable_excel(request.args.get("as_of"))
        elif report_name == "payable":
            path = excel_export.generate_payable_excel(request.args.get("as_of"))
        elif report_name == "ledger":
            party_id = request.args.get("party_id", type=int)
            if not party_id:
                flash("Select a party first.", "error")
                return redirect(url_for("report_ledger"))
            path = excel_export.generate_ledger_excel(party_id)
        elif report_name == "cashbook":
            date_from = request.args.get("from") or date.today().replace(day=1).isoformat()
            date_to = request.args.get("to") or date.today().isoformat()
            path = excel_export.generate_cashbook_excel(date_from, date_to)
        elif report_name == "profit":
            date_from = request.args.get("from") or date.today().replace(month=1, day=1).isoformat()
            date_to = request.args.get("to") or date.today().isoformat()
            path = excel_export.generate_profit_excel(date_from, date_to)
        elif report_name == "stock":
            path = excel_export.generate_stock_excel()
        elif report_name == "trial_balance":
            path = excel_export.generate_trial_balance_excel()
        elif report_name == "brokerage":
            path = excel_export.generate_brokerage_excel(request.args.get("broker_id", type=int))
        else:
            flash("Unknown report.", "error")
            return redirect(url_for("dashboard"))
        return send_file(path, as_attachment=True)
    except Exception as exc:
        flash(f"Couldn't generate Excel file: {exc}", "error")
        return redirect(url_for("dashboard"))


# --- Settings ---
# --- Team (company admins manage their own company's users) ---
@app.route("/team", methods=["GET", "POST"])
@company_required
def team():
    if g.user["role"] != "admin":
        flash("Only a company admin can manage team members.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "staff")
        if role not in ("staff", "admin"):
            role = "staff"
        if not username or not password:
            flash("Username and password are required.", "error")
        elif len(password) < MIN_PASSWORD_LENGTH:
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "error")
        else:
            user_id = master.create_user(g.company["id"], username, password, full_name, role, email)
            if user_id is None:
                flash(f"Username '{username}' is already taken.", "error")
            else:
                flash(f"User '{username}' added.", "success")
        return redirect(url_for("team"))

    users = master.list_users_for_company(g.company["id"])
    search_q = request.args.get("q", "").strip()
    if search_q:
        q_lower = search_q.lower()
        users = [u for u in users if q_lower in u["username"].lower() or q_lower in (u["full_name"] or "").lower()]
    return render_template("app/team.html", users=users, search_q=search_q)


@app.route("/team/<int:user_id>/delete", methods=["POST"])
@company_required
def team_delete_user(user_id):
    if g.user["role"] != "admin":
        flash("Only a company admin can manage team members.", "error")
        return redirect(url_for("dashboard"))
    target = master.get_user(user_id)
    # Security: only allow deleting users that belong to THIS company -
    # never let a company admin touch another company's accounts.
    if not target or target["company_id"] != g.company["id"]:
        flash("User not found.", "error")
        return redirect(url_for("team"))
    if target["id"] == g.user["id"]:
        flash("You can't remove your own account while signed in.", "error")
        return redirect(url_for("team"))
    master.delete_user(user_id)
    flash("User removed.", "success")
    return redirect(url_for("team"))


@app.route("/team/<int:user_id>/toggle-edit", methods=["POST"])
@company_admin_required
def team_toggle_edit(user_id):
    target = master.get_user(user_id)
    # Security: only allow granting/revoking edit rights for users that
    # belong to THIS company - never let a company admin touch another
    # company's accounts.
    if not target or target["company_id"] != g.company["id"]:
        flash("User not found.", "error")
        return redirect(url_for("team"))
    if target["role"] in ("admin", "super_admin"):
        flash("Admins already have full edit rights - nothing to change.", "error")
        return redirect(url_for("team"))
    master.set_can_edit(user_id, not target["can_edit"])
    flash(f"Edit rights {'granted to' if not target['can_edit'] else 'revoked from'} '{target['username']}'.", "success")
    return redirect(url_for("team"))


@app.route("/team/<int:user_id>/email", methods=["POST"])
@company_required
def team_set_email(user_id):
    if g.user["role"] != "admin" and g.user["id"] != user_id:
        flash("Only a company admin can update another user's email.", "error")
        return redirect(url_for("team"))
    target = master.get_user(user_id)
    if not target or target["company_id"] != g.company["id"]:
        flash("User not found.", "error")
        return redirect(url_for("team"))
    master.set_user_email(user_id, request.form.get("email", ""))
    flash(f"Email updated for '{target['username']}' — needed for them to use \"Forgot password?\".", "success")
    return redirect(url_for("team"))


@app.route("/settings", methods=["GET", "POST"])
@company_required
def company_settings():
    if request.method == "POST":
        settings.set_company_name(request.form.get("company_name", ""))
        settings.set_theme(request.form.get("theme", "Purple"))
        settings.set_warehouse_address(request.form.get("warehouse_address", ""))
        settings.set_notification_email(request.form.get("notification_email", ""))
        amount = float(request.form.get("opening_cash_balance") or 0)
        as_of = request.form.get("opening_cash_date") or None
        settings.set_opening_cash_balance(amount, as_of)

        logo_file = request.files.get("logo")
        if logo_file and logo_file.filename:
            ext = os.path.splitext(logo_file.filename)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".gif"):
                flash("Logo must be a PNG, JPG, or GIF image.", "error")
                return redirect(url_for("company_settings"))
            tenant_dir = os.path.dirname(db.get_active_db_path())
            filename = f"logo{ext}"
            logo_file.save(os.path.join(tenant_dir, filename))
            settings.set_logo_filename(filename)

        flash("Settings saved.", "success")
        return redirect(url_for("company_settings"))

    amount, as_of = settings.get_opening_cash_balance()
    logo_filename = settings.get_logo_filename()
    return render_template("app/settings.html", company_name=settings.get_company_name(),
                            theme=settings.get_theme(), themes=ui_theme.THEMES,
                            opening_cash_balance=amount, opening_cash_date=as_of or "",
                            warehouse_address=settings.get_warehouse_address(),
                            logo_filename=logo_filename,
                            notification_email=settings.get_notification_email())


@app.route("/logo/<filename>")
@company_required
def company_logo(filename):
    """filename always comes from settings.get_logo_filename() (this
    company's own "logo{ext}", written by company_settings() above) - but
    it still arrives here as raw user-controllable request input, so it's
    sanitized and containment-checked the same as any other user input
    that touches a filesystem path, not trusted just because it's usually
    well-formed. This previously used a <path:...> converter (which
    allows "/" in the value) with no sanitization, so a request like
    /logo/../other-company-slug/ultra_erp.db could escape this tenant's
    own directory and read any other company's database file, or the
    platform's master database - see the security audit that found this.
    """
    tenant_dir = os.path.abspath(os.path.dirname(db.get_active_db_path()))
    safe_name = secure_filename(filename)
    if not safe_name:
        abort(404)
    full_path = os.path.abspath(os.path.join(tenant_dir, safe_name))
    if os.path.commonpath([full_path, tenant_dir]) != tenant_dir or not os.path.isfile(full_path):
        abort(404)
    return send_file(full_path)


# --- Backup ---
@app.route("/backup")
@company_required
def backup():
    slug = g.company["slug"]
    src = master.tenant_db_path(slug)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(master.BACKUPS_DIR, slug)
    os.makedirs(backup_dir, exist_ok=True)
    zip_path = os.path.join(backup_dir, f"backup_{stamp}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src, arcname="ultra_erp.db")
    return send_file(zip_path, as_attachment=True, download_name=f"{slug}_backup_{stamp}.zip")


def _b2_bucket():
    return os.environ.get("B2_BUCKET")


def _run_rclone(args, timeout=60):
    """Runs rclone as a subprocess, using the same config already set up
    by deploy/setup_backups.sh. Returns (success, stdout_or_error)."""
    try:
        result = subprocess.run(
            ["rclone"] + args, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or "rclone command failed"
        return True, result.stdout
    except FileNotFoundError:
        return False, "rclone isn't installed on this server"
    except subprocess.TimeoutExpired:
        return False, "Timed out reaching cloud storage"
    except Exception as exc:
        return False, str(exc)


@app.route("/backup-history")
@company_admin_required
def backup_history():
    bucket = _b2_bucket()
    if not bucket:
        return render_template("app/backup_history.html", available=False, backups=[])

    slug = g.company["slug"]
    ok, output = _run_rclone(["lsjson", f"b2backup:{bucket}/{slug}/"])
    backups = []
    if ok:
        try:
            entries = json.loads(output)
            for e in entries:
                if e["Name"].endswith(".zip"):
                    backups.append({
                        "name": e["Name"],
                        "size_kb": round(e.get("Size", 0) / 1024, 1),
                        "modified": e.get("ModTime", "")[:19].replace("T", " "),
                    })
            backups.sort(key=lambda b: b["name"], reverse=True)
        except (json.JSONDecodeError, KeyError):
            ok = False
            output = "Could not read the backup list."

    return render_template("app/backup_history.html", available=True, backups=backups,
                            error=None if ok else output)


@app.route("/backup-history/restore", methods=["POST"])
@company_admin_required
def restore_backup():
    bucket = _b2_bucket()
    if not bucket:
        flash("Cloud backups aren't configured on this server yet.", "error")
        return redirect(url_for("backup_history"))

    filename = request.form.get("filename", "").strip()
    confirm_text = request.form.get("confirm_text", "").strip()
    if confirm_text != "RESTORE":
        flash('You must type RESTORE exactly to confirm - nothing was changed.', "error")
        return redirect(url_for("backup_history"))
    if not filename.endswith(".zip") or "/" in filename or ".." in filename:
        flash("Invalid backup file.", "error")
        return redirect(url_for("backup_history"))

    slug = g.company["slug"]
    live_db_path = master.tenant_db_path(slug)

    # 1. safety net: back up the CURRENT live data first, before touching
    # anything - so even a restore mistake can itself be undone
    safety_dir = tempfile.mkdtemp(prefix="pre_restore_")
    safety_zip = os.path.join(safety_dir, f"{slug}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
    try:
        with zipfile.ZipFile(safety_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(live_db_path, arcname="ultra_erp.db")
        ok, msg = _run_rclone(["copy", safety_zip, f"b2backup:{bucket}/{slug}/_pre_restore_safety/"])
        if not ok:
            flash(f"Could not create a safety backup before restoring - aborted, nothing was changed. ({msg})", "error")
            return redirect(url_for("backup_history"))
    except Exception as exc:
        flash(f"Could not create a safety backup before restoring - aborted, nothing was changed. ({exc})", "error")
        return redirect(url_for("backup_history"))

    # 2. download the requested backup
    download_dir = tempfile.mkdtemp(prefix="restore_")
    ok, msg = _run_rclone(["copy", f"b2backup:{bucket}/{slug}/{filename}", download_dir])
    if not ok:
        flash(f"Could not download that backup - nothing was changed. ({msg})", "error")
        return redirect(url_for("backup_history"))

    downloaded_zip = os.path.join(download_dir, filename)
    if not os.path.exists(downloaded_zip):
        flash("Downloaded backup file not found - nothing was changed.", "error")
        return redirect(url_for("backup_history"))

    # 3. extract and swap in the restored database
    try:
        extract_dir = tempfile.mkdtemp(prefix="extract_")
        with zipfile.ZipFile(downloaded_zip, "r") as zf:
            # This zip is always one this same app created (deploy/backup.sh
            # / the safety-backup above, both just zf.write(db, arcname=
            # "ultra_erp.db")), but extracting it is still one bad entry
            # name away from writing outside extract_dir ("zip slip") if
            # that ever isn't true - e.g. someone's B2 credentials leak and
            # an attacker plants a crafted zip in this path. Cheap to guard
            # against regardless of how likely it is today.
            extract_dir_abs = os.path.abspath(extract_dir)
            for member in zf.namelist():
                member_path = os.path.abspath(os.path.join(extract_dir_abs, member))
                if os.path.commonpath([member_path, extract_dir_abs]) != extract_dir_abs:
                    flash("That backup file looks corrupted or tampered with - nothing was changed.", "error")
                    return redirect(url_for("backup_history"))
            zf.extractall(extract_dir)
        restored_db = os.path.join(extract_dir, "ultra_erp.db")
        if not os.path.exists(restored_db):
            flash("That backup file looks corrupted or in an unexpected format - nothing was changed.", "error")
            return redirect(url_for("backup_history"))
        os.replace(restored_db, live_db_path)
    except Exception as exc:
        flash(f"Restore failed partway through ({exc}) - a safety backup of your data from just before "
              f"this attempt is saved in your cloud storage under _pre_restore_safety/, contact support if needed.", "error")
        return redirect(url_for("backup_history"))

    flash(f"Restored from {filename}. A safety copy of what was live just before this restore was saved "
          f"to your cloud backups under _pre_restore_safety/, in case you need to undo this.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    master.init_master_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
