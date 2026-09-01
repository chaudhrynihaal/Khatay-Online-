"""Core Yarn module coverage: Parties, Quality/Items, and Purchase & Sale
entry (the original, most complex vertical - unlike Kiryana/Hardware its
CRUD lives as inline SQL directly in app.py routes rather than db.py
helper functions, so these tests go through the routes rather than
calling db.* directly, mirroring how a user actually exercises it)."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


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


def test_add_party_and_list(client, company):
    r = client.post("/parties", data={"name": "Yarn Customer A", "party_type": "Customer",
                                       "opening_balance": "0"}, follow_redirects=True)
    assert b"Party added" in r.data
    r2 = client.get("/parties")
    assert b"Yarn Customer A" in r2.data


def test_add_quality_item(client, company):
    r = client.post("/quality", data={"name": "40s Combed Cotton", "sale_rate": "250"}, follow_redirects=True)
    assert b"Item added" in r.data
    r2 = client.get("/quality")
    assert b"40s Combed Cotton" in r2.data


def test_delete_quality_blocked_once_it_has_transactions(client, company):
    party_id = _add_party(client, "Yarn Customer B")
    quality_id = _add_quality(client, "20s Carded")

    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "10", "rate": "100", "date": _today(), "mode": "Cash",
    })

    r = client.post(f"/quality/{quality_id}/delete", follow_redirects=True)
    assert b"transactions recorded against it" in r.data
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM quality WHERE id = ?", (quality_id,))
    assert cur.fetchone()[0] == 1, "item must survive a blocked delete"
    conn.close()


def test_sale_increases_receivable_balance(client, company):
    party_id = _add_party(client, "Yarn Customer C")
    quality_id = _add_quality(client, "30s Combed")

    r = client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "50", "rate": "200", "date": _today(), "mode": "Credit", "credit_days": "30",
    }, follow_redirects=True)
    assert b"Sale saved" in r.data

    balance = db.get_party_balance(party_id)
    assert balance == 50 * 200, "a credit Sale must add qty*rate to the party's receivable balance"


def test_purchase_creates_payable_balance(client, company):
    supplier_id = _add_party(client, "Yarn Supplier A", party_type="Supplier")
    quality_id = _add_quality(client, "16s Open End")

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "80", "date": _today(), "mode": "Credit", "credit_days": "15",
    })

    balance = db.get_party_balance(supplier_id)
    assert balance == -(100 * 80), "a credit Purchase must show as payable (negative balance)"


def test_stock_qty_reflects_purchase_minus_sale(client, company):
    supplier_id = _add_party(client, "Yarn Supplier B", party_type="Supplier")
    customer_id = _add_party(client, "Yarn Customer D")
    quality_id = _add_quality(client, "10s Carded")

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "200", "rate": "70", "date": _today(), "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "60", "rate": "90", "date": _today(), "mode": "Cash",
    })

    assert db.get_stock_qty(quality_id) == 140


def test_voucher_numbering_increments_per_type_independently(client, company):
    party_id = _add_party(client, "Yarn Customer E")
    quality_id = _add_quality(client, "Grey Yarn")

    first_no = db.get_next_voucher_no("SALE")
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "5", "rate": "100", "date": _today(), "mode": "Cash",
    })
    second_no = db.get_next_voucher_no("SALE")
    assert second_no == first_no + 1

    formatted = db.format_voucher_no("SALE", first_no)
    assert formatted == f"INV-{first_no:06d}"
