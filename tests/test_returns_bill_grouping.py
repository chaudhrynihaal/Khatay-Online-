"""The Returns page's "Return against a bill" picker used to list one
dropdown option per transaction LINE, so a 3-item sale showed up as 3
near-identical entries all starting with the same invoice number,
looking like 3 separate bills. It's grouped by invoice now - one option
per bill, with a sub-picker for which line to return when a bill has
more than one item."""
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

    import re
    bill_options = re.findall(r'<option value="\d+" data-lines=', html)
    assert len(bill_options) == 1, "a 3-line sale must appear as exactly one bill option, not three"

    m = re.search(r"data-lines='(.*?)'>", html, re.S)
    import json
    lines = json.loads(m.group(1))
    assert len(lines) == 3
    assert {l["item"] for l in lines} == {"Lays", "Dairy Milk"}


def test_hardware_returns_page_groups_multi_item_sale_as_one_bill(client, company):
    item1 = db.hardware_add_item("Hammer", "pcs", 200, 300, 50)
    item2 = db.hardware_add_item("Screws", "box", 50, 80, 100)
    party_id = db.hardware_add_party("Walk-in", "", "Customer", 0)
    invoice_no = db.hardware_get_next_invoice_no("SALE")
    db.hardware_record_sale(_today(), party_id, item1, 2, 300, "Cash", invoice_no=invoice_no)
    db.hardware_record_sale(_today(), party_id, item2, 5, 80, "Cash", invoice_no=invoice_no)

    r = client.get("/hardware/returns?type=Sale")
    html = r.data.decode()

    import re
    bill_options = re.findall(r'<option value="\d+" data-lines=', html)
    assert len(bill_options) == 1
