"""The redesigned Yarn Dashboard (first screen migrated to the new
React/design-system frontend). The page itself is client-rendered, so
these tests check what the test client CAN verify server-side: the
injected __PAGE__ data is correct, and the static assets it depends on
are actually reachable."""
from datetime import date

import db


def _add_party(client, name, party_type="Customer", opening_balance=0):
    client.post("/parties", data={"name": name, "party_type": party_type,
                                   "opening_balance": str(opening_balance)}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def _add_quality(client, name, sale_rate=100):
    client.post("/quality", data={"name": name, "sale_rate": str(sale_rate)}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_dashboard_page_loads_the_new_design_system_assets(client, company):
    r = client.get("/")
    assert r.status_code == 200
    html = r.data.decode()
    assert 'static/ds/styles.css' in html
    assert 'static/ds/ds-bundle.js' in html
    assert 'static/js/pages/yarn-dashboard.js' in html
    assert '__PAGE__' in html


def test_dashboard_injects_correct_real_numbers(client, company):
    party_id = _add_party(client, "Dashboard Test Customer", opening_balance=0)
    quality_id = _add_quality(client, "Dashboard Test Yarn")
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "10", "rate": "200", "date": date.today().isoformat(), "mode": "Credit",
    })

    r = client.get("/")
    html = r.data.decode()
    assert "totalReceivable: 2000.0" in html
    assert "partyCount: 1" in html


def test_dashboard_static_assets_are_served_correctly(client, company):
    for path, snippet in [
        ("/static/ds/styles.css", "@import"),
        ("/static/ds/ds-bundle.js", "KhatayOnlineDesignSystem_90c3f9"),
        ("/static/js/pages/ds-shell.js", "mountShell"),
        ("/static/js/pages/yarn-dashboard.js", "Quick actions"),
    ]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert snippet in r.data.decode()
