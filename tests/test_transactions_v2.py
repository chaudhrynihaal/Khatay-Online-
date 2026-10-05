"""The redesigned Purchase & Sale Entry screen. Its two-step
signature-capture wizard was visually verified via headless browser and
caught a real bug: the first version rendered each wizard step as its
own <form>-owning component, so React unmounted (detached) the step-1
form the moment the signature step mounted, and calling .submit() on a
detached form is a silent no-op in Chrome - nothing ever saved. Fixed by
giving the whole wizard one persistent <form>, both steps as
conditionally-rendered children inside it. These tests check the
server-side data wiring; the save flow itself is covered by having
caused and fixed that exact bug via the browser."""
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


def test_transactions_page_injects_parties_items_and_brokers(client, company):
    _add_party(client, "V2 Txn Customer")
    _add_party(client, "V2 Txn Broker", party_type="Broker")
    _add_quality(client, "V2 Txn Item")

    r = client.get("/transactions")
    html = r.data.decode()
    assert '"name": "V2 Txn Customer"' in html
    assert '"name": "V2 Txn Item"' in html
    # brokers is filtered server-side to party_type='Broker' only
    assert html.count('"name": "V2 Txn Broker"') >= 1
    # quick-add wiring for both comboboxes, so a new party/item can be
    # added without leaving this form (see /parties/quick-add,
    # /quality/quick-add)
    assert 'partyQuickAddUrl: "/parties/quick-add"' in html
    assert 'itemQuickAddUrl: "/quality/quick-add"' in html


def test_parties_quick_add_creates_a_party_and_returns_it_as_json(client, company):
    r = client.post("/parties/quick-add", data={"name": "V2 Quick Party", "party_type": "Supplier"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert data["name"] == "V2 Quick Party"
    assert data["meta"] == "Supplier"

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT party_type, is_gl FROM parties WHERE id = ?", (data["id"],))
    row = cur.fetchone()
    conn.close()
    assert row == ("Supplier", 0)


def test_parties_quick_add_defaults_to_customer(client, company):
    r = client.post("/parties/quick-add", data={"name": "V2 Quick Party Default"})
    assert r.get_json()["meta"] == "Customer"


def test_parties_quick_add_rejects_missing_name(client, company):
    r = client.post("/parties/quick-add", data={})
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_parties_quick_add_rejects_duplicate_name(client, company):
    _add_party(client, "V2 Quick Dup")
    r = client.post("/parties/quick-add", data={"name": "V2 Quick Dup"})
    assert r.status_code == 400
    assert "already exists" in r.get_json()["error"]


def test_transactions_saved_banner_and_recent_list_after_save(client, company):
    party_id = _add_party(client, "V2 Txn Customer 2")
    quality_id = _add_quality(client, "V2 Txn Item 2", sale_rate=250)

    r = client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "4", "rate": "250", "date": date.today().isoformat(), "mode": "Cash",
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"amount": 1000.0' in html
    assert "savedVoucher:" in html
    assert '"voucher": "INV-000001"' in html or "INV-00000" in html


def test_transaction_signature_data_round_trips_through_the_real_form(client, company):
    """Doesn't drive a browser - just confirms the server side of the fix:
    a POST carrying signature_data alongside the rest of the fields
    saves it correctly, which is what the fixed single-<form> wizard now
    actually manages to send (the pre-fix version never got this far)."""
    party_id = _add_party(client, "V2 Sig Customer")
    quality_id = _add_quality(client, "V2 Sig Item")
    fake_signature = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAE="

    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "1", "rate": "100", "date": date.today().isoformat(), "mode": "Cash",
        "signature_data": fake_signature,
    })

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT signature_data FROM transactions WHERE party_id = ?", (party_id,))
    row = cur.fetchone()
    conn.close()
    assert row[0] == fake_signature
