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


def test_zakat_reduces_capital_not_net_profit(client, company):
    """Zakat is a personal draw against capital, not a business expense -
    it must NOT reduce Net Profit (unlike Home/Office Expense), and must
    reduce the Capital Account balance instead."""
    supplier_id = _add_party(client, "Zakat Test Supplier", party_type="Supplier")
    customer_id = _add_party(client, "Zakat Test Customer")
    quality_id = _add_quality(client, "Zakat Test Yarn")
    today = _today()

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "50", "date": today, "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "80", "date": today, "mode": "Cash",
    })
    client.post("/capital-expense", data={"kind": "capital", "direction": "CAPITAL_IN", "amount": "50000", "date": today})
    client.post("/capital-expense", data={"kind": "expense", "category": "Zakat", "amount": "600", "date": today})

    profit = db.get_profit_summary(today, today)
    assert profit["gross_profit"] == (100 * 80) - (100 * 50)
    assert profit["zakat_expense"] == 600  # still reported, just not subtracted below
    assert profit["net_profit"] == profit["gross_profit"]  # unaffected by Zakat

    capital = db.get_capital_summary()
    assert capital["zakat_total"] == 600
    assert capital["total_out"] == 600  # no CAPITAL_OUT recorded, only Zakat
    assert capital["net_capital"] == 50000 - 600


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


def test_brokerage_summary_shows_owed_paid_and_balance(client, company):
    broker_id = _add_party(client, "Summary Broker", party_type="Broker",
                            brokerage_type="percentage", brokerage_rate="2")
    supplier_id = _add_party(client, "Brokered Supplier", party_type="Supplier")
    quality_id = _add_quality(client, "Brokered Yarn")
    today = _today()

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "broker_party_id": str(broker_id), "qty": "100", "rate": "200", "date": today, "mode": "Cash",
    })
    # owed = 2% of (100*200) = 400

    summary = db.get_brokerage_summary(broker_party_id=broker_id)
    assert summary == [{"broker_id": broker_id, "broker_name": "Summary Broker",
                         "owed": 400.0, "paid": 0.0, "balance": 400.0}]

    r = client.post("/reports/brokerage/pay", data={
        "broker_id": str(broker_id), "date": today, "amount": "250", "description": "Partial payment",
    }, follow_redirects=True)
    assert b"Brokerage payment recorded." in r.data

    summary2 = db.get_brokerage_summary(broker_party_id=broker_id)
    assert summary2[0]["paid"] == 250.0
    assert summary2[0]["balance"] == 150.0

    # brokerage stays isolated - paying it must not touch the broker's
    # own party balance, the Cash Book, or the Trial Balance
    assert db.get_party_balance(broker_id) == 0.0


def test_brokerage_pay_rejects_missing_broker_or_bad_amount(client, company):
    r = client.post("/reports/brokerage/pay", data={"amount": "100", "date": _today()}, follow_redirects=True)
    assert b"Pick a broker and enter a valid amount." in r.data

    broker_id = _add_party(client, "Zero Amount Broker", party_type="Broker",
                            brokerage_type="percentage", brokerage_rate="2")
    r2 = client.post("/reports/brokerage/pay", data={
        "broker_id": str(broker_id), "amount": "0", "date": _today(),
    }, follow_redirects=True)
    assert b"Pick a broker and enter a valid amount." in r2.data


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


def test_quality_ledger_overall_shows_running_qty_balance(client, company):
    supplier_id = _add_party(client, "QL Supplier", party_type="Supplier")
    customer_id = _add_party(client, "QL Customer")
    quality_id = _add_quality(client, "QL Item")
    today = _today()

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "50", "date": today, "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "30", "rate": "80", "date": today, "mode": "Cash",
    })

    ledger = db.get_quality_ledger(quality_id)
    assert ledger["item"]["name"] == "QL Item"
    assert len(ledger["rows"]) == 2
    assert ledger["rows"][0]["voucher_type"] == "PURCHASE"
    assert ledger["rows"][0]["balance"] == 100
    assert ledger["rows"][1]["voucher_type"] == "SALE"
    assert ledger["rows"][1]["balance"] == 70
    assert ledger["closing_balance"] == 70


def test_quality_ledger_unknown_item_returns_none(client, company):
    assert db.get_quality_ledger(999999) is None


def test_quality_ledger_summary_by_count_and_by_rate(client, company):
    supplier_id = _add_party(client, "QL Supplier 2", party_type="Supplier")
    customer_id = _add_party(client, "QL Customer 2")
    quality_id = _add_quality(client, "QL Item 2")
    today = _today()

    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "50", "rate": "100", "date": today, "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "PURCHASE", "party_id": str(supplier_id), "quality_id": str(quality_id),
        "qty": "50", "rate": "200", "date": today, "mode": "Cash",
    })
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(customer_id), "quality_id": str(quality_id),
        "qty": "40", "rate": "300", "date": today, "mode": "Cash",
    })

    summary = db.get_quality_ledger_summary()
    row = next(r for r in summary if r["name"] == "QL Item 2")
    assert row["purchased_qty"] == 100
    assert row["sold_qty"] == 40
    assert row["net_qty"] == 60
    assert row["purchase_rate_min"] == 100
    assert row["purchase_rate_max"] == 200
    assert row["purchase_rate_avg"] == 150
    assert row["sale_rate_min"] == row["sale_rate_max"] == row["sale_rate_avg"] == 300


def test_quality_ledger_summary_excludes_items_with_no_activity(client, company):
    _add_quality(client, "QL Untouched Item")
    summary = db.get_quality_ledger_summary()
    assert not any(r["name"] == "QL Untouched Item" for r in summary)
