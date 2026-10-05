"""The redesigned pre-auth screens (Login, Forgot Password, Reset
Password) and Business Select. These run before g.user/g.company exist
(Login/Forgot/Reset) so they use a separate, minimal
_v2_auth_page_data.html + the sidebar-less mountAuthShell, rather than
the normal app shell every other migrated screen uses.

Two real bugs found and fixed during this migration:
1. Every already-migrated page (this one included) had silently lost
   PWA service-worker registration, since only the OLD base.html
   registered it and none of the new standalone pages extend it -
   fixed once in the shared _v2_head.html include, which fixes every
   past and future migrated screen at once.
2. login.html's `alreadySignedIn: {{ already_signed_in|tojson }}`
   crashed with "Object of type Undefined is not JSON serializable"
   on the rate-limited-login 429 path, which renders login.html
   without passing already_signed_in at all - fixed with
   `|default(none)|tojson`, the same pattern already used for
   backup_history's `error` var.

Also visually verified via a headless browser: the "already signed
in" banner initially overlapped its own text with the Continue/Sign-out
buttons in the narrow 400px auth card (DS.Banner's fixed two-column
title/action layout doesn't reflow) - fixed by hand-rolling a stacked
layout instead of using DS.Banner there. The real sign-in flow, the
Business Select grid, and a real (single-use) password-reset link all
rendered and worked correctly with no console errors."""
import master


def test_login_page_renders_and_registers_service_worker(client_anon):
    r = client_anon.get("/login")
    html = r.data.decode()
    assert r.status_code == 200
    assert "serviceWorker" in html
    assert "alreadySignedIn: null" in html


def test_login_page_shows_already_signed_in_banner(client):
    r = client.get("/login")
    html = r.data.decode()
    assert '"username": "testadmin"' in html


def test_rate_limited_login_still_renders_without_crashing(client_anon):
    """Hitting POST /login enough times trips the 8/min rate limit,
    whose handler renders login.html with no already_signed_in kwarg at
    all - this used to be a 500 (Undefined isn't JSON serializable),
    not the intended 429 + rendered page."""
    last = None
    for _ in range(9):
        last = client_anon.post("/login", data={"username": "nobody", "password": "wrong"})
    assert last.status_code == 429
    assert "alreadySignedIn: null" in last.data.decode()


def test_forgot_password_page_renders(client_anon):
    r = client_anon.get("/forgot-password")
    assert r.status_code == 200
    assert "serviceWorker" in r.data.decode()


def test_reset_password_page_renders_with_valid_token(client_anon):
    company_id, slug = master.create_company("V2 Reset Co", "v2resetuser", "pw123456", admin_full_name="V2 Reset Admin")
    admin_user = master.list_users_for_company(company_id)[0]
    token, _ = master.create_password_reset(admin_user["id"])
    r = client_anon.get(f"/reset-password/{token}")
    html = r.data.decode()
    assert r.status_code == 200
    assert 'username: "v2resetuser"' in html
    master.consume_password_reset(token)


def test_reset_password_invalid_token_redirects(client_anon):
    r = client_anon.get("/reset-password/not-a-real-token", follow_redirects=True)
    assert '"That reset link is invalid or has expired' in r.data.decode()


def test_business_select_page_renders_for_logged_in_company(client):
    r = client.get("/business")
    html = r.data.decode()
    assert r.status_code == 200
    assert "yarnUrl:" in html
    assert "kiryanaUrl:" in html
    assert "hardwareUrl:" in html
