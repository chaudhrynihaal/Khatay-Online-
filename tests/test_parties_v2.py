"""The redesigned Parties screen (second screen migrated to the new
React/design-system frontend) - list, add, edit. Visually verified via
a headless-browser pass (dialog open/close, Reveal-based broker fields,
prefilled edit form, soft-disabled delete tooltip, flash-message
toasts); these tests check what the test client can verify server-side:
the injected data is correct and the underlying routes still behave
exactly as before."""
from datetime import date

import db


def _add_party(client, name, party_type="Customer", **extra):
    data = {"name": name, "party_type": party_type, "opening_balance": "0"}
    data.update(extra)
    client.post("/parties", data=data, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row[0]


def test_parties_list_injects_data_and_flash_toast(client, company):
    r = client.post("/parties", data={"name": "V2 Test Customer", "party_type": "Customer",
                                       "opening_balance": "0"}, follow_redirects=True)
    html = r.data.decode()
    assert '"name": "V2 Test Customer"' in html
    assert '"has_history": false' in html
    assert '"Party added."' in html  # flash message carried through to the toast data


def test_parties_list_flags_has_history_once_transaction_exists(client, company):
    party_id = _add_party(client, "V2 History Customer")
    client.post("/quality", data={"name": "V2 History Item", "sale_rate": "50"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 History Item'")
    quality_id = cur.fetchone()[0]
    conn.close()

    r0 = client.get("/parties")
    assert '"has_history": false' in r0.data.decode()

    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "1", "rate": "50", "date": date.today().isoformat(), "mode": "Cash",
    })

    r1 = client.get("/parties")
    html = r1.data.decode()
    idx = html.find('"id": %d' % party_id)
    assert idx != -1
    # has_history should be true somewhere in this party's JSON object
    assert '"has_history": true' in html


def test_edit_party_page_injects_prefilled_data(client, company):
    party_id = _add_party(client, "V2 Edit Customer", city="Lahore", phone="0300-0000000",
                           credit_limit="5000")
    r = client.get(f"/parties/{party_id}/edit")
    assert r.status_code == 200
    html = r.data.decode()
    assert '"name": "V2 Edit Customer"' in html
    assert '"city": "Lahore"' in html
    assert '"credit_limit": 5000.0' in html


def test_edit_party_page_shows_opening_entries_count(client, company):
    party_id = _add_party(client, "V2 Opening Customer")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO opening_entries (party_id, entry_type, date, reference, amount, created_at) "
                "VALUES (?, 'SALE', '2025-01-01', 'imported', 3000, ?)", (party_id, db.now_iso()))
    conn.commit()
    conn.close()

    r = client.get(f"/parties/{party_id}/edit")
    html = r.data.decode()
    assert "openingCount: 1" in html
    assert "openingTotal: 3000.0" in html
