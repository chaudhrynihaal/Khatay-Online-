"""
settings.py
------------
Per-tenant settings (company name, color theme, opening cash balance),
stored as key-value rows in the active tenant's own database (via
db.get_connection(), which is already tenant-aware - see db.py's
set_active_db_path()). A JSON file wouldn't be safe here since
multiple companies' web requests can be in flight at once; a row in
each tenant's own SQLite file is naturally isolated per-tenant and
safe for concurrent access.
"""

import db

_DEFAULTS = {
    "company_name": "Your Company Name",
    "theme": "Purple",
    "opening_cash_balance": "0",
    "opening_cash_date": "",
    "warehouse_address": "",
    "logo_filename": "",
    "notification_email": "",
    "hardware_tax_rate": "0",
    "hardware_gst_number": "",
}


def _ensure_table():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()


def _get(key):
    _ensure_table()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else _DEFAULTS.get(key)


def _set(key, value):
    _ensure_table()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))
    conn.commit()
    conn.close()


def get_company_name():
    return _get("company_name") or _DEFAULTS["company_name"]


def set_company_name(name):
    _set("company_name", (name or "").strip() or _DEFAULTS["company_name"])


def get_theme():
    return _get("theme") or _DEFAULTS["theme"]


def set_theme(theme_name):
    _set("theme", theme_name)


def get_opening_cash_balance():
    amount = _get("opening_cash_balance")
    date_ = _get("opening_cash_date")
    try:
        amount = float(amount) if amount else 0.0
    except (TypeError, ValueError):
        amount = 0.0
    return amount, (date_ or None)


def set_opening_cash_balance(amount, as_of_date):
    _set("opening_cash_balance", float(amount or 0))
    _set("opening_cash_date", as_of_date or "")


def get_notification_email():
    return _get("notification_email") or ""


def set_notification_email(email):
    _set("notification_email", (email or "").strip())


def get_warehouse_address():
    return _get("warehouse_address") or ""


def set_warehouse_address(address):
    _set("warehouse_address", (address or "").strip())


def get_logo_filename():
    return _get("logo_filename") or ""


def set_logo_filename(filename):
    _set("logo_filename", filename or "")


def get_hardware_tax_rate():
    """Percentage - e.g. 17 for 17% GST. 0 means tax invoicing is off:
    bills print as a plain total with no tax breakdown."""
    try:
        return float(_get("hardware_tax_rate") or 0)
    except (TypeError, ValueError):
        return 0.0


def set_hardware_tax_rate(rate):
    _set("hardware_tax_rate", float(rate or 0))


def get_hardware_gst_number():
    return _get("hardware_gst_number") or ""


def set_hardware_gst_number(number):
    _set("hardware_gst_number", (number or "").strip())
