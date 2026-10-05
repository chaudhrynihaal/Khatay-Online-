"""Login, rate limiting, and self-service password reset."""
import master
import app as app_module


def test_login_success_and_failure(company):
    c = app_module.app.test_client()
    ok = c.post("/login", data={"username": "testadmin", "password": "testpass123"})
    assert ok.status_code in (302, 200)
    with c.session_transaction() as sess:
        assert sess.get("user_id")

    c2 = app_module.app.test_client()
    bad = c2.post("/login", data={"username": "testadmin", "password": "wrongpassword"})
    with c2.session_transaction() as sess:
        assert not sess.get("user_id")


def test_login_goes_to_business_picker_until_a_business_is_chosen(company):
    c = app_module.app.test_client()
    r = c.post("/login", data={"username": "testadmin", "password": "testpass123"})
    assert r.headers["Location"].endswith("/business")


def test_choosing_a_business_persists_it_and_skips_the_picker_on_next_login(company):
    c = app_module.app.test_client()
    c.post("/login", data={"username": "testadmin", "password": "testpass123"})

    r = c.get("/business/choose/kiryana")
    assert r.headers["Location"].endswith("/kiryana")
    assert master.get_company(company["id"])["business_type"] == "kiryana"

    # a fresh login (fresh client/session) should now skip the picker
    c2 = app_module.app.test_client()
    r2 = c2.post("/login", data={"username": "testadmin", "password": "testpass123"})
    assert r2.headers["Location"].endswith("/kiryana")


def test_business_choose_rejects_an_unknown_business_type(company):
    c = app_module.app.test_client()
    c.post("/login", data={"username": "testadmin", "password": "testpass123"})
    r = c.get("/business/choose/not-a-real-business", follow_redirects=True)
    assert b"Unknown business type." in r.data
    assert master.get_company(company["id"])["business_type"] is None


def test_login_rate_limit_kicks_in(company):
    if app_module.limiter is None:
        return  # flask-limiter not installed in this environment
    c = app_module.app.test_client()
    statuses = []
    for _ in range(10):
        r = c.post("/login", data={"username": "testadmin", "password": "wrongpassword"})
        statuses.append(r.status_code)
    assert 429 in statuses, "expected a 429 once the per-minute login attempt limit is exceeded"


def test_password_reset_full_cycle(company):
    master.set_user_email(company["admin_user_id"], "reset-test@example.com")
    c = app_module.app.test_client()

    r = c.post("/forgot-password", data={"identifier": "testadmin"}, follow_redirects=True)
    assert b"reset link has been sent" in r.data

    r_unknown = c.post("/forgot-password", data={"identifier": "no-such-user"}, follow_redirects=True)
    assert r_unknown.data == r.data, "must show the identical generic message for unknown identifiers (no enumeration)"

    token, minutes = master.create_password_reset(company["admin_user_id"])
    assert minutes == master.RESET_TOKEN_VALID_MINUTES

    get_r = c.get(f"/reset-password/{token}")
    assert get_r.status_code == 200

    post_r = c.post(f"/reset-password/{token}",
                     data={"password": "newpassword456", "confirm": "newpassword456"},
                     follow_redirects=True)
    assert b"Password updated" in post_r.data

    assert master.verify_login("testadmin", "newpassword456") is not None
    assert master.verify_login("testadmin", "testpass123") is None


def test_password_reset_token_is_single_use(company):
    token, _ = master.create_password_reset(company["admin_user_id"])
    assert master.get_valid_password_reset(token) is not None
    master.consume_password_reset(token)
    assert master.get_valid_password_reset(token) is None


def test_password_reset_rejects_mismatched_or_short_password(company):
    c = app_module.app.test_client()
    token, _ = master.create_password_reset(company["admin_user_id"])

    r = c.post(f"/reset-password/{token}", data={"password": "abcdef", "confirm": "zzzzzz"})
    assert b"match" in r.data

    r2 = c.post(f"/reset-password/{token}", data={"password": "ab", "confirm": "ab"})
    assert b"at least 6 characters" in r2.data

    # token must still be valid/unused after both rejected attempts
    assert master.get_valid_password_reset(token) is not None


def test_invalid_or_expired_token_rejected(company):
    c = app_module.app.test_client()

    r = c.get("/reset-password/not-a-real-token", follow_redirects=True)
    assert b"invalid or has expired" in r.data

    token, _ = master.create_password_reset(company["admin_user_id"])
    conn = master.get_master_connection()
    conn.execute("UPDATE password_resets SET expires_at = '2000-01-01 00:00:00' WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    r2 = c.get(f"/reset-password/{token}", follow_redirects=True)
    assert b"invalid or has expired" in r2.data
