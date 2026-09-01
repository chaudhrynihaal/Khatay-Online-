"""Receipt & Payment (recovery) and Contra entries - the two ways money
moves between parties without a Sale/Purchase behind it."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_party(client, name, party_type="Customer", opening_balance=0):
    client.post("/parties", data={"name": name, "party_type": party_type,
                                   "opening_balance": str(opening_balance)}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_recovery_positive_amount_is_a_receipt_and_reduces_receivable(client, company):
    party_id = _add_party(client, "Recovery Customer A", opening_balance=1000)
    assert db.get_party_balance(party_id) == 1000

    r = client.post("/recovery", data={
        "voucher_type": "RECEIPT", "party_id": str(party_id), "mode": "Cash",
        "amount": "400", "date": _today(),
    }, follow_redirects=True)
    assert b"Receipt saved" in r.data
    assert db.get_party_balance(party_id) == 600


def test_recovery_negative_amount_is_a_payment_regardless_of_dropdown(client, company):
    """Cash mode: the sign typed in Amount decides Receipt vs Payment,
    overriding whatever the Type dropdown happened to be set to - see
    the comment in app.py's recovery() route."""
    party_id = _add_party(client, "Recovery Supplier A", party_type="Supplier", opening_balance=-500)
    assert db.get_party_balance(party_id) == -500

    r = client.post("/recovery", data={
        "voucher_type": "RECEIPT", "party_id": str(party_id), "mode": "Cash",
        "amount": "-200", "date": _today(),
    }, follow_redirects=True)
    assert b"Payment saved" in r.data
    # paying a supplier reduces what you owe them - balance moves toward
    # zero (less negative), not further away
    assert db.get_party_balance(party_id) == -300


def test_recovery_zero_amount_rejected(client, company):
    party_id = _add_party(client, "Recovery Customer B")
    r = client.post("/recovery", data={
        "voucher_type": "RECEIPT", "party_id": str(party_id), "mode": "Cash",
        "amount": "0", "date": _today(),
    }, follow_redirects=True)
    assert b"zero" in r.data


def test_recovery_cheque_mode_sums_multiple_cheques(client, company):
    party_id = _add_party(client, "Recovery Customer C", opening_balance=5000)

    r = client.post("/recovery", data={
        "voucher_type": "RECEIPT", "party_id": str(party_id), "mode": "Cheque", "date": _today(),
        "cheque_date[]": [_today(), _today()],
        "cheque_bank[]": ["Bank A", "Bank B"],
        "cheque_no[]": ["111", "222"],
        "cheque_amount[]": ["300", "700"],
    }, follow_redirects=True)
    assert b"Receipt saved" in r.data
    assert db.get_party_balance(party_id) == 5000 - 1000


def test_contra_entry_must_balance(company):
    p1 = db.get_connection()
    cur = p1.cursor()
    cur.execute("INSERT INTO parties (name, party_type, is_gl, opening_balance, created_at) "
                "VALUES ('Contra Leg A', 'Customer', 0, 0, ?)", (db.now_iso(),))
    leg_a = cur.lastrowid
    cur.execute("INSERT INTO parties (name, party_type, is_gl, opening_balance, created_at) "
                "VALUES ('Contra Leg B', 'Customer', 0, 0, ?)", (db.now_iso(),))
    leg_b = cur.lastrowid
    p1.commit()
    p1.close()

    try:
        db.create_contra_entry(date.today().isoformat(),
                                [{"party_id": leg_a, "direction": "DR", "amount": 100},
                                 {"party_id": leg_b, "direction": "CR", "amount": 90}])
        assert False, "an unbalanced contra entry must raise ValueError"
    except ValueError as exc:
        assert "doesn't balance" in str(exc)

    voucher_no = db.create_contra_entry(date.today().isoformat(),
                                         [{"party_id": leg_a, "direction": "DR", "amount": 250},
                                          {"party_id": leg_b, "direction": "CR", "amount": 250}])
    assert voucher_no is not None
    assert db.get_party_balance(leg_a) == 250
    assert db.get_party_balance(leg_b) == -250
