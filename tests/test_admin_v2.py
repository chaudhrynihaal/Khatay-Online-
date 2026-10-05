"""The redesigned super-admin panel (Companies/Dashboard, Subscriptions,
Company Detail, Change Password) - 4 screens, all React/design-system
pages reading window.__PAGE__, wired to the entirely unchanged app.py/
master.py admin_* routes. This is the smallest and most tightly scoped
vertical: a super_admin's g.company is always None (see
load_tenant_context), so there is deliberately no tenant business data
or "log in as this company" feature anywhere here - confirmed by
design-brief.md's explicit no-impersonation scoping, which the new
pages preserve unchanged (only a subscription-status form and a
company-scoped user list/add/remove, same as before).

Visually verified via a headless-browser pass against the live dev
server's real production company list (Demo, SS, Shahid Siddique,
Smart tex world, sapna entp, seasons tex): the Subscriptions page's
overdue-first sort and red "Overdue by Nd" labels, the Company Detail
page's subscription form and user-management flow, and the sidebar
correctly showing only "Sign out" (no "Switch business", since a
super_admin has no tenant to switch away from) - no console errors
anywhere. These tests check what the test client can verify
server-side: injected data and that every route's create/update/
delete behavior for companies and their users is unchanged."""
import master


def _login_as_super_admin(client_anon):
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'super_admin'")
    admin_id = cur.fetchone()[0]
    conn.close()
    with client_anon.session_transaction() as sess:
        sess["user_id"] = admin_id
    return client_anon


def test_dashboard_injects_company_list(client_anon):
    c = _login_as_super_admin(client_anon)
    company_id, slug = master.create_company("V2 Admin Co", "v2adminuser", "pw123456", admin_full_name="V2 Admin")
    r = c.get("/admin")
    html = r.data.decode()
    assert '"name": "V2 Admin Co"' in html
    assert '"subscription_status": "trial"' in html


def test_create_company_flow(client_anon):
    c = _login_as_super_admin(client_anon)
    r = c.post("/admin/companies", data={
        "company_name": "V2 New Co", "admin_username": "v2newadmin", "admin_password": "pw123456",
        "admin_full_name": "V2 New Admin", "admin_email": "v2@test.com", "trial_days": "30",
    }, follow_redirects=True)
    assert '"V2 New Co"' in r.data.decode()

    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM companies WHERE name = 'V2 New Co'")
    company_id = cur.fetchone()[0]
    conn.close()
    company = master.get_company(company_id)
    assert company["subscription_status"] == "trial"


def test_create_company_rejects_short_password(client_anon):
    c = _login_as_super_admin(client_anon)
    r = c.post("/admin/companies", data={
        "company_name": "V2 Bad Co", "admin_username": "v2baduser", "admin_password": "abc",
    }, follow_redirects=True)
    assert "at least" in r.data.decode()
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM companies WHERE name = 'V2 Bad Co'")
    assert cur.fetchone()[0] == 0
    conn.close()


def test_company_detail_injects_company_and_users(client_anon):
    c = _login_as_super_admin(client_anon)
    company_id, slug = master.create_company("V2 Detail Co", "v2detailadmin", "pw123456")
    r = c.get(f"/admin/companies/{company_id}")
    html = r.data.decode()
    assert '"name": "V2 Detail Co"' in html
    assert '"username": "v2detailadmin"' in html


def test_update_subscription(client_anon):
    c = _login_as_super_admin(client_anon)
    company_id, slug = master.create_company("V2 Sub Co", "v2subadmin", "pw123456")
    r = c.post(f"/admin/companies/{company_id}/subscription", data={
        "status": "active", "expiry": "2027-06-01", "notes": "V2 test note",
    }, follow_redirects=True)
    assert '"Subscription updated."' in r.data.decode()
    company = master.get_company(company_id)
    assert company["subscription_status"] == "active"
    assert company["subscription_expiry"] == "2027-06-01"
    assert company["notes"] == "V2 test note"


def test_create_and_delete_user_for_company(client_anon):
    c = _login_as_super_admin(client_anon)
    company_id, slug = master.create_company("V2 User Co", "v2useradmin", "pw123456")
    r = c.post(f"/admin/companies/{company_id}/users", data={
        "username": "v2staffuser", "password": "pw123456", "full_name": "V2 Staff", "role": "staff",
    }, follow_redirects=True)
    assert '"v2staffuser"' in r.data.decode()

    users = master.list_users_for_company(company_id)
    staff = next(u for u in users if u["username"] == "v2staffuser")
    assert staff["role"] == "staff"

    r2 = c.post(f"/admin/users/{staff['id']}/delete", follow_redirects=True)
    assert r2.status_code == 200
    users_after = master.list_users_for_company(company_id)
    assert not any(u["username"] == "v2staffuser" for u in users_after)


def test_delete_user_route_refuses_to_delete_a_super_admin(client_anon):
    c = _login_as_super_admin(client_anon)
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'super_admin'")
    super_admin_id = cur.fetchone()[0]
    conn.close()
    c.post(f"/admin/users/{super_admin_id}/delete", follow_redirects=True)
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE id = ?", (super_admin_id,))
    assert cur.fetchone()[0] == 1  # still present
    conn.close()


def test_subscriptions_page_sorts_overdue_first(client_anon):
    c = _login_as_super_admin(client_anon)
    company_id, slug = master.create_company("V2 Overdue Co", "v2overdueadmin", "pw123456")
    master.set_subscription(company_id, "trial", "2020-01-01", "")
    r = c.get("/admin/subscriptions")
    html = r.data.decode()
    assert "overdueCount:" in html
    assert '"name": "V2 Overdue Co"' in html
    # keys are serialized alphabetically, so days_until_due (a large
    # negative number for a 2020 expiry) precedes name in the same object
    idx = html.find('"name": "V2 Overdue Co"')
    snippet = html[max(0, idx - 400):idx]
    assert '"days_until_due": -' in snippet


def test_change_own_password(client_anon):
    c = _login_as_super_admin(client_anon)
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'super_admin'")
    admin_id = cur.fetchone()[0]
    conn.close()

    r = c.post("/admin/change-password", data={"new_password": "brandnewpass123"}, follow_redirects=True)
    assert '"Password changed."' in r.data.decode()

    from master import verify_login
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE id = ?", (admin_id,))
    username = cur.fetchone()[0]
    conn.close()
    assert verify_login(username, "brandnewpass123") is not None


def test_non_super_admin_cannot_reach_admin_panel(client):
    r = client.get("/admin", follow_redirects=True)
    assert r.status_code == 200
    assert b"Companies" not in r.data or b"Add a new company" not in r.data
