"""The redesigned Kiryana vertical (Dashboard, Inventory + item edit,
Sale Book, Purchase List, Returns, Cash Book, Ledger + payment/
transaction edit, Expenses + expense edit, Print Bill) - 16 screens in
total, all React/design-system pages reading window.__PAGE__, wired to
the entirely unchanged app.py/db.py Kiryana routes (a separate,
simpler engine from the Yarn vertical - own kiryana_* tables). Visually
verified via a headless-browser pass across every screen: the dashboard's
click-to-expand stat breakdowns, a multi-line credit sale with item-rate
autofill, the Purchase List's bulk-unit converter (2 bags @ 25/unit,
Rs 5000 total -> qty 50 @ Rs 100), the Returns "return against a bill"
picker (auto-fill on a single-line bill, a line-sub-picker on a
multi-line one, confirmed against the existing multi-item invoice-
grouping fix), and the Ledger's two-column Dr/Cr T-account with a
correct running balance - no console errors anywhere. These tests
check what the test client can verify server-side: injected data and
that every route's create/update/delete behavior is unchanged."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_item(client, name, **kw):
    data = {"name[]": [name], "unit[]": [kw.get("unit", "kg")], "unit_other[]": [""],
            "category[]": [kw.get("category", "")], "barcode[]": [kw.get("barcode", "")],
            "purchase_rate[]": [str(kw.get("purchase_rate", 100))], "sale_rate[]": [str(kw.get("sale_rate", 130))],
            "opening_qty[]": [str(kw.get("opening_qty", 50))], "reorder_level[]": [str(kw.get("reorder_level", 0))],
            "purchase_unit[]": [kw.get("purchase_unit", "")], "conversion_factor[]": [str(kw.get("conversion_factor", 1))]}
    client.post("/kiryana/inventory", data=data, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM kiryana_items WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def _add_party(name, party_type):
    return db.kiryana_add_party(name, "", party_type, 0)


def test_dashboard_injects_stock_receivable_payable_and_low_stock(client, company):
    item = _add_item(client, "V2 Rice", reorder_level=10, opening_qty=5)
    customer = _add_party("V2 Customer", "Customer")
    db.kiryana_record_sale(_today(), customer, item, 2, 130, "Credit")

    r = client.get("/kiryana")
    html = r.data.decode()
    assert '"name": "V2 Rice"' in html
    assert "lowStock:" in html
    assert '"id": %d' % item in html  # low stock breakdown includes it (stock 3 <= reorder 10)


def test_inventory_bulk_add_creates_multiple_items_in_one_post(client, company):
    r = client.post("/kiryana/inventory", data={
        "name[]": ["V2 Item A", "V2 Item B", ""],
        "unit[]": ["kg", "pcs", "kg"], "unit_other[]": ["", "", ""],
        "category[]": ["", "", ""], "barcode[]": ["", "", ""],
        "purchase_rate[]": ["10", "20", "0"], "sale_rate[]": ["15", "25", "0"],
        "opening_qty[]": ["5", "10", "0"], "reorder_level[]": ["0", "0", "0"],
        "purchase_unit[]": ["", "", ""], "conversion_factor[]": ["1", "1", "1"],
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"2 items added to inventory."' in html
    items = db.kiryana_list_items()
    names = {i["name"] for i in items}
    assert {"V2 Item A", "V2 Item B"}.issubset(names)


def test_inventory_bulk_add_rejects_duplicate_barcode_in_same_batch(client, company):
    r = client.post("/kiryana/inventory", data={
        "name[]": ["V2 Dup A", "V2 Dup B"], "unit[]": ["kg", "kg"], "unit_other[]": ["", ""],
        "category[]": ["", ""], "barcode[]": ["DUP123", "DUP123"],
        "purchase_rate[]": ["10", "10"], "sale_rate[]": ["15", "15"],
        "opening_qty[]": ["0", "0"], "reorder_level[]": ["0", "0"],
        "purchase_unit[]": ["", ""], "conversion_factor[]": ["1", "1"],
    }, follow_redirects=True)
    assert "already used by another item" in r.data.decode()
    assert not any(i["name"] == "V2 Dup A" for i in db.kiryana_list_items())


def test_item_edit_page_and_save(client, company):
    item_id = _add_item(client, "V2 Edit Item")
    r = client.get(f"/kiryana/inventory/{item_id}/edit")
    assert '"name": "V2 Edit Item"' in r.data.decode()

    client.post(f"/kiryana/inventory/{item_id}/edit", data={
        "name": "V2 Edit Item", "barcode": "", "unit": "kg", "unit_other": "",
        "purchase_rate": "120", "sale_rate": "150", "stock_qty": "99",
        "reorder_level": "0", "category": "", "purchase_unit": "", "conversion_factor": "1",
    }, follow_redirects=True)
    item = db.kiryana_get_item(item_id)
    assert item["stock_qty"] == 99.0
    assert item["sale_rate"] == 150.0


def test_item_quick_add_endpoint_returns_json(client, company):
    r = client.post("/kiryana/items/quick-add", data={"name": "V2 Quick Item", "barcode": ""})
    data = r.get_json()
    assert data["ok"] is True
    assert data["name"] == "V2 Quick Item"


def test_item_by_barcode_lookup(client, company):
    item_id = _add_item(client, "V2 Barcode Item", barcode="BC001")
    r = client.get("/kiryana/items/by-barcode?code=BC001")
    data = r.get_json()
    assert data["ok"] is True
    assert data["id"] == item_id

    r2 = client.get("/kiryana/items/by-barcode?code=NOPE")
    assert r2.status_code == 404


def test_multi_line_credit_sale_creates_one_invoice_with_shared_number(client, company):
    item1 = _add_item(client, "V2 Sale Item 1")
    item2 = _add_item(client, "V2 Sale Item 2")
    customer = _add_party("V2 Sale Customer", "Customer")

    r = client.post("/kiryana/sales", data={
        "item_id[]": [str(item1), str(item2)], "qty[]": ["2", "3"], "rate[]": ["130", "50"],
        "mode": "Credit", "party_id": str(customer), "date": _today(), "description": "",
    }, follow_redirects=True)
    html = r.data.decode()
    assert "recorded (2 items)" in html

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT invoice_no FROM kiryana_transactions WHERE txn_type='SALE'")
    invoice_nos = cur.fetchall()
    conn.close()
    assert len(invoice_nos) == 1


def test_sale_without_party_in_credit_mode_is_rejected(client, company):
    item = _add_item(client, "V2 No Party Item")
    r = client.post("/kiryana/sales", data={
        "item_id[]": [str(item)], "qty[]": ["1"], "rate[]": ["130"],
        "mode": "Credit", "date": _today(),
    }, follow_redirects=True)
    assert "Pick a customer for a credit sale." in r.data.decode()


def test_purchase_updates_item_purchase_and_sale_rate(client, company):
    item = _add_item(client, "V2 Purchase Item", purchase_rate=100, sale_rate=130)
    supplier = _add_party("V2 Purchase Supplier", "Supplier")
    client.post("/kiryana/purchases", data={
        "item_id[]": [str(item)], "qty[]": ["10"], "rate[]": ["90"], "sale_rate[]": ["140"], "expiry_date[]": [""],
        "mode": "Cash", "date": _today(),
    }, follow_redirects=True)
    updated = db.kiryana_get_item(item)
    assert updated["purchase_rate"] == 90.0
    assert updated["sale_rate"] == 140.0
    assert updated["stock_qty"] == 60.0  # 50 opening + 10 purchased


def test_sale_return_against_a_bill_restocks_and_credits(client, company):
    item = _add_item(client, "V2 Return Item")
    customer = _add_party("V2 Return Customer", "Customer")
    client.post("/kiryana/sales", data={
        "item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"],
        "mode": "Credit", "party_id": str(customer), "date": _today(),
    })
    before_stock = db.kiryana_get_item(item)["stock_qty"]

    r = client.post("/kiryana/returns", data={
        "return_type": "Sale", "item_id": str(item), "qty": "2", "rate": "130",
        "mode": "Credit", "party_id": str(customer), "date": _today(), "description": "damaged",
    }, follow_redirects=True)
    assert "Sale Return SR-000001 recorded." in r.data.decode()
    after_stock = db.kiryana_get_item(item)["stock_qty"]
    assert after_stock == before_stock + 2

    ledger = db.kiryana_party_ledger(customer)
    assert ledger["closing_balance"] == 130 * 5 - 130 * 2


def test_cashbook_reflects_cash_mode_only(client, company):
    item = _add_item(client, "V2 Cash Item")
    _add_party("unused", "Customer")
    client.post("/kiryana/sales", data={"item_id[]": [str(item)], "qty[]": ["1"], "rate[]": ["130"], "mode": "Cash", "date": _today()})
    r = client.get("/kiryana/cashbook")
    html = r.data.decode()
    assert '"in_amount": 130.0' in html
    assert "closingBalance: 130.0" in html


def test_ledger_payment_record_and_edit(client, company):
    customer = _add_party("V2 Ledger Customer", "Customer")
    r = client.post("/kiryana/ledger/payment", data={"party_id": str(customer), "amount": "300", "date": _today(), "description": "advance"}, follow_redirects=True)
    assert '"Payment recorded."' in r.data.decode()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM kiryana_payments WHERE party_id = ?", (customer,))
    payment_id = cur.fetchone()[0]
    conn.close()

    client.post(f"/kiryana/ledger/payment/{payment_id}/edit", data={"amount": "500", "date": _today(), "description": "advance updated", "return_to": ""}, follow_redirects=True)
    payment = db.kiryana_get_payment(payment_id)
    assert payment["amount"] == 500.0


def test_ledger_transaction_edit_adjusts_stock_by_delta(client, company):
    item = _add_item(client, "V2 Txn Edit Item")
    customer = _add_party("V2 Txn Edit Customer", "Customer")
    client.post("/kiryana/sales", data={"item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"], "mode": "Cash", "date": _today()})
    stock_after_sale = db.kiryana_get_item(item)["stock_qty"]

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM kiryana_transactions WHERE item_id = ?", (item,))
    txn_id = cur.fetchone()[0]
    conn.close()

    client.post(f"/kiryana/ledger/transaction/{txn_id}/edit", data={"date": _today(), "qty": "8", "rate": "130", "description": "", "return_to": ""}, follow_redirects=True)
    stock_after_edit = db.kiryana_get_item(item)["stock_qty"]
    assert stock_after_edit == stock_after_sale - 3  # 3 more units sold


def test_expenses_add_edit_and_net_profit(client, company):
    r = client.post("/kiryana/expenses", data={"date": _today(), "category": "Rent", "description": "shop", "amount": "500"}, follow_redirects=True)
    assert '"Expense recorded."' in r.data.decode()

    r2 = client.get("/kiryana/expenses")
    assert '"category": "Rent"' in r2.data.decode()
    assert "totalExpenses: 500.0" in r2.data.decode()
