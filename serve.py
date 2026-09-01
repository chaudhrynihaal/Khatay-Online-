"""
serve.py
---------
Production entry point. Unlike `python3 app.py` (which uses Flask's
built-in development server - fine for testing, not meant for real use
with real people depending on it), this uses waitress, a proper
production-grade WSGI server: no debug reloader, no "do not use in
production" warning, and it's what the systemd service (see
deploy/ultraerp.service) actually runs.

Usage:
    python3 serve.py

Reads two optional environment variables, same as app.py:
    ULTRAERP_SECRET_KEY      - long random string (required for real use)
    ULTRAERP_ADMIN_PASSWORD  - set the super-admin password on first run
"""

import os
from waitress import serve

import master
import db
import app as app_module

if __name__ == "__main__":
    master.init_master_db()

    # every time the app starts, bring every existing company's
    # database up to date with the current schema - so a future
    # update that adds a new table/column never leaves an older
    # company's database behind the way this one just did. Always
    # safe to run: every step is CREATE TABLE IF NOT EXISTS / ALTER
    # TABLE IF NOT EXISTS, never touches existing data.
    companies = master.list_companies()
    for c in companies:
        db.set_active_db_path(master.tenant_db_path(c["slug"]))
        db.init_db()
    if companies:
        print(f"Schema check: {len(companies)} compan{'y' if len(companies) == 1 else 'ies'} up to date.")

    port = int(os.environ.get("PORT", 8000))
    print(f"Khatay serving on port {port} (production mode)")
    serve(app_module.app, host="0.0.0.0", port=port, threads=8)
