"""Proves CSRF protection is actually wired up - every other test in the
suite runs with it disabled (see conftest.py), so this is the one place
that turns it back on to check a request without a valid token is really
rejected, and one with a valid token really goes through."""
import pytest

import app as app_module
import db


@pytest.fixture()
def csrf_enabled():
    app_module.app.config["WTF_CSRF_ENABLED"] = True
    yield
    app_module.app.config["WTF_CSRF_ENABLED"] = False


def test_post_without_csrf_token_is_rejected(client, company, csrf_enabled):
    before = len(db.kiryana_list_parties("Customer"))
    r = client.post("/kiryana/customers/add", data={"name": "No Token Customer", "phone": ""},
                     follow_redirects=True)
    assert b"session needs a refresh" in r.data
    after = len(db.kiryana_list_parties("Customer"))
    assert after == before, "a request without a valid CSRF token must not be allowed through"


def test_post_with_valid_csrf_token_is_accepted(client, company, csrf_enabled):
    login_page = client.get("/kiryana/inventory")
    html = login_page.data.decode()
    start = html.find('name="csrf-token" content="') + len('name="csrf-token" content="')
    token = html[start:html.find('"', start)]
    assert token, "base.html must render a non-empty csrf-token meta tag"

    r = client.post("/kiryana/customers/add", data={"name": "With Token Customer", "phone": "",
                                                      "csrf_token": token}, follow_redirects=True)
    assert b"added" in r.data
