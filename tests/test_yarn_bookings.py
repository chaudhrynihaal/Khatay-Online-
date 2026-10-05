"""Bookings (forward contracts / "sauda") - recording one must not touch
stock or party balance; only delivering against it (fully or partially)
creates a real transaction that does."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def _add_party(client, name, party_type="Customer"):
    client.post("/parties", data={"name": name, "party_type": party_type,
                                   "opening_balance": "0"}, follow_redirects=True)
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


def test_creating_a_booking_does_not_touch_stock_or_balance(client, company):
    party_id = _add_party(client, "Booking Customer A")
    quality_id = _add_quality(client, "Booking Yarn A")

    r = client.post("/bookings", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "500", "rate": "120", "date": _today(), "delivery_terms": "Ex-mill, 30 days",
    }, follow_redirects=True)
    assert b"Booking created" in r.data

    assert db.get_stock_qty(quality_id) == 0
    assert db.get_party_balance(party_id) == 0

    bookings = db.list_bookings("Open")
    assert len(bookings) == 1
    assert bookings[0]["remaining_qty"] == 500


def test_partial_delivery_creates_transaction_and_keeps_booking_open(client, company):
    party_id = _add_party(client, "Booking Customer B")
    quality_id = _add_quality(client, "Booking Yarn B")
    booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 1000, 100)

    r = client.post(f"/bookings/{booking_id}/deliver", data={
        "deliver_qty": "400", "delivery_date": _today(),
    }, follow_redirects=True)
    assert b"Delivery recorded" in r.data

    booking = db.get_booking(booking_id)
    assert booking["status"] == "Open"
    assert booking["delivered_qty"] == 400
    assert booking["remaining_qty"] == 600
    assert db.get_stock_qty(quality_id) == -400  # a Sale delivery reduces stock
    assert db.get_party_balance(party_id) == 400 * 100


def test_full_delivery_marks_booking_delivered(client, company):
    party_id = _add_party(client, "Booking Customer C")
    quality_id = _add_quality(client, "Booking Yarn C")
    booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 200, 90)

    client.post(f"/bookings/{booking_id}/deliver", data={"deliver_qty": "200", "delivery_date": _today()})

    booking = db.get_booking(booking_id)
    assert booking["status"] == "Delivered"
    assert booking["remaining_qty"] == 0


def test_delivery_exceeding_remaining_quantity_rejected(client, company):
    party_id = _add_party(client, "Booking Customer D")
    quality_id = _add_quality(client, "Booking Yarn D")
    booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 100, 50)

    r = client.post(f"/bookings/{booking_id}/deliver", data={"deliver_qty": "150"}, follow_redirects=True)
    assert b"must be between" in r.data
    booking = db.get_booking(booking_id)
    assert booking["delivered_qty"] == 0
    assert booking["status"] == "Open"


def test_cancel_booking_blocked_once_partially_delivered(client, company):
    party_id = _add_party(client, "Booking Customer E")
    quality_id = _add_quality(client, "Booking Yarn E")
    booking_id = db.create_booking("PURCHASE", _today(), party_id, quality_id, 300, 60)

    client.post(f"/bookings/{booking_id}/deliver", data={"deliver_qty": "50"})

    r = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert b"already has deliveries" in r.data
    assert db.get_booking(booking_id)["status"] == "Open"


def test_cancel_booking_allowed_before_any_delivery(client, company):
    party_id = _add_party(client, "Booking Customer F")
    quality_id = _add_quality(client, "Booking Yarn F")
    booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 300, 60)

    r = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert b"Booking cancelled" in r.data
    assert db.get_booking(booking_id)["status"] == "Cancelled"


def test_purchase_and_sale_entry_screen_lists_open_bookings_to_fulfill(client, company):
    """The Purchase & Sale entry screen offers fulfilling an open
    booking as an alternative to a fresh direct entry - it shouldn't
    need a trip to the Bookings section for that."""
    party_id = _add_party(client, "Booking Customer G", "Supplier")
    quality_id = _add_quality(client, "Booking Yarn G")
    booking_id = db.create_booking("PURCHASE", _today(), party_id, quality_id, 300, 60)
    # a fully delivered booking must not still show up as fulfillable
    other_booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 50, 60)
    client.post(f"/bookings/{other_booking_id}/deliver", data={"deliver_qty": "50", "delivery_date": _today()})

    r = client.get("/transactions")
    html = r.data.decode()
    assert '"id": %d' % booking_id in html
    assert '"remaining_qty": 300.0' in html
    assert '"id": %d' % other_booking_id not in html


def test_delivering_a_booking_from_the_transactions_screen_returns_there(client, company):
    """Passing return_to=transactions (as the Transactions page's Deliver
    dialog does) redirects back to the Purchase & Sale entry screen with
    the usual "saved" banner, instead of the Bookings page."""
    party_id = _add_party(client, "Booking Customer H")
    quality_id = _add_quality(client, "Booking Yarn H")
    booking_id = db.create_booking("SALE", _today(), party_id, quality_id, 100, 75)

    r = client.post(f"/bookings/{booking_id}/deliver", data={
        "deliver_qty": "100", "delivery_date": _today(), "return_to": "transactions",
    })
    assert r.status_code == 302
    assert r.headers["Location"].startswith("/transactions?saved=")

    r2 = client.post(f"/bookings/{booking_id}/deliver", data={
        "deliver_qty": "999", "return_to": "transactions",
    })
    assert r2.status_code == 302
    assert r2.headers["Location"] == "/transactions"
