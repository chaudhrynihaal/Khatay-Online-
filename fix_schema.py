"""
fix_schema.py
------------------
One-time fix: brings every EXISTING company's database up to date with
the latest schema (new tables/columns added since they were created).

Newly-created companies always get the current schema automatically,
but companies created before a schema change never retroactively pick
it up on their own - this script does that catch-up, safely (every
step uses CREATE TABLE IF NOT EXISTS / ALTER TABLE IF NOT EXISTS, so
running this never touches or risks any existing data).

Usage (on the server):
    cd /opt/ultraerp
    sudo -u ultraerp venv/bin/python3 fix_schema.py
"""

import master
import db

master.init_master_db()

companies = master.list_companies()
print(f"Found {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}.")

for c in companies:
    db.set_active_db_path(master.tenant_db_path(c["slug"]))
    db.init_db()
    print(f"  {c['name']} ({c['slug']}) - schema up to date")

print("Done. Every company's database is now current.")
