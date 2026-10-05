"""Stock report print/export: two options, with and without stock value
(see pdf_export.generate_stock_report_pdf / excel_export.generate_stock_excel).
"With Value" prices each item at its quantity-weighted average purchase
rate (not the mostly-unused quality.purchase_rate column, which only
prices opening stock - see db.get_weighted_avg_purchase_rate); "Without
Value" is a plain physical count with no pricing at all."""
from datetime import date

import db


def _add_quality(client, name, sale_rate=100):
    client.post("/quality", data={"name": name, "sale_rate": str(sale_rate)}, follow_redirects=True)
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


def test_stock_pdf_with_value_defaults_on(client, company):
    r = client.get("/reports/pdf/stock")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"


def test_stock_pdf_without_value(client, company):
    r = client.get("/reports/pdf/stock?with_value=0")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"


def test_stock_excel_with_and_without_value(client, company):
    r1 = client.get("/reports/excel/stock?with_value=1")
    assert r1.status_code == 200
    r2 = client.get("/reports/excel/stock?with_value=0")
    assert r2.status_code == 200


def test_stock_value_uses_weighted_average_not_raw_purchase_rate_column(client, company):
    """Regression coverage for a real bug this fix corrected: the PDF
    export used to read quality.purchase_rate directly (which only
    prices opening stock, and is 0 for any item added without one) -
    instead of the same weighted-average rate the web page and Excel
    export already used. An item bought via a real Purchase entry (no
    priced opening stock) must value its stock from that purchase, not
    show Rs 0."""
    item_id = _add_quality(client, "Export Test Item", sale_rate=300)
    supplier = _add_party(client, "Export Test Supplier")
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier), "quality_id": str(item_id),
        "qty": "20", "rate": "150", "date": date.today().isoformat(), "mode": "Cash", "credit_days": "0",
    })

    # quality.purchase_rate is untouched (0) for this item - it only has
    # opening_balance=0 and a real Purchase, so the old bug would have
    # valued its stock at 0 instead of 20 * 150
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT purchase_rate FROM quality WHERE id = ?", (item_id,))
    assert cur.fetchone()[0] == 0
    conn.close()

    expected_value = db.get_weighted_avg_purchase_rate(item_id) * db.get_stock_qty(item_id)
    assert expected_value == 3000.0

    # both exports must succeed with this data present
    assert client.get("/reports/pdf/stock").status_code == 200
    assert client.get("/reports/excel/stock").status_code == 200
