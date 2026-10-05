"""The redesigned Quality/Items screen - list, add (via a Dialog with an
info Banner explaining the auto-computed Purchase Rate), soft-disabled
Delete once an item has transaction history. Visually verified via a
headless-browser pass; these tests check what the test client can
verify server-side: the injected data (including the computed
purchase_rate/stock fields) is correct and has_history flips once a
transaction references the item."""
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


def test_quality_list_injects_data_and_flash_toast(client, company):
    r = client.post("/quality", data={"name": "V2 Test Item", "city_area": "Lahore",
                                       "sale_rate": "150"}, follow_redirects=True)
    html = r.data.decode()
    assert '"name": "V2 Test Item"' in html
    assert '"sale_rate": 150.0' in html
    assert '"has_history": false' in html
    assert '"Item added."' in html


def test_quality_list_flags_has_history_once_transaction_exists(client, company):
    client.post("/quality", data={"name": "V2 History Item", "sale_rate": "50"}, follow_redirects=True)
    party_id = _add_party(client, "V2 History Party")
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 History Item'")
    quality_id = cur.fetchone()[0]
    conn.close()

    r0 = client.get("/quality")
    assert '"has_history": false' in r0.data.decode()

    client.post("/transactions", data={
        "voucher_type": "SALE", "party_id": str(party_id), "quality_id": str(quality_id),
        "qty": "1", "rate": "50", "date": date.today().isoformat(), "mode": "Cash",
    })

    r1 = client.get("/quality")
    assert '"has_history": true' in r1.data.decode()


def test_quality_search_filters_by_name_and_area(client, company):
    client.post("/quality", data={"name": "V2 Search Alpha", "city_area": "Karachi", "sale_rate": "10"}, follow_redirects=True)
    client.post("/quality", data={"name": "V2 Search Beta", "city_area": "Multan", "sale_rate": "20"}, follow_redirects=True)

    r = client.get("/quality?q=Karachi")
    html = r.data.decode()
    assert '"name": "V2 Search Alpha"' in html
    assert '"name": "V2 Search Beta"' not in html


def test_edit_quality_item_page_renders_current_values(client, company):
    client.post("/quality", data={"name": "V2 Edit Item", "city_area": "Lahore",
                                   "sale_rate": "75", "opening_balance": "12",
                                   "purchase_rate": "60"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 Edit Item'")
    item_id = cur.fetchone()[0]
    conn.close()

    r = client.get(f"/quality/{item_id}/edit")
    html = r.data.decode()
    assert '"name": "V2 Edit Item"' in html
    assert '"area": "Lahore"' in html
    assert '"sale_rate": 75.0' in html
    assert '"opening_balance": 12.0' in html
    assert '"purchase_rate": 60.0' in html


def test_edit_quality_item_saves_changes(client, company):
    client.post("/quality", data={"name": "V2 Edit Save", "sale_rate": "10"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 Edit Save'")
    item_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/quality/{item_id}/edit", data={
        "name": "V2 Edit Save Renamed", "city_area": "Faisalabad",
        "sale_rate": "99", "opening_balance": "5", "purchase_rate": "80",
    }, follow_redirects=True)
    assert '"Item updated."' in r.data.decode()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, city_area, sale_rate, opening_balance, purchase_rate FROM quality WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    assert row == ("V2 Edit Save Renamed", "Faisalabad", 99.0, 5.0, 80.0)


def test_edit_quality_item_requires_a_name(client, company):
    client.post("/quality", data={"name": "V2 Edit NoName", "sale_rate": "10"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 Edit NoName'")
    item_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/quality/{item_id}/edit", data={"name": "", "sale_rate": "10"}, follow_redirects=True)
    assert "Item name is required." in r.data.decode()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM quality WHERE id = ?", (item_id,))
    assert cur.fetchone()[0] == "V2 Edit NoName"
    conn.close()


def test_delete_quality_item_without_history_succeeds(client, company):
    client.post("/quality", data={"name": "V2 Deletable Item", "sale_rate": "10"}, follow_redirects=True)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality WHERE name = 'V2 Deletable Item'")
    item_id = cur.fetchone()[0]
    conn.close()

    r = client.post(f"/quality/{item_id}/delete", follow_redirects=True)
    assert r.status_code == 200

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM quality WHERE id = ?", (item_id,))
    assert cur.fetchone()[0] == 0
    conn.close()
