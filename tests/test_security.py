"""Regression coverage for security issues found in the whole-app audit.
Each test here should map to a real, previously-exploitable request."""
import os

import settings


def test_logo_route_blocks_path_traversal_out_of_tenant_dir(client, company, tmp_path, monkeypatch):
    """/logo/<filename> used to use a <path:...> converter with no
    sanitization, so a request like /logo/../other-slug/ultra_erp.db
    could read any other tenant's database - or the master DB - straight
    off the filesystem. See app.py's company_logo() for the fix."""
    payloads = [
        "../ss/ultra_erp.db",
        "../../ultra_erp_master.db",
        "..%2f..%2fultra_erp_master.db",
    ]
    for payload in payloads:
        r = client.get(f"/logo/{payload}")
        assert r.status_code == 404, f"path traversal payload {payload!r} was not blocked"


def test_logo_route_still_serves_a_real_uploaded_logo(client, company):
    import db
    tenant_dir = os.path.dirname(db.get_active_db_path())
    logo_path = os.path.join(tenant_dir, "logo.png")
    with open(logo_path, "wb") as f:
        f.write(b"not-a-real-png-just-bytes")
    settings.set_logo_filename("logo.png")
    try:
        r = client.get("/logo/logo.png")
        assert r.status_code == 200
        assert r.data == b"not-a-real-png-just-bytes"
        r.close()  # release the file handle send_file() opened, before we try to remove it below
    finally:
        settings.set_logo_filename("")
        try:
            os.remove(logo_path)
        except PermissionError:
            pass  # Windows may still hold the handle briefly; tmp_path teardown will clean it up
