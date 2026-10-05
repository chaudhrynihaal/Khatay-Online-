"""The 8 redesigned Reports screens (Party Ledger, Receivable Ledger,
Payable Ledger, Brokerage, Cash Book, Profit & Capital, Stock, Trial
Balance). All 8 routes are read-only (GET) and were untouched by this
migration - only their templates changed, from server-rendered HTML
tables to a React shell reading window.__PAGE__. Visually verified via
a headless-browser pass with a full purchase/sale/receipt/payment/
brokerage dataset (confirmed the grouped-with-subtotal layout, the
Cash Book's balanced two-sided T-account, the Party Ledger's running
balance, and accurate totals throughout - no console errors on any of
the 8). These tests check what the test client can verify server-side:
each report's injected data is present and correctly shaped, since the
underlying db.* aggregation functions themselves are unchanged and
already covered by other test files."""
from datetime import date

import db


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type, "opening_balance": "0"}, follow_redirects=True)
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


def _seed(client):
    customer = _add_party(client, "V2 Report Customer")
    supplier = _add_party(client, "V2 Report Supplier", "Supplier")
    item = _add_quality(client, "V2 Report Item", sale_rate=200)
    today = date.today().isoformat()
    client.post("/transactions", data={"voucher_type": "PURCHASE", "party_id": str(supplier),
                                        "quality_id": str(item), "qty": "50", "rate": "150",
                                        "date": today, "mode": "Cash", "credit_days": "30"})
    client.post("/transactions", data={"voucher_type": "SALE", "party_id": str(customer),
                                        "quality_id": str(item), "qty": "10", "rate": "200",
                                        "date": today, "mode": "Cash", "credit_days": "15"})
    client.post("/recovery", data={"date": today, "party_id": str(customer), "mode": "Cash", "amount": "500"})
    client.post("/recovery", data={"date": today, "party_id": str(supplier), "mode": "Cash", "amount": "-300"})
    return customer, supplier, item


def test_ledger_page_lists_parties_and_shows_selected_ledger(client, company):
    customer, supplier, item = _seed(client)
    r = client.get(f"/reports/ledger?party_id={customer}")
    html = r.data.decode()
    assert '"name": "V2 Report Customer"' in html
    assert 'partyId: %d' % customer in html
    assert '"balance": 2000.0' in html  # after the sale row
    assert 'closingBalance: 1500.0' in html  # after the 500 receipt


def test_ledger_page_with_no_party_selected_has_null_party(client, company):
    r = client.get("/reports/ledger")
    assert "party: null" in r.data.decode()


def test_ledger_now_also_lists_and_shows_gl_accounts(client, company):
    """Party Ledger doubles as the Expense Ledger and Capital Ledger -
    every GL account (Home/Office Expense, Zakat, Capital Account) is
    selectable, and EXPENSE/CAPITAL_IN/CAPITAL_OUT postings against them
    get the correct Debit/Credit side (not just SALE/PAYMENT, which is
    all an ordinary customer/supplier ever needs)."""
    today = date.today().isoformat()
    client.post("/capital-expense", data={"kind": "expense", "category": "Office", "amount": "1200", "date": today})
    client.post("/capital-expense", data={"kind": "capital", "direction": "CAPITAL_IN", "amount": "50000", "date": today})
    client.post("/capital-expense", data={"kind": "capital", "direction": "CAPITAL_OUT", "amount": "4000", "date": today})

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (db.GL_OFFICE_EXPENSE,))
    office_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM parties WHERE name = ?", (db.GL_CAPITAL,))
    capital_id = cur.fetchone()[0]
    conn.close()

    r = client.get("/reports/ledger")
    html = r.data.decode()
    assert '"name": "Office Expense"' in html
    assert '"name": "Capital Account"' in html

    r2 = client.get(f"/reports/ledger?party_id={office_id}")
    html2 = r2.data.decode()
    assert '"debit": 1200.0' in html2
    assert 'closingBalance: 1200.0' in html2

    r3 = client.get(f"/reports/ledger?party_id={capital_id}")
    html3 = r3.data.decode()
    assert '"credit": 50000.0' in html3  # Capital In
    assert '"debit": 4000.0' in html3    # Capital Out
    # same debit-minus-credit convention as get_trial_balance() - a
    # capital/equity account is credit-normal, so its raw balance here
    # is negative (the business "owes" this back to the owner); the
    # page already takes abs() and labels it "(Payable)" for display
    assert 'closingBalance: -46000.0' in html3


def test_receivable_report_groups_by_party_with_subtotal(client, company):
    _seed(client)
    r = client.get("/reports/receivable")
    html = r.data.decode()
    assert '"party_name": "V2 Report Customer"' in html
    assert '"subtotal": 1500.0' in html
    assert "total: 1500.0" in html


def test_receivable_report_shows_contact_number_and_days_outstanding(client, company):
    """The Receivable Ledger's party group header shows the party's
    phone number (so collections don't need a separate trip to Parties),
    and each outstanding invoice carries its own days-outstanding figure
    (not just buried inside the "Overdue by Xd" status sentence)."""
    client.post("/parties", data={"name": "V2 Phone Customer", "party_type": "Customer",
                                   "phone": "0300-1234567", "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", ("V2 Phone Customer",))
    customer = cur.fetchone()[0]
    conn.close()
    item = _add_quality(client, "V2 Phone Item", sale_rate=200)
    client.post("/transactions", data={"voucher_type": "SALE", "party_id": str(customer),
                                        "quality_id": str(item), "qty": "5", "rate": "200",
                                        "date": "2020-01-01", "mode": "Cash", "credit_days": "10"})

    r = client.get("/reports/receivable?as_of=2020-01-20")
    html = r.data.decode()
    assert '"party_phone": "0300-1234567"' in html
    assert '"days": 9' in html  # 2020-01-20 minus due date (2020-01-01 + 10 credit days = 2020-01-11)


def test_payable_report_groups_by_party_with_subtotal(client, company):
    _seed(client)
    r = client.get("/reports/payable")
    html = r.data.decode()
    assert '"party_name": "V2 Report Supplier"' in html
    assert '"subtotal": 7200.0' in html


def test_brokerage_report_computes_percentage_brokerage(client, company):
    customer, supplier, item = _seed(client)
    broker = _add_party(client, "V2 Report Broker", "Broker")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE parties SET brokerage_type='percentage', brokerage_rate=1.0 WHERE id = ?", (broker,))
    cur.execute("UPDATE transactions SET broker=?, broker_party_id=? WHERE voucher_type='SALE'", ("V2 Report Broker", broker))
    conn.commit()
    conn.close()

    r = client.get("/reports/brokerage")
    html = r.data.decode()
    assert '"broker_name": "V2 Report Broker"' in html
    assert '"brokerage": 20.0' in html  # 1% of the 2000 sale


def test_cashbook_report_balances_both_sides(client, company):
    _seed(client)
    r = client.get("/reports/cashbook")
    html = r.data.decode()
    assert '"total_debit": 500.0' in html
    assert '"total_credit": 500.0' in html
    assert '"closing_balance": 200.0' in html


def test_cashbook_includes_contra_entries_as_real_cash_movement(client, company):
    """Contra entries are treated as real cash movement in the Cash Book
    (e.g. "Cash to Bank") - each leg shows as its own row on the
    matching side, and since every contra entry balances Dr == Cr by
    construction, the all-time closing balance is unaffected even
    though both totals for the period grow by the contra amount."""
    customer, supplier, item = _seed(client)
    bank = _add_party(client, "V2 Contra Bank", "Bank")
    today = date.today().isoformat()

    r_before = client.get("/reports/cashbook")
    closing_before = r_before.data.decode()

    client.post("/contra", data={
        "date": today, "description": "V2 cash to bank",
        "party_id[]": [str(bank), str(customer)],
        "direction[]": ["DR", "CR"],
        "amount[]": ["150", "150"],
    })

    r = client.get("/reports/cashbook")
    html = r.data.decode()
    assert '"party": "V2 Contra Bank"' in html
    assert '"party": "V2 Report Customer"' in html
    assert '"remarks": "V2 cash to bank"' in html
    # total_debit/total_credit both grew by 150 (one new row on each
    # side), but the closing balance - the actual cash position - is
    # exactly the same as before the contra entry, since it nets to zero
    assert '"total_debit": 650.0' in html
    assert '"total_credit": 650.0' in html
    assert '"closing_balance": 200.0' in html
    assert '"closing_balance": 200.0' in closing_before


def test_balance_sheet_balances_and_matches_the_other_reports(client, company):
    """Same seeded data as the cashbook/profit tests above - Assets must
    equal Liabilities + Equity, and every figure here should match what
    those other reports already show for the identical data (cash
    closing balance 200, net profit 500, customer receivable 1500,
    supplier payable 7200), since db.get_balance_sheet reuses those
    exact functions rather than recalculating any of it independently."""
    _seed(client)
    r = client.get("/reports/balance-sheet")
    html = r.data.decode()
    assert '"cash_balance": 200.0' in html
    assert '"amount": 1500.0, "name": "V2 Report Customer"' in html
    assert '"stock_value": 6000.0' in html
    assert '"total_assets": 7700.0' in html
    assert '"amount": 7200.0, "name": "V2 Report Supplier"' in html
    assert '"total_liabilities": 7200.0' in html
    assert '"capital": 0.0' in html
    assert '"opening_balance_equity": 0.0' in html
    assert '"retained_earnings": 500.0' in html
    assert '"total_equity": 500.0' in html
    assert '"total_liabilities_and_equity": 7700.0' in html


def test_profit_report_computes_gross_and_net_profit(client, company):
    _seed(client)
    r = client.get("/reports/profit")
    html = r.data.decode()
    assert '"total_sales": 2000.0' in html
    assert '"cogs": 1500.0' in html  # 10 units * weighted-avg purchase rate 150
    assert '"gross_profit": 500.0' in html
    assert '"net_profit": 500.0' in html


def test_stock_report_shows_current_quantity(client, company):
    _seed(client)
    r = client.get("/reports/stock")
    html = r.data.decode()
    assert '"name": "V2 Report Item"' in html
    assert '"stock": 40.0' in html  # 50 purchased - 10 sold


def test_stock_report_computes_value_and_summary_stats(client, company):
    """Each item's Value (stock x weighted-avg purchase rate) and the
    page-level Total Stock Value / Negative Stock summary stats - the
    With/Without Value toggle used to only affect the PDF/Excel export
    params while the on-screen table always showed the same columns
    either way; these numbers are what makes the toggle mean something
    on screen too."""
    _seed(client)  # 40 units of "V2 Report Item" left at a 150 weighted-avg purchase rate -> value 6000
    r = client.get("/reports/stock")
    html = r.data.decode()
    assert '"value": 6000.0' in html
    assert "totalValue: 6000.0" in html
    assert "negativeStockCount: 0" in html


def test_trial_balance_report_lists_active_parties_only(client, company):
    _seed(client)
    r = client.get("/reports/trial-balance")
    html = r.data.decode()
    assert '"name": "V2 Report Customer"' in html
    assert '"balance": 1500.0' in html
    assert '"name": "V2 Report Supplier"' in html
    assert '"balance": -7200.0' in html
    # a real trial balance always foots to the same total on both sides -
    # that only holds once the counter-accounts this app never stores as
    # rows (Sales, Purchases, Cash) are included alongside the parties'
    # own balances, which is what pushes this past the old 2300/8000 pair
    assert '"name": "Sales Account"' in html
    assert '"name": "Purchase Account"' in html
    assert '"name": "Cash Account"' in html
    assert "totalDebit: 10000.0" in html
    assert "totalCredit: 10000.0" in html
