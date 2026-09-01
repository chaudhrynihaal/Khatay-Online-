"""
retail_pdf.py
--------------
Real PDF bills for the Kiryana and Hardware verticals, replacing the
browser-print HTML pages (templates/app/kiryana|hardware/print_bill.html
are kept only as an HTML fallback if reportlab isn't available).

Takes the same `bill` dict already assembled by db.kiryana_get_bill() /
db.hardware_get_bill() - {invoice, date, mode, description, party, lines,
total} - rather than re-querying the database, so this module stays a
thin rendering layer.

Two generators, matching the two distinct visual families that already
existed as HTML (kept distinct on purpose - see print_bill.html history):

    generate_kiryana_bill_pdf(bill, txn_type, output_path=None)
        Plain single-copy receipt, portrait A4.

    generate_hardware_bill_pdf(bill, txn_type, tax_rate=0, tax_amount=0,
                                gst_number=None, output_path=None)
        Invoice-style with a colored header band, Billed-To block, GST
        numbers, tax breakdown and signature lines.
"""

import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, HRFlowable

from voucher_print import (
    _build_pdf, _get_theme_colors, _get_logo_path, _default_output_dir,
    fmt_amount, styles, _elegant_table_style, _ColorBar,
)

try:
    import settings as _settings_module
except ImportError:
    _settings_module = None


def _get_company_name():
    if _settings_module is not None and hasattr(_settings_module, "get_company_name"):
        return _settings_module.get_company_name()
    return "Company Name"


_KIRYANA_TITLES = {"SALE": "Sale Receipt", "PURCHASE": "Purchase Bill",
                    "SALE_RETURN": "Sale Return", "PURCHASE_RETURN": "Purchase Return"}
_HARDWARE_TITLES = {"SALE": "Sale Invoice", "PURCHASE": "Purchase Bill",
                     "SALE_RETURN": "Sale Return Note", "PURCHASE_RETURN": "Purchase Return Note",
                     "QUOTATION": "Quotation", "QUOTATION_CONVERTED": "Quotation"}


def _qty_str(qty):
    try:
        return f"{qty:g}"
    except (TypeError, ValueError):
        return str(qty)


def _safe_filename(invoice_str):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (invoice_str or "bill"))


# =======================================================================
# KIRYANA - plain receipt
# =======================================================================
def generate_kiryana_bill_pdf(bill, txn_type, output_path=None):
    theme = _get_theme_colors()
    primary_dark = theme["primary_dark"]
    company_name = _get_company_name()
    doc_label = _KIRYANA_TITLES.get(txn_type, txn_type)
    party_role = "Customer" if txn_type in ("SALE", "SALE_RETURN") else "Supplier"

    page_width = A4[0] - 32 * mm
    flow = []

    header = Table(
        [[Paragraph(f'<font size="15"><b>{company_name}</b></font>'
                     f'<br/><font size="9" color="{primary_dark}">{doc_label}</font>',
                    ParagraphStyle("KHdr", parent=styles["Normal"], leading=13)),
          Paragraph(f'<font size="12"><b>{bill["invoice"]}</b></font>'
                     f'<br/><font size="9" color="#666666">{bill["date"]}</font>',
                    ParagraphStyle("KHdrR", parent=styles["Normal"], alignment=2, leading=13))]],
        colWidths=[page_width * 0.6, page_width * 0.4],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(header)
    flow.append(Spacer(1, 4 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=0.75))
    flow.append(Spacer(1, 4 * mm))

    party_name = bill["party"]["name"] if bill["party"] else "Walk-in"
    party_phone = bill["party"].get("phone") if bill["party"] else None
    party_text = f"<b>{party_role}:</b> {party_name}"
    if party_phone:
        party_text += f" &middot; {party_phone}"
    meta = Table(
        [[Paragraph(party_text, ParagraphStyle("KMetaL", parent=styles["Normal"], fontSize=9.5)),
          Paragraph(f"<b>Mode:</b> {bill['mode']}",
                    ParagraphStyle("KMetaR", parent=styles["Normal"], fontSize=9.5, alignment=2))]],
        colWidths=[page_width * 0.6, page_width * 0.4],
    )
    flow.append(meta)
    flow.append(Spacer(1, 5 * mm))

    data = [["Item", "Qty", "Rate", "Amount"]]
    for l in bill["lines"]:
        data.append([l["item"] or "-", _qty_str(l["qty"]), fmt_amount(l["rate"]), fmt_amount(l["amount"])])
    tbl = Table(data, colWidths=[page_width * 0.42, page_width * 0.16, page_width * 0.21, page_width * 0.21],
                repeatRows=1)
    tbl.setStyle(_elegant_table_style())
    tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
    ]))
    flow.append(tbl)

    total_tbl = Table([["TOTAL", fmt_amount(bill["total"])]],
                       colWidths=[page_width * 0.79, page_width * 0.21])
    total_tbl.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(primary_dark)),
        ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor(primary_dark)),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(total_tbl)

    if bill.get("description"):
        flow.append(Spacer(1, 4 * mm))
        flow.append(Paragraph(bill["description"],
                               ParagraphStyle("KDesc", parent=styles["Normal"], fontSize=8.5,
                                              textColor=colors.HexColor("#666666"))))

    flow.append(Spacer(1, 8 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#eeeeee"), thickness=0.5))
    flow.append(Paragraph(f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} — {bill['invoice']}",
                           ParagraphStyle("KFooter", parent=styles["Normal"], fontSize=7, textColor=colors.grey)))

    if output_path is None:
        output_path = os.path.join(_default_output_dir(),
                                    f"{_safe_filename(bill['invoice'])}_{txn_type}.pdf")
    return _build_pdf(output_path, flow, margins=(16, 16, 16, 16))


# =======================================================================
# HARDWARE - invoice with header band, GST, tax breakdown, signatures
# =======================================================================
def generate_hardware_bill_pdf(bill, txn_type, tax_rate=0, tax_amount=0, gst_number=None, output_path=None):
    theme = _get_theme_colors()
    primary = theme["primary"]
    primary_dark = theme["primary_dark"]
    company_name = _get_company_name()
    doc_label = _HARDWARE_TITLES.get(txn_type, txn_type)
    party_role = "Billed To" if txn_type in ("SALE", "SALE_RETURN") else "Supplier"
    party_gst_role = "Customer" if txn_type in ("SALE", "SALE_RETURN") else "Supplier"

    page_width = A4[0] - 30 * mm
    flow = []

    band = Table(
        [[Paragraph(f'<font color="white" size="16"><b>{company_name}</b></font>'
                     f'<br/><font color="white" size="8.5">{doc_label.upper()}</font>',
                    ParagraphStyle("HBandL", parent=styles["Normal"], leading=15)),
          Paragraph(f'<font color="white" size="13"><b>{bill["invoice"]}</b></font>'
                     f'<br/><font color="white" size="8.5">{bill["date"]}</font>',
                    ParagraphStyle("HBandR", parent=styles["Normal"], alignment=2, leading=15))]],
        colWidths=[page_width * 0.6, page_width * 0.4],
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(primary)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 10), ("RIGHTPADDING", (1, 0), (1, 0), 10),
    ]))
    flow.append(band)
    flow.append(Spacer(1, 6 * mm))

    party_name = bill["party"]["name"] if bill["party"] else "Walk-in"
    party_phone = bill["party"].get("phone") if bill["party"] else None
    party_gst = bill["party"].get("gst_number") if bill["party"] else None

    left_lines = [f'<font size="7.5" color="#888888">{party_role.upper()}</font>',
                  f'<font size="10"><b>{party_name}</b></font>']
    if party_phone:
        left_lines.append(f'<font size="8.5">{party_phone}</font>')
    left_para = Paragraph("<br/>".join(left_lines), ParagraphStyle("HPartyL", parent=styles["Normal"], leading=12))

    right_lines = [f'<font size="7.5" color="#888888">PAYMENT MODE</font>',
                   f'<font size="9.5"><b>{bill["mode"]}</b></font>']
    if gst_number:
        right_lines.append(f'<font size="7.5" color="#888888">OUR GST NO.</font>')
        right_lines.append(f'<font size="9">{gst_number}</font>')
    if party_gst:
        right_lines.append(f'<font size="7.5" color="#888888">{party_gst_role.upper()} GST NO.</font>')
        right_lines.append(f'<font size="9">{party_gst}</font>')
    right_para = Paragraph("<br/>".join(right_lines),
                            ParagraphStyle("HPartyR", parent=styles["Normal"], leading=12, alignment=2))

    party_tbl = Table([[left_para, right_para]], colWidths=[page_width * 0.6, page_width * 0.4])
    party_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor("#dddddd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    flow.append(party_tbl)
    flow.append(Spacer(1, 6 * mm))

    data = [["#", "Item", "Qty", "Rate", "Amount"]]
    for idx, l in enumerate(bill["lines"], start=1):
        data.append([str(idx), l["item"] or "-", _qty_str(l["qty"]), fmt_amount(l["rate"]), fmt_amount(l["amount"])])
    tbl = Table(data, colWidths=[page_width * 0.06, page_width * 0.4, page_width * 0.15,
                                  page_width * 0.19, page_width * 0.2], repeatRows=1)
    tbl.setStyle(_elegant_table_style())
    tbl.setStyle(TableStyle([
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ]))
    flow.append(tbl)
    flow.append(Spacer(1, 5 * mm))

    totals_width = page_width * 0.4
    if tax_rate:
        subtotal_rows = [
            ["Subtotal", fmt_amount(bill["total"])],
            [f"Tax ({tax_rate:g}%)", fmt_amount(tax_amount)],
            ["TOTAL", fmt_amount(bill["total"] + tax_amount)],
        ]
    else:
        subtotal_rows = [["TOTAL", fmt_amount(bill["total"])]]
    totals_tbl = Table(subtotal_rows, colWidths=[totals_width * 0.55, totals_width * 0.45])
    style_cmds = [
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor(primary_dark)),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor(primary_dark)),
        ("TOPPADDING", (0, -1), (-1, -1), 5),
    ]
    totals_tbl.setStyle(TableStyle(style_cmds))
    wrapper = Table([["", totals_tbl]], colWidths=[page_width - totals_width, totals_width])
    flow.append(wrapper)

    if bill.get("description"):
        flow.append(Spacer(1, 5 * mm))
        flow.append(Paragraph(f"<b>Note:</b> {bill['description']}",
                               ParagraphStyle("HDesc", parent=styles["Normal"], fontSize=8.5,
                                              textColor=colors.HexColor("#666666"))))

    flow.append(Spacer(1, 18 * mm))
    sig_tbl = Table(
        [["_______________________", "", "_______________________"],
         ["Received By", "", "Authorized Signature"]],
        colWidths=[page_width * 0.42, page_width * 0.16, page_width * 0.42],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, 1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
    ]))
    flow.append(sig_tbl)

    flow.append(Spacer(1, 8 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#eeeeee"), thickness=0.5))
    flow.append(Paragraph(f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} — {bill['invoice']}",
                           ParagraphStyle("HFooter", parent=styles["Normal"], fontSize=7, textColor=colors.grey)))

    if output_path is None:
        output_path = os.path.join(_default_output_dir(),
                                    f"{_safe_filename(bill['invoice'])}_{txn_type}.pdf")
    return _build_pdf(output_path, flow, margins=(15, 15, 15, 15))


if __name__ == "__main__":
    print("This module is meant to be imported from app.py's print routes.")
