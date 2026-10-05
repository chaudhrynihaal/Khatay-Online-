"""Editing and deleting existing entries. Yarn derives stock/balance from
SUM() over the transactions table at read time, so editing/deleting a row
there needs no special reversal bookkeeping - it's correct automatically.
Kiryana/Hardware store stock_qty as a running column instead, so their
edit/delete need to explicitly reverse the qty delta - see
_STOCK_INCREASING_TXN_TYPES in db.py. That asymmetry is exactly why both
get covered here, not just one."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type,
                                   "opening_balance": "0"}, follow_redirects=True)
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


# --- Yarn: derived balance/stock, no explicit reversal needed ---
def test_yarn_editing_a_sale_qty_updates_derived_balance(client, company):
    party_id = _add_party(client, "Edit Test Customer")
    quality_id = _add_quality(client, "Edit Test Yarn")
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "10", "rate": "100", "date": _today(), "mode": "Credit",
    })
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'SALE' ORDER BY id DESC LIMIT 1")
    txn_id = cur.fetchone()[0]
    conn.close()
    assert db.get_party_balance(party_id) == 1000

    client.post(f"/transaction/{txn_id}/edit", data={
        "date": _today(), "do_no": "", "party_id": str(party_id), "broker": "",
        "quality_id": str(quality_id), "qty": "15", "rate": "100", "mode": "Credit",
        "cheque_no": "", "description": "", "credit_days": "0",
    })
    assert db.get_party_balance(party_id) == 1500


def test_yarn_deleting_a_purchase_removes_its_effect_on_stock_and_balance(client, company):
    supplier_id = _add_party(client, "Delete Test Supplier", party_type="Supplier")
    quality_id = _add_quality(client, "Delete Test Yarn")
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "50", "rate": "80", "date": _today(), "mode": "Credit",
    })
    assert db.get_stock_qty(quality_id) == 50
    assert db.get_party_balance(supplier_id) == -4000

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM transactions WHERE voucher_type = 'PURCHASE' ORDER BY id DESC LIMIT 1")
    txn_id = cur.fetchone()[0]
    conn.close()

    client.post(f"/transaction/{txn_id}/delete")
    assert db.get_stock_qty(quality_id) == 0
    assert db.get_party_balance(supplier_id) == 0


# --- Kiryana: stock_qty is a running column, edit/delete must reverse it ---
def test_kiryana_editing_sale_qty_adjusts_stock_by_the_delta(client, company):
    item_id = db.kiryana_add_item("Edit Item", "pcs", 10, 20, 100)
    party_id = db.kiryana_add_party("Edit Customer", "", "Customer", 0)
    db.kiryana_record_sale(_today(), party_id, item_id, 10, 20, "Cash")
    assert db.kiryana_get_item(item_id)["stock_qty"] == 90

    invs = db.kiryana_list_invoices("SALE", limit=1)
    txn_id = invs[0]["lines"][0]["id"]

    r = client.post(f"/kiryana/ledger/transaction/{txn_id}/edit", data={
        "date": _today(), "qty": "25", "rate": "20", "description": "",
    }, follow_redirects=True)
    assert b"Entry updated" in r.data
    # sold 10 originally (stock 90), now sold 25 instead -> stock 75
    assert db.kiryana_get_item(item_id)["stock_qty"] == 75


def test_kiryana_deleting_a_purchase_reverses_stock_increase(client, company):
    item_id = db.kiryana_add_item("Delete Item", "pcs", 10, 20, 50)
    supplier_id = db.kiryana_add_party("Delete Supplier", "", "Supplier", 0)
    db.kiryana_record_purchase(_today(), supplier_id, item_id, 30, 10, mode="Cash")
    assert db.kiryana_get_item(item_id)["stock_qty"] == 80

    invs = db.kiryana_list_invoices("PURCHASE", limit=1)
    txn_id = invs[0]["lines"][0]["id"]

    r = client.post(f"/kiryana/ledger/transaction/{txn_id}/delete", follow_redirects=True)
    assert b"Entry deleted" in r.data
    assert db.kiryana_get_item(item_id)["stock_qty"] == 50


def test_kiryana_deleting_a_sale_return_reverses_its_stock_increase(client, company):
    """SALE_RETURN is a stock-INCREASING type - deleting one must
    subtract that stock back out, not add more (the exact bug class
    _STOCK_INCREASING_TXN_TYPES exists to get right)."""
    item_id = db.kiryana_add_item("Return Delete Item", "pcs", 10, 20, 20)
    party_id = db.kiryana_add_party("Return Delete Customer", "", "Customer", 0)
    db.kiryana_record_sale_return(_today(), party_id, item_id, 5, 20, "Cash")
    assert db.kiryana_get_item(item_id)["stock_qty"] == 25

    invs = db.kiryana_list_invoices("SALE_RETURN", limit=1)
    txn_id = invs[0]["lines"][0]["id"]
    client.post(f"/kiryana/ledger/transaction/{txn_id}/delete")
    assert db.kiryana_get_item(item_id)["stock_qty"] == 20


# --- Hardware: same stock-column pattern, verified independently since
# it's a separately-duplicated code path, not a shared implementation ---
def test_hardware_editing_purchase_qty_adjusts_stock_by_the_delta(client, company):
    item_id = db.hardware_add_item("Edit HW Item", "pcs", 100, 150, 50)
    supplier_id = db.hardware_add_party("Edit HW Supplier", "", "Supplier", 0)
    db.hardware_record_purchase(_today(), supplier_id, item_id, 10, 100, mode="Cash")
    assert db.hardware_get_item(item_id)["stock_qty"] == 60

    invs = db.hardware_list_invoices("PURCHASE", limit=1)
    txn_id = invs[0]["lines"][0]["id"]

    client.post(f"/hardware/ledger/transaction/{txn_id}/edit", data={
        "date": _today(), "qty": "20", "rate": "100", "description": "",
    })
    # bought 10 originally (stock 60), now 20 instead -> stock 70
    assert db.hardware_get_item(item_id)["stock_qty"] == 70


def test_hardware_deleting_a_sale_reverses_stock_decrease(client, company):
    item_id = db.hardware_add_item("Delete HW Item", "pcs", 100, 150, 40)
    party_id = db.hardware_add_party("Delete HW Customer", "", "Customer", 0)
    db.hardware_record_sale(_today(), party_id, item_id, 8, 150, "Cash")
    assert db.hardware_get_item(item_id)["stock_qty"] == 32

    invs = db.hardware_list_invoices("SALE", limit=1)
    txn_id = invs[0]["lines"][0]["id"]
    client.post(f"/hardware/ledger/transaction/{txn_id}/delete")
    assert db.hardware_get_item(item_id)["stock_qty"] == 40
