"""Bulk-add multiple new items to inventory in one submission (Kiryana
and Hardware Inventory pages), as opposed to the pre-existing multi-line
support on the Purchase forms, which records a purchase against items
that already exist."""
import db


def test_kiryana_multi_item_add(client, company):
    before = len(db.kiryana_list_items())
    r = client.post("/kiryana/inventory", data={
        "name[]": ["Item A", "Item B", ""],
        "unit[]": ["kg", "__other__", ""],
        "unit_other[]": ["", "crate", ""],
        "category[]": ["Grocery", "Grocery", ""],
        "barcode[]": ["BC-A", "", ""],
        "purchase_rate[]": ["50", "80", ""],
        "sale_rate[]": ["65", "100", ""],
        "opening_qty[]": ["20", "10", ""],
        "reorder_level[]": ["5", "0", ""],
        "purchase_unit[]": ["", "", ""],
        "conversion_factor[]": ["1", "1", ""],
    }, follow_redirects=True)
    assert r.status_code == 200
    assert b"2 items added" in r.data

    items = db.kiryana_list_items()
    assert len(items) - before == 2
    b = next(i for i in items if i["name"] == "Item B")
    assert b["unit"] == "crate", "an 'Other' unit typed per-row must resolve correctly for that row"


def test_kiryana_multi_item_add_rejects_duplicate_barcode_within_the_same_batch(client, company):
    before = len(db.kiryana_list_items())
    r = client.post("/kiryana/inventory", data={
        "name[]": ["Dup 1", "Dup 2"],
        "barcode[]": ["SAMECODE", "SAMECODE"],
        "unit[]": ["pcs", "pcs"], "unit_other[]": ["", ""], "category[]": ["", ""],
        "purchase_rate[]": ["1", "1"], "sale_rate[]": ["1", "1"], "opening_qty[]": ["0", "0"],
        "reorder_level[]": ["0", "0"], "purchase_unit[]": ["", ""], "conversion_factor[]": ["1", "1"],
    }, follow_redirects=True)
    assert b"already used" in r.data
    assert len(db.kiryana_list_items()) == before, "a rejected batch must add nothing, not just skip the bad row"


def test_hardware_multi_item_add_with_variants(client, company):
    parent_id = db.hardware_add_item("Paint Bucket", "pcs", 500, 650, 0)
    r = client.post("/hardware/inventory", data={
        "name[]": ["Paint - Red", "Paint - Blue"],
        "unit[]": ["pcs", "pcs"], "unit_other[]": ["", ""],
        "category[]": ["Paint", "Paint"], "barcode[]": ["", ""],
        "purchase_rate[]": ["500", "500"], "sale_rate[]": ["650", "650"],
        "opening_qty[]": ["5", "3"], "reorder_level[]": ["0", "0"],
        "purchase_unit[]": ["", ""], "conversion_factor[]": ["1", "1"],
        "parent_item_id[]": [str(parent_id), str(parent_id)],
        "variant_name[]": ["Red", "Blue"],
    }, follow_redirects=True)
    assert b"2 items added" in r.data

    items = db.hardware_list_items()
    red = next(i for i in items if i["name"] == "Paint - Red")
    assert red["parent_item_id"] == parent_id
    assert red["variant_name"] == "Red"
