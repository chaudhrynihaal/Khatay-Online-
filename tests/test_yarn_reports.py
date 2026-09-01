"""Capital & Expense entry, brokerage calculation, and the Profit report -
the parts of Yarn that read across many transactions rather than
recording one."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_party(client, name, party_type="Customer", **kwargs):
    data = {"name": name, "party_type": party_type, "opening_balance": "0"}
    data.update({k: str(v) for k, v in kwargs.items()})
    client.post("/parties", data=data, follow_redirects=True)
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


def test_expense_recorded_against_correct_gl_category(client, company):
    r = client.post("/capital-expense", data={
        "kind": "expense", "category": "Office", "amount": "1500",
        "date": _today(), "description": "Office rent",
    }, follow_redirects=True)
    assert b"Expense saved" in r.data

    office_id = db.get_gl_party_id(db.GL_OFFICE_EXPENSE)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM transactions WHERE voucher_type = 'EXPENSE' AND party_id = ?",
                (office_id,))
    total = cur.fetchone()[0]
    conn.close()
    assert total == 1500


def test_capital_in_and_out_summary(client, company):
    client.post("/capital-expense", data={
        "kind": "capital", "direction": "CAPITAL_IN", "amount": "50000",
        "date": _today(), "description": "Owner investment",
    })
    client.post("/capital-expense", data={
        "kind": "capital", "direction": "CAPITAL_OUT", "amount": "10000",
        "date": _today(), "description": "Owner withdrawal",
    })

    summary = db.get_capital_summary()
    assert summary["total_in"] == 50000
    assert summary["total_out"] == 10000
    assert summary["net_capital"] == 40000


def test_brokerage_percentage_calculation(client, company):
    broker_id = _add_party(client, "Test Broker", party_type="Broker",
                            brokerage_type="percentage", brokerage_rate="2")
    assert db.calculate_brokerage(broker_id, qty=100, amount=20000) == 400  # 2% of 20000


def test_brokerage_per_unit_calculation(client, company):
    broker_id = _add_party(client, "Test Broker Per Unit", party_type="Broker",
                            brokerage_type="per_unit", brokerage_rate="5")
    assert db.calculate_brokerage(broker_id, qty=100, amount=20000) == 500  # 5/unit * 100


def test_brokerage_report_includes_sale_with_broker_assigned(client, company):
    broker_id = _add_party(client, "Report Broker", party_type="Broker",
                            brokerage_type="percentage", brokerage_rate="1")
    customer_id = _add_party(client, "Brokered Sale Customer")
    quality_id = _add_quality(client, "Brokered Yarn")

    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "40", "rate": "150", "date": _today(), "mode": "Cash",
        "broker_party_id": str(broker_id),
    })

    report = db.get_brokerage_report(broker_party_id=broker_id)
    assert len(report) == 1
    assert report[0]["brokerage"] == round(40 * 150 * 0.01, 2)


def test_profit_summary_sales_minus_cogs_minus_expenses(client, company):
    supplier_id = _add_party(client, "Profit Test Supplier", party_type="Supplier")
    customer_id = _add_party(client, "Profit Test Customer")
    quality_id = _add_quality(client, "Profit Test Yarn")
    today = _today()

    # Buy 100 units @ 50, sell 100 units @ 80 - all in one day so opening
    # stock value is 0 and closing stock value is also 0 (nothing left).
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "50", "date": today, "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "80", "date": today, "mode": "Cash",
    })
    client.post("/capital-expense", data={
        "kind": "expense", "category": "Home", "amount": "300", "date": today,
    })

    summary = db.get_profit_summary(today, today)
    assert summary["total_sales"] == 100 * 80
    assert summary["total_purchases"] == 100 * 50
    assert summary["gross_profit"] == (100 * 80) - (100 * 50)
    assert summary["net_profit"] == summary["gross_profit"] - 300
