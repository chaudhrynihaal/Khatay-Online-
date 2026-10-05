"""The redesigned Receipt & Payment screen - Cash mode (the sign typed
into Amount silently picks Receipt vs Payment, matching the server
which ignores the submitted voucher_type in this branch) and Cheque
mode (explicit Receipt/Payment choice, a repeatable cheque-lines
builder posted as real cheque_date[]/cheque_bank[]/cheque_no[]/
cheque_amount[] arrays). Visually verified via a headless-browser pass
covering both modes, including the client-side "add at least one
cheque" guard. These tests check what the test client can verify
server-side: the injected data, and that both save paths still produce
the same DB rows as the pre-migration page did."""
import db


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type, "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_recovery_page_injects_parties_and_recent(client, company):
    _add_party(client, "V2 Recovery Party")
    r = client.get("/recovery")
    html = r.data.decode()
    assert '"name": "V2 Recovery Party"' in html
    assert "recent:" in html
    assert 'partyQuickAddUrl: "/parties/quick-add"' in html


def test_cash_mode_negative_amount_saves_as_payment(client, company):
    party_id = _add_party(client, "V2 Recovery Party 2")
    r = client.post("/recovery", data={
        "date": "2026-01-01", "party_id": str(party_id), "mode": "Cash",
        "amount": "-500", "voucher_type": "RECEIPT",  # server ignores this in Cash mode
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"Payment saved as PAY-000001."' in html

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT voucher_type, amount, cash_or_cheque FROM transactions WHERE party_id = ?", (party_id,))
    row = cur.fetchone()
    conn.close()
    assert row == ("PAYMENT", 500.0, "Cash")


def test_cash_mode_positive_amount_saves_as_receipt(client, company):
    party_id = _add_party(client, "V2 Recovery Party 3")
    r = client.post("/recovery", data={
        "date": "2026-01-01", "party_id": str(party_id), "mode": "Cash", "amount": "750",
    }, follow_redirects=True)
    assert '"Receipt saved as RCPT-000001."' in r.data.decode()


def test_cheque_mode_saves_lines_and_sums_amount(client, company):
    party_id = _add_party(client, "V2 Recovery Party 4")
    r = client.post("/recovery", data={
        "date": "2026-01-01", "party_id": str(party_id), "mode": "Cheque", "voucher_type": "RECEIPT",
        "cheque_date[]": ["2026-01-01", "2026-01-02"],
        "cheque_bank[]": ["HBL", "UBL"],
        "cheque_no[]": ["CHQ-1", "CHQ-2"],
        "cheque_amount[]": ["300", "450"],
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"Receipt saved as RCPT-000001."' in html
    assert '"amount": 750.0' in html  # sum of the two cheque lines

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cash_or_cheque, cheque_no FROM transactions WHERE party_id = ?", (party_id,))
    tid, mode, first_no = cur.fetchone()
    assert mode == "Cheque"
    assert first_no == "CHQ-1"
    cur.execute("SELECT bank, cheque_no, amount FROM transaction_cheques WHERE transaction_id = ? ORDER BY id", (tid,))
    rows = cur.fetchall()
    conn.close()
    assert rows == [("HBL", "CHQ-1", 300.0), ("UBL", "CHQ-2", 450.0)]
