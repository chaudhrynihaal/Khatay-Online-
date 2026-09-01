"""Regression coverage for the real (reportlab) PDF bills that replaced
the browser-print HTML pages for Kiryana and Hardware."""
from datetime import date

import db
import retail_pdf


def _today():
    return date.today().isoformat()


def test_kiryana_bill_pdf_generates_a_real_file(company, tmp_path):
    item_id = db.kiryana_add_item("PDF Test Item", "pcs", 10, 15, 20)
    party_id = db.kiryana_add_party("PDF Test Customer", "0300", "Customer", 0)
    db.kiryana_record_sale(_today(), party_id, item_id, 2, 15, "Cash")

    invs = db.kiryana_list_invoices("SALE", limit=1)
    bill = db.kiryana_get_bill("SALE", invs[0]["lines"][0]["id"])

    out_path = tmp_path / "kiryana_test_bill.pdf"
    result_path = retail_pdf.generate_kiryana_bill_pdf(bill, "SALE", output_path=str(out_path))

    assert out_path.exists()
    assert out_path.stat().st_size > 500
    with open(result_path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_hardware_bill_pdf_generates_a_real_file_with_tax(company, tmp_path):
    item_id = db.hardware_add_item("PDF Test Hardware Item", "pcs", 100, 150, 20)
    party_id = db.hardware_add_party("PDF Test Hardware Customer", "0311", "Customer", 0)
    db.hardware_record_sale(_today(), party_id, item_id, 3, 150, "Cash")

    invs = db.hardware_list_invoices("SALE", limit=1)
    bill = db.hardware_get_bill("SALE", invs[0]["lines"][0]["id"])

    out_path = tmp_path / "hardware_test_bill.pdf"
    result_path = retail_pdf.generate_hardware_bill_pdf(
        bill, "SALE", tax_rate=17, tax_amount=round(bill["total"] * 0.17, 2),
        gst_number="TEST-GST-001", output_path=str(out_path),
    )

    assert out_path.exists()
    assert out_path.stat().st_size > 500
    with open(result_path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_print_routes_serve_pdf(client, company):
    item_id = db.hardware_add_item("Route Test Item", "pcs", 100, 150, 20)
    party_id = db.hardware_add_party("Route Test Customer", "0322", "Customer", 0)
    db.hardware_record_sale(_today(), party_id, item_id, 1, 150, "Cash")
    invs = db.hardware_list_invoices("SALE", limit=1)
    txn_id = invs[0]["lines"][0]["id"]

    r = client.get(f"/hardware/print/SALE/{txn_id}")
    assert r.status_code == 200
    assert r.content_type == "application/pdf"
