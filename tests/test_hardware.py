"""Hardware vertical: the 7 extra features built on top of Kiryana
parity - item variants, customer-specific pricing, credit limits,
quotations, and smarter reorder suggestions."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def test_item_variant_linked_to_parent(company):
    parent_id = db.hardware_add_item("Paint Bucket", "pcs", 500, 650, 20)
    variant_id = db.hardware_add_item("Paint Bucket - Red", "pcs", 500, 650, 10,
                                       parent_item_id=parent_id, variant_name="Red")

    parents = db.hardware_list_parent_items()
    assert any(p["id"] == parent_id for p in parents)

    items = db.hardware_list_items()
    variant = next(i for i in items if i["id"] == variant_id)
    assert variant["parent_item_id"] == parent_id
    assert variant["variant_name"] == "Red"


def test_customer_specific_price_overrides_standard_rate(company):
    item_id = db.hardware_add_item("Cement Bag", "bag", 700, 900, 100)
    party_id = db.hardware_add_party("Contractor Customer", "0333", "Customer", 0)

    db.hardware_set_customer_price(party_id, item_id, 850)

    price_map = db.hardware_all_customer_prices_map()
    assert price_map[f"{party_id}_{item_id}"] == 850


def test_credit_limit_is_stored_on_party(company):
    party_id = db.hardware_add_party("Credit Customer", "0344", "Customer", 0, credit_limit=50000)
    party = db.hardware_get_party(party_id)
    assert party["credit_limit"] == 50000


def test_quotation_convert_creates_new_sale_and_reduces_stock(company):
    item_id = db.hardware_add_item("Drill Machine", "pcs", 3000, 4000, 15)
    party_id = db.hardware_add_party("Quote Customer", "0355", "Customer", 0)

    quote_invoice_no = db.hardware_get_next_invoice_no("QUOTATION")
    db.hardware_record_quotation_line(_today(), party_id, item_id, 2, 4000, invoice_no=quote_invoice_no)

    stock_before = next(i for i in db.hardware_list_items() if i["id"] == item_id)["stock_qty"]
    assert stock_before == 15, "a quotation must not touch stock until it's converted"

    sale_invoice_no = db.hardware_convert_quotation(quote_invoice_no, _today())
    assert sale_invoice_no is not None
    # SALE and QUOTATION each have their own independent numbering
    # sequence, so the raw integers can coincide - what must actually
    # differ is the formatted invoice (different prefix).
    assert db.hardware_format_invoice_no("SALE", sale_invoice_no) != \
        db.hardware_format_invoice_no("QUOTATION", quote_invoice_no)

    stock_after = next(i for i in db.hardware_list_items() if i["id"] == item_id)["stock_qty"]
    assert stock_after == 13

    invoices = db.hardware_list_invoices("QUOTATION_CONVERTED", limit=5)
    assert any(i["invoice_no"] == quote_invoice_no for i in invoices), \
        "converted quotation lines should show up as QUOTATION_CONVERTED, not disappear"


def test_split_payment_records_separately_from_sale_amount(company):
    item_id = db.hardware_add_item("Tile Box", "box", 400, 550, 40)
    party_id = db.hardware_add_party("Split Pay Customer", "0366", "Customer", 0)

    db.hardware_record_sale(_today(), party_id, item_id, 5, 550, "Credit")
    db.hardware_record_payment(_today(), party_id, 1000, "Partial payment at time of sale")

    ledger = db.hardware_party_ledger(party_id)
    total_sale = 5 * 550
    assert ledger["closing_balance"] == total_sale - 1000


def test_low_stock_suggested_qty_accounts_for_recent_sales(company):
    item_id = db.hardware_add_item("Wire Roll", "roll", 200, 280, 3, reorder_level=10)
    party_id = db.hardware_add_party("Wire Buyer", "0377", "Customer", 0)
    db.hardware_record_sale(_today(), party_id, item_id, 4, 280, "Cash")

    summary = db.hardware_low_stock_summary()
    row = next(b for b in summary["breakdown"] if b["id"] == item_id)
    # stock_qty is now 3 - 4 = -1; shortfall to reorder_level(10) is 11, plus 4 sold in last 30d
    assert row["sold_30d"] == 4
    assert row["suggested_qty"] == 15
