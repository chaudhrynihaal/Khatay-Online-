"""The three remaining old-style pages found and migrated after the
main Yarn/Kiryana/Hardware/Admin sweep: Data Import (Yarn's bulk
Excel-import screen, previously still on the old purple sidebar despite
being linked from the new one - the one screen that was actually
reachable mid-session from the redesigned nav but hadn't been rebuilt),
Subscription Expired/Suspended (shown by several permission decorators
whenever a company's subscription lapses), and branded 404/500 error
pages (previously nonexistent - bare Flask defaults).

Visually verified via a headless-browser pass: a real template
download -> fill -> upload round trip on Data Import (correctly
redirects to /parties with an "Imported N new parties." toast, matching
the unchanged data_import.import_parties() behavior), the Subscription
Expired page rendering correctly for a temporarily-suspended real
company on the live dev server (immediately restored after), and the
404 page rendering correctly even fully logged out. No console errors
on any of the three."""
import io

import db


def test_data_import_page_renders(client, company):
    r = client.get("/data-import")
    assert r.status_code == 200
    assert b"Import Your Existing Data" in r.data


def test_data_import_parties_round_trip_redirects_to_parties_with_flash(client, company):
    csv_content = "Name,Type,City,Phone,NTN,STN,Credit Limit,Opening Balance,Address,Brokerage Rate Type,Brokerage Rate\nV2 Import Party,Customer,Lahore,0300,,,,1000,,,\n"
    data = {"file": (io.BytesIO(csv_content.encode()), "parties.csv")}
    r = client.post("/data-import/parties", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert r.request.path == "/parties"
    assert b"Imported 1 new party." in r.data or b"Imported" in r.data

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM parties WHERE name = 'V2 Import Party'")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_data_import_without_a_file_flashes_error_and_returns_to_import_page(client, company):
    r = client.post("/data-import/parties", follow_redirects=True)
    assert r.request.path == "/data-import"
    assert b"Choose a file to upload first." in r.data


def test_subscription_suspended_shows_the_new_page_not_the_requested_one(client, company):
    import master
    master.set_subscription(company["id"], "suspended", None, "")
    r = client.get("/parties")
    assert r.status_code == 200
    html = r.data.decode()
    assert "subscriptionStatus: \"suspended\"" in html
    assert "yarn-subscription-expired.js" in html
    master.set_subscription(company["id"], "active", None, "")


def test_404_page_renders_for_unknown_route_even_logged_out(client_anon):
    r = client_anon.get("/this-route-does-not-exist-v2-test")
    assert r.status_code == 404
    html = r.data.decode()
    assert "heading: \"Page not found\"" in html
    assert "code: 404" in html
