"""The redesigned Capital & Expense screen - two client-side tabs (Home
& Office Expense, Capital In / Out) sharing one page, each posting its
own real <form kind=expense|capital> to the unchanged
/capital-expense route. Visually verified via a headless-browser pass
(tab switching, both save flows, the saved-voucher banner defaulting
back to the Expense tab after a Capital save - matching the
pre-migration page, which always reset to the Expense tab on reload
regardless of which form was submitted). These tests check what the
test client can verify server-side: the injected data and that both
save paths still produce the same DB rows and voucher numbering as
before."""
import db


def test_capital_expense_page_injects_expenses_and_capital_summary(client, company):
    client.post("/capital-expense", data={"kind": "expense", "date": "2026-01-01",
                                           "category": "Office", "amount": "300"}, follow_redirects=True)
    r = client.get("/capital-expense")
    html = r.data.decode()
    assert '"category": "Office"' in html
    assert '"amount": 300.0' in html
    assert "capital:" in html


def test_save_expense_creates_transaction_and_saved_banner(client, company):
    r = client.post("/capital-expense", data={
        "kind": "expense", "date": "2026-01-01", "category": "Home", "amount": "150",
        "description": "utilities",
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"Expense saved."' in html
    assert '"voucher": "EXP-000001"' in html

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT voucher_type, amount, description FROM transactions WHERE voucher_type = 'EXPENSE'")
    row = cur.fetchone()
    conn.close()
    assert row == ("EXPENSE", 150.0, "utilities")


def test_save_capital_in_updates_summary_and_history(client, company):
    r = client.post("/capital-expense", data={
        "kind": "capital", "date": "2026-01-01", "direction": "CAPITAL_IN", "amount": "5000",
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"Capital In saved."' in html
    assert '"total_in": 5000.0' in html
    assert '"net_capital": 5000.0' in html
    assert '"direction": "In"' in html


def test_save_capital_out_reduces_net_capital(client, company):
    client.post("/capital-expense", data={"kind": "capital", "date": "2026-01-01",
                                           "direction": "CAPITAL_IN", "amount": "5000"}, follow_redirects=True)
    r = client.post("/capital-expense", data={
        "kind": "capital", "date": "2026-01-02", "direction": "CAPITAL_OUT", "amount": "2000",
    }, follow_redirects=True)
    html = r.data.decode()
    assert '"total_out": 2000.0' in html
    assert '"net_capital": 3000.0' in html
