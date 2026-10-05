"""The redesigned Team, Settings, and Backup History screens. Visually
verified via a headless-browser pass: adding a team member, granting
edit rights (button flips to the "Can Edit" primary state), and saving
Settings with a changed warehouse address + theme swatch (both
persisted and reflected on reload). Backup History was also checked in
its "not configured" empty state (no B2_BUCKET env var in dev) - a
bug found and fixed during this migration: the old app.py route
sometimes omits `error` from its render_template() call, and the first
version of the new template's `{{ error|tojson }}` blew up on Jinja's
Undefined placeholder in that case; fixed with `{{ error|default(none)|tojson }}`.
These tests check what the test client can verify server-side: each
screen's injected data and that the underlying routes still behave
exactly as before."""
import master
import settings as settings_module


def test_team_page_injects_users_and_current_user_id(client, company):
    r = client.get("/team")
    html = r.data.decode()
    assert '"username": "testadmin"' in html
    assert "currentUserId: %d" % company["admin_user_id"] in html


def test_adding_team_member_and_granting_edit_rights(client, company):
    r = client.post("/team", data={"username": "v2staffuser", "password": "pw123456",
                                    "full_name": "V2 Staff", "role": "staff"}, follow_redirects=True)
    assert "'v2staffuser' added" in r.data.decode() or "v2staffuser" in r.data.decode()

    users = master.list_users_for_company(company["id"])
    staff = next(u for u in users if u["username"] == "v2staffuser")
    assert staff["can_edit"] is False

    r2 = client.post(f"/team/{staff['id']}/toggle-edit", follow_redirects=True)
    assert '"Edit rights granted to' in r2.data.decode()

    users2 = master.list_users_for_company(company["id"])
    staff2 = next(u for u in users2 if u["username"] == "v2staffuser")
    assert staff2["can_edit"] is True


def test_deleting_own_account_is_blocked(client, company):
    r = client.post(f"/team/{company['admin_user_id']}/delete", follow_redirects=True)
    assert "can\\u0027t remove your own account" in r.data.decode()


def test_settings_page_injects_current_values(client, company):
    r = client.get("/settings")
    html = r.data.decode()
    assert "theme: \"Purple\"" in html
    assert '"Purple"' in html  # present in the themes dict too


def test_saving_settings_updates_warehouse_address_and_theme(client, company):
    r = client.post("/settings", data={
        "company_name": "V2 Test Co", "theme": "Green",
        "warehouse_address": "V2 Test Warehouse", "notification_email": "",
        "opening_cash_balance": "0",
    }, follow_redirects=True)
    assert '"Settings saved."' in r.data.decode()
    assert settings_module.get_warehouse_address() == "V2 Test Warehouse"
    assert settings_module.get_theme() == "Green"


def test_backup_history_page_renders_not_configured_state(client, company, monkeypatch):
    monkeypatch.delenv("B2_BUCKET", raising=False)
    r = client.get("/backup-history")
    html = r.data.decode()
    assert "available: false" in html
    assert "error: null" in html


def test_backup_history_blocked_for_non_admin(client, company):
    staff_id = master.create_user(company["id"], "v2nonadmin", "pw123456", "V2 Non Admin", "staff")
    c = client.application.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = staff_id
    r = c.get("/backup-history", follow_redirects=True)
    assert '"Only a company admin can manage users."' in r.data.decode()
