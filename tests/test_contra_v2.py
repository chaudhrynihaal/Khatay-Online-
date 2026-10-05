"""Contra entries - folded into Receipt & Payment as a third Mode
("Contra") instead of their own page (see yarn-recovery.js's
ContraLegsBuilder). The underlying /contra route is unchanged - same
validation (create_contra_entry still enforces total Dr == total Cr
and at least two legs server-side), same party_id[]/direction[]/
amount[] arrays - it just redirects back to /recovery afterward
instead of rendering its own page, and a GET on /contra (an old
bookmark/link) redirects there too. These tests check what the test
client can verify server-side: the redirect behavior, that saved
contra entries show up in Receipt & Payment's own recent-entries list,
and that the balance/leg-count validation still behaves exactly as
before."""
import db


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type, "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_get_contra_redirects_to_recovery(client, company):
    r = client.get("/contra")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/recovery")


def test_balanced_two_leg_contra_saves_and_redirects_to_recovery(client, company):
    a = _add_party(client, "V2 Contra A")
    b = _add_party(client, "V2 Contra B")

    r = client.post("/contra", data={
        "date": "2026-01-01", "description": "V2 test transfer",
        "party_id[]": [str(a), str(b)],
        "direction[]": ["DR", "CR"],
        "amount[]": ["800", "800"],
    })
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/recovery")

    r2 = client.get("/recovery", follow_redirects=True)
    html = r2.data.decode()
    assert '"Contra entry saved as CONTRA-000001."' in html
    assert '"voucher": "CONTRA-000001"' in html
    assert '"type": "CONTRA_DR"' in html
    assert '"type": "CONTRA_CR"' in html
    assert '"description": "V2 test transfer"' in html
    assert '"mode": "Contra"' in html

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE voucher_type IN ('CONTRA_DR','CONTRA_CR')")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_unbalanced_contra_is_rejected_server_side(client, company):
    a = _add_party(client, "V2 Contra C")
    b = _add_party(client, "V2 Contra D")

    r = client.post("/contra", data={
        "date": "2026-01-01",
        "party_id[]": [str(a), str(b)],
        "direction[]": ["DR", "CR"],
        "amount[]": ["800", "500"],
    }, follow_redirects=True)
    html = r.data.decode()
    assert "doesn\\u0027t balance" in html

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE voucher_type IN ('CONTRA_DR','CONTRA_CR')")
    assert cur.fetchone()[0] == 0
    conn.close()


def test_single_nonzero_leg_contra_fails_the_balance_check_first(client, company):
    """A lone non-zero leg can never balance (nothing sums against it),
    so create_contra_entry's Dr==Cr check rejects it before its
    separate "needs at least two parties" check is ever reached -
    matching the pre-migration page's server-side validation order."""
    a = _add_party(client, "V2 Contra E")
    r = client.post("/contra", data={
        "date": "2026-01-01",
        "party_id[]": [str(a)],
        "direction[]": ["DR"],
        "amount[]": ["500"],
    }, follow_redirects=True)
    assert "doesn\\u0027t balance" in r.data.decode()


def test_single_zero_amount_leg_hits_the_needs_two_parties_check(client, company):
    a = _add_party(client, "V2 Contra F")
    r = client.post("/contra", data={
        "date": "2026-01-01",
        "party_id[]": [str(a)],
        "direction[]": ["DR"],
        "amount[]": ["0"],
    }, follow_redirects=True)
    assert "at least two parties" in r.data.decode()
