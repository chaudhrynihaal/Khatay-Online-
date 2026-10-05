"""The Returns page's "Return against a bill" picker used to list one
dropdown option per transaction LINE, so a 3-item sale showed up as 3
near-identical entries all starting with the same invoice number,
looking like 3 separate bills. It's grouped by invoice now - one option
per bill, with a sub-picker for which line to return when a bill has
more than one item.

The Kiryana and Hardware redesigns (React shell reading
window.__PAGE__.sourceBills, built from the unchanged
db.kiryana_list_invoices()/db.hardware_list_invoices()) replaced the
old pages' server-rendered <option data-lines=...> markup with a
Combobox built client-side from the same grouped JSON, so both tests
now check that JSON directly rather than scraping HTML option tags -
the underlying grouping behavior they guard against regressing is
identical either way."""
from datetime import date

import db


def _today():
    return date.today().isoformat()


def test_kiryana_returns_page_groups_multi_item_sale_as_one_bill(client, company):
    item1 = db.kiryana_add_item("Lays", "pcs", 40, 50, 100)
    item2 = db.kiryana_add_item("Dairy Milk", "pcs", 45, 60, 100)
    party_id = db.kiryana_add_party("Walk-in", "", "Customer", 0)
    invoice_no = db.kiryana_get_next_invoice_no("SALE")
    db.kiryana_record_sale(_today(), party_id, item1, 5, 50, "Cash", invoice_no=invoice_no)
    db.kiryana_record_sale(_today(), party_id, item2, 3, 60, "Cash", invoice_no=invoice_no)
    db.kiryana_record_sale(_today(), party_id, item2, 3, 60, "Cash", invoice_no=invoice_no)

    r = client.get("/kiryana/returns?type=Sale")
    html = r.data.decode()

    idx = html.find("sourceBills")
    end = html.find("printUrlBase", idx)
    snippet = html[idx:end]
    assert snippet.count('"total_amount":') == 1, "a 3-line sale must appear as exactly one bill, not three"
    assert snippet.count('"item":') == 3
    assert '"item": "Lays"' in snippet
    assert '"item": "Dairy Milk"' in snippet


def test_hardware_returns_page_groups_multi_item_sale_as_one_bill(client, company):
    item1 = db.hardware_add_item("Hammer", "pcs", 200, 300, 50)
    item2 = db.hardware_add_item("Screws", "box", 50, 80, 100)
    party_id = db.hardware_add_party("Walk-in", "", "Customer", 0)
    invoice_no = db.hardware_get_next_invoice_no("SALE")
    db.hardware_record_sale(_today(), party_id, item1, 2, 300, "Cash", invoice_no=invoice_no)
    db.hardware_record_sale(_today(), party_id, item2, 5, 80, "Cash", invoice_no=invoice_no)

    r = client.get("/hardware/returns?type=Sale")
    html = r.data.decode()

    idx = html.find("sourceBills")
    end = html.find("printUrlBase", idx)
    snippet = html[idx:end]
    assert snippet.count('"total_amount":') == 1, "a 2-line sale must appear as exactly one bill, not two"
    assert snippet.count('"item":') == 2
