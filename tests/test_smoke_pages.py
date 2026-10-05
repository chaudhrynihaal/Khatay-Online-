"""Broad, shallow coverage: every GET page in the app (that doesn't need
a specific record id) rendered once with a logged-in session, asserting
it doesn't 500. Cheap to write and run, and catches template/query bugs
that the more targeted correctness tests elsewhere in this suite
wouldn't happen to exercise. Not a substitute for those - just a wide,
thin net underneath them."""
import pytest

import app as app_module
import master

COMPANY_PAGES = [
    "/", "/business", "/parties", "/quality", "/transactions", "/bookings",
    # /contra deliberately excluded - it's folded into /recovery now
    # (Mode: Contra) and just redirects there, see test_contra_v2.py
    "/recovery", "/capital-expense", "/data-import",
    "/reports/receivable", "/reports/payable", "/reports/stock", "/reports/trial-balance",
    "/reports/balance-sheet", "/reports/profit", "/reports/cashbook", "/reports/brokerage",
    "/reports/quality-ledger", "/reports/quality-ledger?view=count", "/reports/quality-ledger?view=rate",
    "/reports/ledger", "/settings", "/team",
    "/kiryana", "/kiryana/inventory", "/kiryana/sales", "/kiryana/purchases",
    "/kiryana/returns", "/kiryana/cashbook", "/kiryana/ledger", "/kiryana/expenses",
    "/hardware", "/hardware/inventory", "/hardware/sales", "/hardware/purchases",
    "/hardware/returns", "/hardware/cashbook", "/hardware/ledger", "/hardware/expenses",
    "/hardware/parties", "/hardware/quotations",
    "/backup", "/backup-history",
]

ADMIN_PAGES = ["/admin", "/admin/subscriptions", "/admin/change-password"]


@pytest.mark.parametrize("path", COMPANY_PAGES)
def test_company_page_renders_without_error(client, company, path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"


@pytest.fixture()
def admin_client(isolated_env):
    conn = master.get_master_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'super_admin'")
    uid = cur.fetchone()[0]
    conn.close()
    c = app_module.app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = uid
    return c


@pytest.mark.parametrize("path", ADMIN_PAGES)
def test_admin_page_renders_without_error(admin_client, path):
    r = admin_client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"


def test_reports_render_with_data_present(client, company):
    """The empty-state pass above is easy to satisfy trivially - this
    repeats the highest-traffic reports with at least one real
    transaction on the books, since that's where a template touching a
    None field or an off-by-one in a loop is actually likely to show up."""
    import db
    from datetime import date
    client.post("/parties", data={"name": "Smoke Party", "party_type": "Customer",
                                   "opening_balance": "1000"}, follow_redirects=True)
    client.post("/quality", data={"name": "Smoke Item", "sale_rate": "100"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = 'Smoke Party'")
    party_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM quality WHERE name = 'Smoke Item'")
    quality_id = cur.fetchone()[0]
    conn.close()
    today = date.today().isoformat()
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "10", "rate": "100", "date": today, "mode": "Credit",
    })
    client.post("/capital-expense", data={"kind": "expense", "category": "Home", "amount": "50", "date": today})

    for path in ["/reports/receivable", "/reports/payable", "/reports/stock",
                 "/reports/trial-balance", "/reports/profit", "/reports/cashbook",
                 f"/reports/ledger?party_id={party_id}"]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code} with real data on the books"


def test_quality_ledger_route_now_works(client, company):
    """Used to 500 unconditionally - db.get_quality_ledger() didn't
    exist and nothing in the UI linked here. Now implemented (Purchase/
    Sale Ledger, 3 views: Overall/By count/By rate) - see
    test_yarn_reports.py for the real correctness coverage."""
    r = client.get("/reports/quality-ledger?quality_id=1")
    assert r.status_code == 200
