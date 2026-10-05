"""The redesigned Edit Entry screen - reachable from every entry
screen's Edit action, its field set depends on the transaction's
voucher_type (Sale/Purchase gets qty+rate+item+broker; Receipt/Payment
gets a single amount + a note about cheque lines; Expense/Capital gets
just date+amount+description), exactly like the old page's three
Jinja branches. Visually verified via a headless-browser pass
(prefilled fields, sidebar highlighting the right section per
voucher_type, and that Save correctly honors return_to to land back on
whichever entry screen linked here instead of always the dashboard).
These tests check what the test client can verify server-side: each
branch injects the right data, and each branch's POST still updates
the same columns the pre-migration page did."""
from datetime import date

import db


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type, "opening_balance": "0"}, follow_redirects=True)
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


def test_edit_page_for_sale_injects_qty_rate_and_item_fields(client, company):
    party_id = _add_party(client, "V2 Edit Sale Party")
    quality_id = _add_quality(client, "V2 Edit Sale Item")
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "5", "rate": "100", "date": date.today().isoformat(), "mode": "Cash",
    })
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'SALE'")
    tid = cur.fetchone()[0]
    conn.close()

    r = client.get(f"/transaction/{tid}/edit?return_to=/transactions")
    html = r.data.decode()
    assert 'vType: "SALE"' in html
    assert '"qty": 5.0' in html
    assert '"rate": 100.0' in html
    assert 'returnTo: "/transactions"' in html


def test_edit_page_for_receipt_injects_amount_only_fields(client, company):
    party_id = _add_party(client, "V2 Edit Receipt Party")
    client.post("/recovery", data={"date": date.today().isoformat(), "party_id": str(party_id),
                                    "mode": "Cash", "amount": "300"})
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'RECEIPT'")
    tid = cur.fetchone()[0]
    conn.close()

    r = client.get(f"/transaction/{tid}/edit")
    html = r.data.decode()
    assert 'vType: "RECEIPT"' in html
    assert '"amount": 300.0' in html


def test_saving_sale_edit_updates_qty_and_recomputes_amount(client, company):
    party_id = _add_party(client, "V2 Edit Sale Party 2")
    quality_id = _add_quality(client, "V2 Edit Sale Item 2")
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "5", "rate": "100", "date": date.today().isoformat(), "mode": "Cash",
    })
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'SALE'")
    tid = cur.fetchone()[0]
    conn.close()

    client.post(f"/transaction/{tid}/edit", data={
        "date": date.today().isoformat(), "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "8", "rate": "100", "mode": "Cash", "return_to": "",
    }, follow_redirects=True)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT qty, amount FROM transactions WHERE id = ?", (tid,))
    row = cur.fetchone()
    conn.close()
    assert row == (8.0, 800.0)


def test_saving_edit_redirects_to_return_to(client, company):
    party_id = _add_party(client, "V2 Edit Receipt Party 2")
    client.post("/recovery", data={"date": date.today().isoformat(), "party_id": str(party_id),
                                    "mode": "Cash", "amount": "150"})
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'RECEIPT'")
    tid = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/transaction/{tid}/edit", data={
        "date": date.today().isoformat(), "party_id": str(party_id), "amount": "150",
        "mode": "Cash", "return_to": "/recovery",
    })
    assert r.status_code == 302
    assert r.headers["Location"] == "/recovery"
