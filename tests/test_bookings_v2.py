"""The redesigned Bookings screen (list/create/Tabs status filter, Deliver
dialog, Cancel) and its read-only detail page. Visually verified via a
headless-browser pass (Tabs navigation, Deliver dialog with a live
"Remaining: N" hint, partial-delivery flow, Cancel disappearing once a
booking has any delivery against it, the delivery-history table on the
detail page). These tests check what the test client can verify
server-side: the injected data is correct and the underlying
create/deliver/cancel routes still behave exactly as before."""
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


def test_bookings_list_injects_parties_items_and_open_bookings(client, company):
    party_id = _add_party(client, "V2 Booking Customer")
    quality_id = _add_quality(client, "V2 Booking Item")

    client.post("/bookings", data={
        "voucher_type": "SALE", "date": date.today().isoformat(),
        "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "500", "rate": "200", "delivery_terms": "within 30 days",
    }, follow_redirects=True)

    r = client.get("/bookings")
    html = r.data.decode()
    assert '"name": "V2 Booking Customer"' in html
    assert '"name": "V2 Booking Item"' in html
    assert '"booking_display": "BK-000001"' in html
    assert '"status": "Open"' in html
    assert '"delivered_qty": 0.0' in html
    assert '"remaining_qty": 500.0' in html
    assert 'statusFilter: "Open"' in html
    assert 'partyQuickAddUrl: "/parties/quick-add"' in html
    assert 'itemQuickAddUrl: "/quality/quick-add"' in html


def test_bookings_status_tab_filters_and_search_works(client, company):
    party_id = _add_party(client, "V2 Booking Customer 2")
    quality_id = _add_quality(client, "V2 Booking Item 2")
    client.post("/bookings", data={
        "voucher_type": "PURCHASE", "date": date.today().isoformat(),
        "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "100", "rate": "50",
    }, follow_redirects=True)

    r_all = client.get("/bookings?status=All")
    assert '"booking_display": "BK-000001"' in r_all.data.decode()

    r_delivered = client.get("/bookings?status=Delivered")
    assert "BK-000001" not in r_delivered.data.decode()

    r_search = client.get("/bookings?q=V2 Booking Customer 2")
    assert '"booking_display": "BK-000001"' in r_search.data.decode()

    r_miss = client.get("/bookings?q=nonexistent-xyz")
    assert "BK-000001" not in r_miss.data.decode()


def test_deliver_booking_partial_updates_status_and_saved_banner(client, company):
    party_id = _add_party(client, "V2 Booking Customer 3")
    quality_id = _add_quality(client, "V2 Booking Item 3")
    client.post("/bookings", data={
        "voucher_type": "SALE", "date": date.today().isoformat(),
        "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "500", "rate": "200",
    }, follow_redirects=True)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM bookings WHERE party_id = ?", (party_id,))
    booking_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/bookings/{booking_id}/deliver", data={
        "deliver_qty": "150", "delivery_date": date.today().isoformat(), "mode": "Cash",
    }, follow_redirects=True)
    html = r.data.decode()
    assert "savedVoucher:" in html
    assert '"delivered_qty": 150.0' in html
    assert '"remaining_qty": 350.0' in html
    assert '"status": "Open"' in html  # not fully delivered yet

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE booking_id = ?", (booking_id,))
    assert cur.fetchone()[0] == 1
    conn.close()


def test_cancel_booking_removes_it_when_no_deliveries_exist(client, company):
    party_id = _add_party(client, "V2 Booking Customer 4")
    quality_id = _add_quality(client, "V2 Booking Item 4")
    client.post("/bookings", data={
        "voucher_type": "SALE", "date": date.today().isoformat(),
        "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "10", "rate": "20",
    }, follow_redirects=True)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM bookings WHERE party_id = ?", (party_id,))
    booking_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/bookings/{booking_id}/cancel", follow_redirects=True)
    assert '"Booking cancelled."' in r.data.decode()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,))
    assert cur.fetchone()[0] == "Cancelled"
    conn.close()


def test_booking_detail_page_injects_summary_and_delivery_history(client, company):
    party_id = _add_party(client, "V2 Booking Customer 5")
    quality_id = _add_quality(client, "V2 Booking Item 5")
    client.post("/bookings", data={
        "voucher_type": "SALE", "date": date.today().isoformat(),
        "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "20", "rate": "100",
    }, follow_redirects=True)

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM bookings WHERE party_id = ?", (party_id,))
    booking_id = cur.fetchone()[0]
    conn.close()

    client.post(f"/bookings/{booking_id}/deliver", data={
        "deliver_qty": "20", "delivery_date": date.today().isoformat(), "mode": "Cash",
    })

    r = client.get(f"/bookings/{booking_id}")
    assert r.status_code == 200
    html = r.data.decode()
    assert '"party_name": "V2 Booking Customer 5"' in html
    assert '"item_name": "V2 Booking Item 5"' in html
    assert '"delivered_qty": 20.0' in html
    assert '"status": "Delivered"' in html
    assert '"amount": 2000.0' in html  # in the deliveries list


def test_booking_detail_missing_id_redirects_with_flash(client, company):
    r = client.get("/bookings/999999", follow_redirects=True)
    assert '"Booking not found."' in r.data.decode()
