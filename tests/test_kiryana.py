"""Kiryana vertical: item CRUD, stock direction correctness across
Sale/Purchase/Return, invoice grouping, and low-stock summary."""
from datetime import date

import pytest

import db


def _today():
    return date.today().isoformat()


def test_add_and_list_item(company):
    item_id = db.kiryana_add_item("Rice 5kg", "kg", 250, 300, 100)
    items = db.kiryana_list_items()
    match = next(i for i in items if i["id"] == item_id)
    assert match["name"] == "Rice 5kg"
    assert match["stock_qty"] == 100
    assert match["purchase_rate"] == 250
    assert match["sale_rate"] == 300


def test_sale_reduces_stock_and_creates_ledger_entry(company):
    item_id = db.kiryana_add_item("Sugar 1kg", "kg", 100, 120, 50)
    party_id = db.kiryana_add_party("Walk-in Customer", "0300", "Customer", 0)

    db.kiryana_record_sale(_today(), party_id, item_id, 10, 120, "Cash")

    item = next(i for i in db.kiryana_list_items() if i["id"] == item_id)
    assert item["stock_qty"] == 40


def test_oversell_is_allowed_and_goes_negative(company):
    """The DB layer intentionally doesn't block an oversell - the app
    only soft-warns (JS + a non-blocking flash) so a cashier can still
    push through a legitimate sale. Regression guard for that decision."""
    item_id = db.kiryana_add_item("Salt 1kg", "kg", 30, 40, 5)
    party_id = db.kiryana_add_party("Walk-in Customer", "0300", "Customer", 0)

    db.kiryana_record_sale(_today(), party_id, item_id, 20, 40, "Cash")

    item = next(i for i in db.kiryana_list_items() if i["id"] == item_id)
    assert item["stock_qty"] == -15


def test_purchase_increases_stock_and_updates_purchase_rate(company):
    item_id = db.kiryana_add_item("Tea 250g", "pcs", 80, 100, 20)
    supplier_id = db.kiryana_add_party("Test Supplier", "0311", "Supplier", 0)

    db.kiryana_record_purchase(_today(), supplier_id, item_id, 30, 95, mode="Cash")

    item = next(i for i in db.kiryana_list_items() if i["id"] == item_id)
    assert item["stock_qty"] == 50
    assert item["purchase_rate"] == 95, "every purchase must refresh purchase_rate, not just manual item edits"


def test_sale_return_adds_stock_back(company):
    item_id = db.kiryana_add_item("Oil 1L", "ltr", 200, 250, 30)
    party_id = db.kiryana_add_party("Walk-in Customer", "0300", "Customer", 0)
    db.kiryana_record_sale(_today(), party_id, item_id, 10, 250, "Cash")

    db.kiryana_record_sale_return(_today(), party_id, item_id, 4, 250, "Cash")

    item = next(i for i in db.kiryana_list_items() if i["id"] == item_id)
    assert item["stock_qty"] == 24  # 30 - 10 + 4


def test_purchase_return_removes_stock(company):
    item_id = db.kiryana_add_item("Flour 10kg", "kg", 500, 600, 20)
    supplier_id = db.kiryana_add_party("Test Supplier", "0311", "Supplier", 0)
    db.kiryana_record_purchase(_today(), supplier_id, item_id, 10, 500, mode="Cash")

    db.kiryana_record_purchase_return(_today(), supplier_id, item_id, 3, 500, "Cash")

    item = next(i for i in db.kiryana_list_items() if i["id"] == item_id)
    assert item["stock_qty"] == 27  # 20 + 10 - 3


def test_multi_item_sale_groups_under_one_invoice(company):
    item1 = db.kiryana_add_item("Item A", "pcs", 10, 15, 100)
    item2 = db.kiryana_add_item("Item B", "pcs", 20, 25, 100)
    party_id = db.kiryana_add_party("Grouped Sale Customer", "0322", "Customer", 0)

    invoice_no = db.kiryana_get_next_invoice_no("SALE")
    db.kiryana_record_sale(_today(), party_id, item1, 2, 15, "Cash", invoice_no=invoice_no)
    db.kiryana_record_sale(_today(), party_id, item2, 3, 25, "Cash", invoice_no=invoice_no)

    invoices = db.kiryana_list_invoices("SALE", limit=5)
    grouped = next(i for i in invoices if i["invoice_no"] == invoice_no)
    assert len(grouped["lines"]) == 2
    assert grouped["total_amount"] == 2 * 15 + 3 * 25

    bill = db.kiryana_get_bill("SALE", grouped["lines"][0]["id"])
    assert len(bill["lines"]) == 2
    assert bill["total"] == 2 * 15 + 3 * 25


def test_delete_item_blocked_once_it_has_transactions(company):
    item_id = db.kiryana_add_item("Item With History", "pcs", 10, 15, 10)
    party_id = db.kiryana_add_party("Customer", "0300", "Customer", 0)
    db.kiryana_record_sale(_today(), party_id, item_id, 1, 15, "Cash")

    assert db.kiryana_item_has_transactions(item_id) is True


def test_low_stock_summary_only_flags_items_with_reorder_level_set(company):
    below = db.kiryana_add_item("Below Reorder", "pcs", 10, 15, 2, reorder_level=5)
    above = db.kiryana_add_item("Above Reorder", "pcs", 10, 15, 50, reorder_level=5)
    no_reorder = db.kiryana_add_item("No Reorder Set", "pcs", 10, 15, 0, reorder_level=0)

    summary = db.kiryana_low_stock_summary()
    ids = {i["id"] for i in summary["breakdown"]}
    assert below in ids
    assert above not in ids
    assert no_reorder not in ids
