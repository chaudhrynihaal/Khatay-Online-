"""Opening-stock-aware purchase rate blending (db.get_weighted_avg_purchase_rate).
An item's Purchase Rate field (added at add/edit time - see app.py's
quality()/edit_quality()) only prices its Opening Stock Qty; the rate
this function returns is the quantity-weighted average across that
opening stock and every real Purchase entry, so Stock/COGS/Profit
reports value opening stock correctly instead of at Rs 0."""
from datetime import date

import db


def _add_quality(client, name, sale_rate=100, opening_balance=0, purchase_rate=0):
    client.post("/quality", data={
        "name": name, "sale_rate": str(sale_rate),
        "opening_balance": str(opening_balance), "purchase_rate": str(purchase_rate),
    }, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def _add_party(client, name, party_type="Supplier"):
    client.post("/parties", data={"name": name, "party_type": party_type, "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_no_opening_stock_and_no_purchases_gives_zero_rate(client, company):
    item_id = _add_quality(client, "Stock Val Item A")
    assert db.get_weighted_avg_purchase_rate(item_id) == 0.0


def test_priced_opening_stock_with_no_purchases_uses_the_opening_rate(client, company):
    item_id = _add_quality(client, "Stock Val Item B", opening_balance=50, purchase_rate=120)
    assert db.get_weighted_avg_purchase_rate(item_id) == 120.0


def test_unpriced_opening_stock_is_excluded_not_treated_as_free(client, company):
    """Opening stock added before this field existed (or just left at 0)
    must NOT drag the average down toward 0 once real purchases exist -
    it's excluded from the blend entirely, matching the old behavior."""
    item_id = _add_quality(client, "Stock Val Item C", opening_balance=50, purchase_rate=0)
    supplier = _add_party(client, "Stock Val Supplier C")
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier), "quality_id": str(item_id),
        "qty": "10", "rate": "200", "date": date.today().isoformat(), "mode": "Cash",
    })
    assert db.get_weighted_avg_purchase_rate(item_id) == 200.0


def test_priced_opening_stock_blends_with_real_purchases(client, company):
    item_id = _add_quality(client, "Stock Val Item D", opening_balance=50, purchase_rate=100)
    supplier = _add_party(client, "Stock Val Supplier D")
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier), "quality_id": str(item_id),
        "qty": "50", "rate": "200", "date": date.today().isoformat(), "mode": "Cash",
    })
    # (50 * 100 + 50 * 200) / 100 = 150
    assert db.get_weighted_avg_purchase_rate(item_id) == 150.0


def test_editing_an_item_to_add_a_purchase_rate_brings_its_opening_stock_into_the_blend(client, company):
    item_id = _add_quality(client, "Stock Val Item E", opening_balance=20, purchase_rate=0)
    supplier = _add_party(client, "Stock Val Supplier E")
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier), "quality_id": str(item_id),
        "qty": "20", "rate": "300", "date": date.today().isoformat(), "mode": "Cash",
    })
    assert db.get_weighted_avg_purchase_rate(item_id) == 300.0  # opening still excluded, unpriced

    client.post(f"/quality/{item_id}/edit", data={
        "name": "Stock Val Item E", "sale_rate": "0",
        "opening_balance": "20", "purchase_rate": "100",
    })
    # (20 * 100 + 20 * 300) / 40 = 200
    assert db.get_weighted_avg_purchase_rate(item_id) == 200.0
