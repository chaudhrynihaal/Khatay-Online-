"""The redesigned Hardware vertical (Dashboard, Inventory + item edit,
Sale Book, Purchase List, Parties + party edit, Quotations, Returns,
Cash Book, Ledger + payment/transaction edit, Expenses + expense edit,
Print Bill) - 15 screens, all React/design-system pages reading
window.__PAGE__, wired to the entirely unchanged app.py/db.py Hardware
routes. Structurally this vertical is Kiryana plus five delta features:
item variants (parent_item_id/variant_name folded into display_name),
a standalone Customers & Suppliers page, per-customer negotiated
pricing (auto-applied on the Sale Book), a credit-limit soft-warning,
split payment on a Credit sale, and Quotations (a stock/ledger-inert
multi-line entry that converts into a real Sale on demand). Visually
verified via a headless-browser pass across every screen with a full
dataset (a parent+variant item, a customer with both a credit limit
and a special price, a supplier, a sale, a purchase, a payment, an
expense, and a quotation) - no console errors anywhere, and the
Quotations screen's Convert-to-Sale flow confirmed end to end. These
tests check what the test client can verify server-side: injected data
and that every route's create/update/delete/convert behavior is
unchanged from before the redesign."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_item(client, name, **kw):
    data = {"name[]": [name], "unit[]": [kw.get("unit", "pcs")], "unit_other[]": [""],
            "category[]": [kw.get("category", "")], "barcode[]": [kw.get("barcode", "")],
            "purchase_rate[]": [str(kw.get("purchase_rate", 100))], "sale_rate[]": [str(kw.get("sale_rate", 130))],
            "opening_qty[]": [str(kw.get("opening_qty", 50))], "reorder_level[]": [str(kw.get("reorder_level", 0))],
            "purchase_unit[]": [kw.get("purchase_unit", "")], "conversion_factor[]": [str(kw.get("conversion_factor", 1))],
            "parent_item_id[]": [str(kw["parent_item_id"]) if kw.get("parent_item_id") else ""],
            "variant_name[]": [kw.get("variant_name", "")]}
    client.post("/hardware/inventory", data=data, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM hardware_items WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def _add_party(name, party_type, **kw):
    return db.hardware_add_party(name, "", party_type, kw.get("opening_balance", 0), kw.get("credit_limit", 0), kw.get("gst_number"))


def test_dashboard_injects_open_quotations_and_tax_settings(client, company):
    r = client.get("/hardware")
    html = r.data.decode()
    assert "openQuotationsCount: 0" in html
    assert "taxRate: 0.0" in html


def test_inventory_bulk_add_supports_variant_fields(client, company):
    parent_id = _add_item(client, "V2 HW Screws")
    variant_id = _add_item(client, "V2 HW Screws Small", parent_item_id=parent_id, variant_name="1 inch")
    items = db.hardware_list_items()
    variant = next(i for i in items if i["id"] == variant_id)
    assert variant["parent_item_id"] == parent_id
    assert variant["display_name"] == "V2 HW Screws — 1 inch"


def test_item_edit_can_set_and_clear_variant_relationship(client, company):
    parent_id = _add_item(client, "V2 HW Parent")
    child_id = _add_item(client, "V2 HW Child")
    client.post(f"/hardware/inventory/{child_id}/edit", data={
        "name": "V2 HW Child", "barcode": "", "unit": "pcs", "unit_other": "",
        "purchase_rate": "100", "sale_rate": "130", "stock_qty": "50", "reorder_level": "0",
        "category": "", "purchase_unit": "", "conversion_factor": "1",
        "parent_item_id": str(parent_id), "variant_name": "Large",
    }, follow_redirects=True)
    item = db.hardware_get_item(child_id)
    assert item["parent_item_id"] == parent_id
    assert item["variant_name"] == "Large"


def test_item_cannot_be_its_own_variant_parent(client, company):
    item_id = _add_item(client, "V2 HW Self Parent")
    r = client.post(f"/hardware/inventory/{item_id}/edit", data={
        "name": "V2 HW Self Parent", "barcode": "", "unit": "pcs", "unit_other": "",
        "purchase_rate": "100", "sale_rate": "130", "stock_qty": "50", "reorder_level": "0",
        "category": "", "purchase_unit": "", "conversion_factor": "1",
        "parent_item_id": str(item_id), "variant_name": "X",
    }, follow_redirects=True)
    assert "can\\u0027t be its own variant parent" in r.data.decode()


def test_credit_sale_with_split_payment_records_partial_payment(client, company):
    item = _add_item(client, "V2 HW Sale Item")
    customer = _add_party("V2 HW Sale Customer", "Customer")
    client.post("/hardware/sales", data={
        "item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"],
        "mode": "Credit", "party_id": str(customer), "date": _today(),
        "amount_paid_now": "300",
    }, follow_redirects=True)

    ledger = db.hardware_party_ledger(customer)
    assert ledger["closing_balance"] == 650 - 300  # 5*130 sale minus the 300 paid now

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hardware_payments WHERE party_id = ?", (customer,))
    assert cur.fetchone()[0] == 1
    conn.close()


def test_credit_sale_over_credit_limit_flashes_warning_but_still_saves(client, company):
    item = _add_item(client, "V2 HW Limit Item")
    customer = _add_party("V2 HW Limit Customer", "Customer", credit_limit=100)
    r = client.post("/hardware/sales", data={
        "item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"],
        "mode": "Credit", "party_id": str(customer), "date": _today(),
    }, follow_redirects=True)
    assert "over their credit limit" in r.data.decode()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE party_id = ?", (customer,))
    assert cur.fetchone()[0] == 1  # not blocked, just warned
    conn.close()


def test_customer_special_price_is_injected_into_sales_page_map(client, company):
    item = _add_item(client, "V2 HW Priced Item")
    customer = _add_party("V2 HW Priced Customer", "Customer")
    db.hardware_set_customer_price(customer, item, 75)

    r = client.get("/hardware/sales")
    html = r.data.decode()
    assert f'"{customer}_{item}": 75.0' in html


def test_parties_page_lists_customers_with_balance_and_credit_limit(client, company):
    item = _add_item(client, "V2 HW Parties Item")
    customer = _add_party("V2 HW Parties Customer", "Customer", credit_limit=500)
    client.post("/hardware/sales", data={"item_id[]": [str(item)], "qty[]": ["1"], "rate[]": ["130"], "mode": "Credit", "party_id": str(customer), "date": _today()})

    r = client.get("/hardware/parties?type=Customer")
    html = r.data.decode()
    assert '"name": "V2 HW Parties Customer"' in html
    assert '"credit_limit": 500.0' in html
    assert '"balance": 130.0' in html


def test_party_edit_updates_credit_limit_and_gst(client, company):
    customer = _add_party("V2 HW Edit Customer", "Customer")
    r = client.post(f"/hardware/parties/{customer}/edit", data={
        "name": "V2 HW Edit Customer", "phone": "0300", "opening_balance": "0",
        "credit_limit": "2000", "gst_number": "GST-999",
    }, follow_redirects=True)
    assert '"Party updated."' in r.data.decode()
    party = db.hardware_get_party(customer)
    assert party["credit_limit"] == 2000.0
    assert party["gst_number"] == "GST-999"


def test_add_and_delete_customer_special_price(client, company):
    item = _add_item(client, "V2 HW Special Item")
    customer = _add_party("V2 HW Special Customer", "Customer")
    r = client.post(f"/hardware/parties/{customer}/prices/add", data={"item_id": str(item), "rate": "88"}, follow_redirects=True)
    assert '"Special price saved."' in r.data.decode()

    prices = db.hardware_list_customer_prices(customer)
    assert len(prices) == 1
    price_id = prices[0]["id"]

    r2 = client.post(f"/hardware/parties/{customer}/prices/{price_id}/delete", follow_redirects=True)
    assert '"Special price removed."' in r2.data.decode()
    assert db.hardware_list_customer_prices(customer) == []


def test_party_delete_blocked_when_has_activity(client, company):
    item = _add_item(client, "V2 HW Activity Item")
    customer = _add_party("V2 HW Activity Customer", "Customer")
    client.post("/hardware/sales", data={"item_id[]": [str(item)], "qty[]": ["1"], "rate[]": ["130"], "mode": "Cash", "party_id": str(customer), "date": _today()})
    r = client.post(f"/hardware/parties/{customer}/delete", follow_redirects=True)
    assert "Can\\u0027t delete a party with sales" in r.data.decode()


def test_quotation_does_not_touch_stock_or_ledger(client, company):
    item = _add_item(client, "V2 HW Quote Item", opening_qty=50)
    customer = _add_party("V2 HW Quote Customer", "Customer")
    r = client.post("/hardware/quotations", data={
        "item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"],
        "party_id": str(customer), "date": _today(), "description": "",
    }, follow_redirects=True)
    assert "won\\u0027t affect stock or the ledger" in r.data.decode()

    stock_item = db.hardware_get_item(item)
    assert stock_item["stock_qty"] == 50.0  # unchanged
    ledger = db.hardware_party_ledger(customer)
    assert ledger["closing_balance"] == 0.0  # unchanged


def test_quotation_conversion_creates_sale_and_flips_line_type(client, company):
    item = _add_item(client, "V2 HW Convert Item", opening_qty=50)
    customer = _add_party("V2 HW Convert Customer", "Customer")
    client.post("/hardware/quotations", data={
        "item_id[]": [str(item)], "qty[]": ["5"], "rate[]": ["130"],
        "party_id": str(customer), "date": _today(),
    })
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT invoice_no FROM hardware_transactions WHERE txn_type = 'QUOTATION'")
    invoice_no = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/hardware/quotations/{invoice_no}/convert", follow_redirects=True)
    assert "Converted to Sale" in r.data.decode()

    stock_item = db.hardware_get_item(item)
    assert stock_item["stock_qty"] == 45.0  # now deducted, since it's a real sale
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE txn_type = 'QUOTATION_CONVERTED'")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE txn_type = 'SALE'")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE txn_type = 'QUOTATION'")
    assert cur.fetchone()[0] == 0  # no longer "open"
    conn.close()


def test_expenses_and_net_profit(client, company):
    r = client.post("/hardware/expenses", data={"date": _today(), "category": "Rent", "description": "shop", "amount": "500"}, follow_redirects=True)
    assert '"Expense recorded."' in r.data.decode()
    r2 = client.get("/hardware/expenses")
    assert "totalExpenses: 500.0" in r2.data.decode()
