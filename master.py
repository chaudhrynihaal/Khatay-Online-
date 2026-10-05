"""
master.py
----------
The platform-level database: one shared ultra_erp_master.db holding
the list of companies (tenants) and every user account (super-admins
and each company's staff). This is completely separate from each
company's own business data, which lives in its own SQLite file under
tenants/<slug>/ultra_erp.db (see db.py).
"""

import os
import re
import sqlite3
import secrets
from datetime import datetime, date, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DB_PATH = os.path.join(BASE_DIR, "ultra_erp_master.db")
TENANTS_DIR = os.path.join(BASE_DIR, "tenants")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")


def get_master_connection():
    """Same WAL + busy_timeout settings as db.get_connection() - see
    that function's docstring for why. The master database (companies/
    users) is shared across every request regardless of which tenant
    is active, so it's actually the most likely place to see
    concurrent-write conflicts once several people are using the app."""
    conn = sqlite3.connect(MASTER_DB_PATH, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 8000")
    return conn


def init_master_db():
    os.makedirs(TENANTS_DIR, exist_ok=True)
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            subscription_status TEXT NOT NULL DEFAULT 'trial',
            subscription_expiry TEXT,
            notes TEXT,
            created_at TEXT
        )
    """)
    conn.commit()

    # --- migration: business_type. Set the first time a company picks a
    # business off the "What do you deal in?" screen (see
    # app.py's business_choose()) - once set, login skips straight to
    # that business's dashboard instead of showing the picker every
    # time. NULL until then (or for companies from before this existed),
    # which is exactly what keeps the old show-the-picker behavior for
    # anyone who hasn't chosen yet. ---
    cur.execute("PRAGMA table_info(companies)")
    existing_company_cols = {row[1] for row in cur.fetchall()}
    if "business_type" not in existing_company_cols:
        cur.execute("ALTER TABLE companies ADD COLUMN business_type TEXT")
        conn.commit()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'staff',
            can_edit INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
    """)
    conn.commit()

    # --- migration: older master databases created before can_edit
    # existed. Staff default to 0 (view/create only, no edit/delete);
    # admins don't need the flag since they always have full rights
    # regardless of it (checked separately in app.py). ---
    cur.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "can_edit" not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN can_edit INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    # --- migration: email, needed for self-service password reset.
    # Existing users just have it unset until an admin fills it in (Team
    # page) or they're recreated - forgot-password gracefully says "no
    # email on file" for those rather than erroring. ---
    if "email" not in existing_cols:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()

    # bootstrap: create a default super-admin the very first time, so
    # there's always a way in.
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
    if cur.fetchone()[0] == 0:
        default_password = os.environ.get("ULTRAERP_ADMIN_PASSWORD") or secrets.token_urlsafe(9)
        cur.execute(
            "INSERT INTO users (company_id, username, password_hash, full_name, role, created_at) "
            "VALUES (NULL, 'admin', ?, 'Platform Admin', 'super_admin', ?)",
            (generate_password_hash(default_password), now_iso()),
        )
        conn.commit()
        print("=" * 60)
        print(" First run: created super-admin login")
        print(f"   username: admin")
        print(f"   password: {default_password}")
        print(" (Change this after logging in - see /admin/change-password)")
        print("=" * 60)

    conn.close()


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "company"


def unique_slug(name):
    base = slugify(name)
    conn = get_master_connection()
    cur = conn.cursor()
    slug = base
    i = 2
    while True:
        cur.execute("SELECT id FROM companies WHERE slug = ?", (slug,))
        if cur.fetchone() is None:
            conn.close()
            return slug
        slug = f"{base}-{i}"
        i += 1


# ---------------------------------------------------------------------
# Companies (tenants)
# ---------------------------------------------------------------------
def create_company(name, admin_username, admin_password, admin_full_name="",
                    subscription_status="trial", trial_days=14, admin_email=None):
    slug = unique_slug(name)
    expiry = (date.today() + timedelta(days=trial_days)).isoformat() if subscription_status == "trial" else None

    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO companies (name, slug, subscription_status, subscription_expiry, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, slug, subscription_status, expiry, now_iso()),
    )
    company_id = cur.lastrowid

    cur.execute(
        "INSERT INTO users (company_id, username, password_hash, full_name, role, email, created_at) "
        "VALUES (?, ?, ?, ?, 'admin', ?, ?)",
        (company_id, admin_username, generate_password_hash(admin_password), admin_full_name,
         admin_email or None, now_iso()),
    )
    conn.commit()
    conn.close()

    # provision this tenant's own database
    import db
    tenant_dir = os.path.join(TENANTS_DIR, slug)
    os.makedirs(tenant_dir, exist_ok=True)
    tenant_db_path = os.path.join(tenant_dir, "ultra_erp.db")
    db.set_active_db_path(tenant_db_path)
    db.init_db()

    return company_id, slug


def list_companies():
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, subscription_status, subscription_expiry, created_at "
                "FROM companies ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "slug": r[2], "subscription_status": r[3],
         "subscription_expiry": r[4], "created_at": r[5],
         "is_expired": bool(r[4] and r[4] < date.today().isoformat())}
        for r in rows
    ]


def get_company(company_id):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, subscription_status, subscription_expiry, notes, created_at, business_type "
                "FROM companies WHERE id = ?", (company_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "slug": row[2], "subscription_status": row[3],
            "subscription_expiry": row[4], "notes": row[5], "created_at": row[6], "business_type": row[7]}


def set_company_business_type(company_id, business_type):
    """Called once, the first time (or a deliberate re-choice) a company
    picks a business off the "What do you deal in?" screen - see
    app.py's business_choose(). From then on, login() sends them
    straight to that business's dashboard instead of the picker."""
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE companies SET business_type = ? WHERE id = ?", (business_type, company_id))
    conn.commit()
    conn.close()


def get_company_by_slug(slug):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, slug, subscription_status, subscription_expiry, notes, created_at "
                "FROM companies WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "slug": row[2], "subscription_status": row[3],
            "subscription_expiry": row[4], "notes": row[5], "created_at": row[6]}


def set_subscription(company_id, status, expiry_date=None, notes=None):
    conn = get_master_connection()
    cur = conn.cursor()
    if notes is not None:
        cur.execute("UPDATE companies SET subscription_status = ?, subscription_expiry = ?, notes = ? WHERE id = ?",
                    (status, expiry_date, notes, company_id))
    else:
        cur.execute("UPDATE companies SET subscription_status = ?, subscription_expiry = ? WHERE id = ?",
                    (status, expiry_date, company_id))
    conn.commit()
    conn.close()


def is_subscription_active(company):
    """A company can be used if status is 'active', or 'trial' with an
    expiry date that hasn't passed yet."""
    if company["subscription_status"] == "active":
        return True
    if company["subscription_status"] == "trial":
        if not company["subscription_expiry"]:
            return True
        return company["subscription_expiry"] >= date.today().isoformat()
    return False


def tenant_db_path(slug):
    return os.path.join(TENANTS_DIR, slug, "ultra_erp.db")


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
def verify_login(username, password):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, company_id, username, password_hash, full_name, role, can_edit, email FROM users WHERE username = ?",
                (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    user_id, company_id, uname, pw_hash, full_name, role, can_edit, email = row
    if not check_password_hash(pw_hash, password):
        return None
    return {"id": user_id, "company_id": company_id, "username": uname, "full_name": full_name,
            "role": role, "can_edit": bool(can_edit), "email": email}


def get_user(user_id):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, company_id, username, full_name, role, can_edit, email FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "company_id": row[1], "username": row[2], "full_name": row[3],
            "role": row[4], "can_edit": bool(row[5]), "email": row[6]}


def get_user_by_login_identifier(identifier):
    """Forgot-password accepts either a username or an email - looks up
    by whichever matches."""
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, company_id, username, full_name, role, can_edit, email FROM users "
                "WHERE username = ? OR (email IS NOT NULL AND email = ?)", (identifier, identifier))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "company_id": row[1], "username": row[2], "full_name": row[3],
            "role": row[4], "can_edit": bool(row[5]), "email": row[6]}


def set_user_email(user_id, email):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET email = ? WHERE id = ?", ((email or "").strip() or None, user_id))
    conn.commit()
    conn.close()


def user_can_edit(user):
    """Admins always have full edit/delete rights. Staff only have it
    if an admin has explicitly granted it (see set_can_edit)."""
    return user["role"] in ("admin", "super_admin") or user.get("can_edit")


def list_users_for_company(company_id):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, can_edit, created_at, email FROM users WHERE company_id = ? ORDER BY username",
                (company_id,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1], "full_name": r[2], "role": r[3], "can_edit": bool(r[4]),
             "created_at": r[5], "email": r[6]}
            for r in rows]


def set_can_edit(user_id, can_edit):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET can_edit = ? WHERE id = ?", (1 if can_edit else 0, user_id))
    conn.commit()
    conn.close()


def create_user(company_id, username, password, full_name="", role="staff", email=None):
    conn = get_master_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (company_id, username, password_hash, full_name, role, email, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (company_id, username, generate_password_hash(password), full_name, role, email or None, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def change_password(user_id, new_password):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new_password), user_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Self-service password reset - a short-lived, one-time token emailed to
# the user, since the only reset path before this was "ask the platform
# admin to do it for you" (admin_change_password, and only for the
# admin's own account at that).
# ---------------------------------------------------------------------
RESET_TOKEN_VALID_MINUTES = 30


def create_password_reset(user_id):
    """Invalidates any earlier unused tokens for this user first, so an
    old emailed link can't still be used after a newer one was issued."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=RESET_TOKEN_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
    cur.execute("INSERT INTO password_resets (user_id, token, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (user_id, token, expires_at, now_iso()))
    conn.commit()
    conn.close()
    return token, RESET_TOKEN_VALID_MINUTES


def get_valid_password_reset(token):
    """Returns the associated user dict if the token exists, hasn't been
    used, and hasn't expired - otherwise None (deliberately doesn't
    distinguish *why* it's invalid, to the caller or the user)."""
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expires_at, used FROM password_resets WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    user_id, expires_at, used = row
    if used or expires_at < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return None
    return get_user(user_id)


def consume_password_reset(token):
    conn = get_master_connection()
    cur = conn.cursor()
    cur.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()
