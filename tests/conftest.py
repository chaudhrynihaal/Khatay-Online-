"""
Shared pytest fixtures.

Every test runs against a throwaway master DB + tenant directory under
pytest's tmp_path, never the real ultra_erp_master.db / tenants/ - so the
suite is safe to run against a machine that has real customer data on it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import master
import db
import app as app_module

# CSRF tokens are injected into forms by client-side JS (see base.html) -
# the test client posts raw dicts and has no browser to run that script,
# so every ordinary test would otherwise fail with a 403 on its first
# POST. Standard practice for testing a Flask-WTF app: disable CSRF
# checking for the suite by default, and prove it's actually wired up
# with one dedicated test that turns it back on - see test_csrf.py.
app_module.app.config["WTF_CSRF_ENABLED"] = False


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setattr(master, "MASTER_DB_PATH", str(tmp_path / "master.db"))
    monkeypatch.setattr(master, "TENANTS_DIR", str(tmp_path / "tenants"))
    master.init_master_db()
    yield


@pytest.fixture()
def company(isolated_env):
    """A fresh, active-subscription company with one admin user, its
    tenant DB fully provisioned (Yarn + Kiryana + Hardware schemas) and
    set as the active DB for direct db.* calls in the test."""
    company_id, slug = master.create_company(
        "Test Co", "testadmin", "testpass123", admin_full_name="Test Admin",
    )
    master.set_subscription(company_id, "active", None)
    db.set_active_db_path(master.tenant_db_path(slug))
    admin_user = master.list_users_for_company(company_id)[0]
    return {"id": company_id, "slug": slug, "admin_user_id": admin_user["id"]}


@pytest.fixture()
def client(company):
    """Flask test client already logged in as the test company's admin.
    app.py's before_request hook derives g.company (and the active tenant
    DB) from session['user_id'] on every request, so nothing else to set."""
    c = app_module.app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = company["admin_user_id"]
    return c


@pytest.fixture()
def client_anon(isolated_env):
    """Flask test client with no session at all - for the pre-auth
    screens (Login, Forgot Password, Reset Password) that render before
    g.user/g.company exist."""
    return app_module.app.test_client()
