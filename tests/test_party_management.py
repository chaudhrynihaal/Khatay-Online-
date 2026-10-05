"""Party edit/delete, and the imported-outstanding-invoices safety net
(opening_entries) that blocks deleting a party until they're cleared."""
import db


def test_edit_party_updates_fields(client, company):
    client.post("/parties", data={"name": "Editable Party", "party_type": "Customer",
                                   "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", ("Editable Party",))
    party_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/parties/{party_id}/edit", data={
        "name": "Renamed Party", "city": "Karachi", "phone": "0300-1234567",
        "party_type": "Customer", "credit_limit": "50000", "opening_balance": "0",
    }, follow_redirects=True)
    assert b"Party updated" in r.data

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, city, credit_limit FROM parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    conn.close()
    assert row == ("Renamed Party", "Karachi", 50000)


def test_delete_party_blocked_once_it_has_transactions(client, company):
    client.post("/parties", data={"name": "Party With History", "party_type": "Customer",
                                   "opening_balance": "0"}, follow_redirects=True)
    client.post("/quality", data={"name": "History Item", "sale_rate": "50"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", ("Party With History",))
    party_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM quality WHERE name = ?", ("History Item",))
    quality_id = cur.fetchone()[0]
    conn.close()

    from datetime import date
    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "1", "rate": "50", "date": date.today().isoformat(), "mode": "Cash",
    })

    r = client.post(f"/parties/{party_id}/delete", follow_redirects=True)
    assert b"delete a party with transactions" in r.data

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM parties WHERE id = ?", (party_id,))
    assert cur.fetchone()[0] == 1
    conn.close()


def test_delete_party_succeeds_with_no_history(client, company):
    client.post("/parties", data={"name": "Deletable Party", "party_type": "Customer",
                                   "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", ("Deletable Party",))
    party_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/parties/{party_id}/delete", follow_redirects=True)
    assert b"Party deleted" in r.data
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM parties WHERE id = ?", (party_id,))
    assert cur.fetchone()[0] == 0
    conn.close()


def test_clear_opening_entries_unblocks_delete(client, company):
    client.post("/parties", data={"name": "Imported Party", "party_type": "Customer",
                                   "opening_balance": "0"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", ("Imported Party",))
    party_id = cur.fetchone()[0]
    cur.execute("INSERT INTO opening_entries (party_id, entry_type, date, reference, amount, created_at) "
                "VALUES (?, 'SALE', '2025-01-01', 'imported invoice', 5000, ?)", (party_id, db.now_iso()))
    conn.commit()
    conn.close()

    r = client.post(f"/parties/{party_id}/delete", follow_redirects=True)
    assert b"imported outstanding invoices" in r.data

    r2 = client.post(f"/parties/{party_id}/clear-opening-entries", follow_redirects=True)
    assert b"Removed 1 imported outstanding invoice" in r2.data

    r3 = client.post(f"/parties/{party_id}/delete", follow_redirects=True)
    assert b"Party deleted" in r3.data
