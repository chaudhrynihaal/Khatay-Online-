"""
voucher_print.py
------------------
Per-transaction printable documents for ULTRA ERP - separate from the
ledger reports in pdf_export.py.

Two distinct visual families, both using the app's selected color
theme (see ui_theme.py / settings.get_theme()):

  INVOICE family (Sale / Purchase) - generate_do_invoice_pdf()
      Full-width colored header band, invoice number top-right,
      itemized table, totals box.

  VOUCHER family (Receipt / Payment) - generate_receipt_voucher_pdf(),
      generate_payment_voucher_pdf()
      Centered card layout with a colored corner stamp for the voucher
      number, big boxed amount, signature strip.

Every document is numbered sequentially per voucher_type (INV-000001,
PINV-000001, RCPT-000001, PAY-000001, ...) via db.format_voucher_no().

    generate_do_invoice_pdf(transaction_id, output_path=None)
    generate_receipt_voucher_pdf(transaction_id, output_path=None)
    generate_payment_voucher_pdf(transaction_id, output_path=None)
    generate_voucher_pdf(transaction_id, output_path=None)   # dispatcher
"""

import os
import io
import base64
import sqlite3
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable, Image
)
from reportlab.platypus.flowables import Flowable

# ---------------------------------------------------------------------
# PROJECT HOOKS
# ---------------------------------------------------------------------
try:
    import db as _db_module
except ImportError:
    _db_module = None

try:
    import settings as _settings_module
except ImportError:
    _settings_module = None

try:
    import ui_theme as _ui_theme
except ImportError:
    _ui_theme = None


def _get_connection():
    if _db_module is not None and hasattr(_db_module, "get_connection"):
        return _db_module.get_connection()
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultra_erp.db")
    return sqlite3.connect(db_path)


def _get_company_name():
    if _settings_module is not None and hasattr(_settings_module, "get_company_name"):
        return _settings_module.get_company_name()
    return "Company Name"


def _get_warehouse_address():
    if _settings_module is not None and hasattr(_settings_module, "get_warehouse_address"):
        return _settings_module.get_warehouse_address()
    return ""


def _get_logo_path():
    """Absolute path to the tenant's uploaded logo image, or None if
    they haven't set one. Lives next to their database file."""
    if _settings_module is None or not hasattr(_settings_module, "get_logo_filename"):
        return None
    filename = _settings_module.get_logo_filename()
    if not filename:
        return None
    path = os.path.join(_default_output_dir(), filename)
    return path if os.path.exists(path) else None


def _get_theme_colors():
    if _ui_theme is not None:
        try:
            return _ui_theme.get_colors()
        except Exception:
            pass
    return {"primary": "#2563eb", "primary_dark": "#1e40af", "light": "#eff6ff"}


def _default_output_dir():
    if _db_module is not None and hasattr(_db_module, "get_active_db_path"):
        return os.path.dirname(os.path.abspath(_db_module.get_active_db_path()))
    return os.path.dirname(os.path.abspath(__file__))


def fmt_amount(value):
    if value is None:
        value = 0
    return f"{value:,.2f}"


def _format_voucher_no(voucher_type, voucher_no):
    if _db_module is not None and hasattr(_db_module, "format_voucher_no"):
        return _db_module.format_voucher_no(voucher_type, voucher_no)
    prefix = {"SALE": "INV", "PURCHASE": "PINV", "RECEIPT": "RCPT", "PAYMENT": "PAY"}.get(voucher_type, "V")
    return f"{prefix}-{(voucher_no or 0):06d}"


# ---------------------------------------------------------------------
# amount-in-words (Pakistani/Indian lakh-crore style)
# ---------------------------------------------------------------------
_ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
         "Seventeen", "Eighteen", "Nineteen"]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digit_words(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three_digit_words(n):
    if n >= 100:
        return (_ONES[n // 100] + " Hundred" + (" " + _two_digit_words(n % 100) if n % 100 else "")).strip()
    return _two_digit_words(n)


def amount_to_words(amount):
    """Rupees, Indian/Pakistani numbering (lakh, crore). Ignores paisa."""
    try:
        rupees = int(round(float(amount)))
    except (TypeError, ValueError):
        return ""
    if rupees == 0:
        return "Zero Rupees only"
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000
    hundred_rest = rupees

    parts = []
    if crore:
        parts.append(_three_digit_words(crore) + " Crore")
    if lakh:
        parts.append(_three_digit_words(lakh) + " Lakh")
    if thousand:
        parts.append(_three_digit_words(thousand) + " Thousand")
    if hundred_rest:
        parts.append(_three_digit_words(hundred_rest))
    return " ".join(parts) + " Rupees only"


# ---------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------
styles = getSampleStyleSheet()


def _decode_signature_image(signature_data):
    """signature_data is a data URI like 'data:image/png;base64,....'
    (or None). Returns a reportlab Image flowable, or None if there's
    no signature / it fails to decode (never let a bad signature blob
    break printing the rest of the document)."""
    if not signature_data:
        return None
    try:
        header, b64 = signature_data.split(",", 1)
        img_bytes = base64.b64decode(b64)
        return Image(io.BytesIO(img_bytes), width=55 * mm, height=20 * mm, kind="proportional")
    except Exception:
        return None


def _fetch_transaction(cur, transaction_id):
    cur.execute(
        """
        SELECT t.id, t.date, t.voucher_type, t.voucher_no, t.do_no, t.party_id, t.broker,
               t.quality_id, t.qty, t.rate, t.amount, t.cash_or_cheque,
               t.cheque_no, t.description, t.credit_days, t.signature_data,
               p.name, p.city, p.phone, p.address, p.ntn, p.stn,
               q.name
        FROM transactions t
        LEFT JOIN parties p ON p.id = t.party_id
        LEFT JOIN quality q ON q.id = t.quality_id
        WHERE t.id = ?
        """,
        (transaction_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Transaction id {transaction_id} not found")
    keys = ["id", "date", "voucher_type", "voucher_no", "do_no", "party_id", "broker",
            "quality_id", "qty", "rate", "amount", "cash_or_cheque",
            "cheque_no", "description", "credit_days", "signature_data",
            "party_name", "party_city", "party_phone", "party_address",
            "party_ntn", "party_stn", "item_name"]
    return dict(zip(keys, row))


def _build_pdf(output_path, flow, pagesize=A4, margins=(15, 15, 15, 15)):
    top, bottom, left, right = margins
    doc = SimpleDocTemplate(
        output_path, pagesize=pagesize,
        topMargin=top * mm, bottomMargin=bottom * mm, leftMargin=left * mm, rightMargin=right * mm,
    )
    doc.build(flow)
    return output_path


class _ColorBar(Flowable):
    """A solid rectangle used as a full-width colored band or a thin accent line."""
    def __init__(self, width, height, color_hex):
        super().__init__()
        self.width = width
        self.height = height
        self.color = colors.HexColor(color_hex)

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def _elegant_table_style(accent_hex=None):
    """Quiet alternative to a solid-color-header table: a rule under
    the header row and thin horizontal-only rules between data rows,
    no vertical grid lines or filled backgrounds."""
    if accent_hex is None:
        accent_hex = _get_theme_colors()["primary_dark"]
    accent = colors.HexColor(accent_hex)
    return TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, accent),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#e5e3df")),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])


def _signature_block(width=180 * mm):
    tbl = Table(
        [["_______________________", "", "_______________________"],
         ["Prepared By", "", "Received / Approved By"]],
        colWidths=[width * 0.42, width * 0.16, width * 0.42],
    )
    tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 14 * mm),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.grey),
    ]))
    return tbl


# =======================================================================
# INVOICE FAMILY - Sale / Purchase D.O. Invoice
# =======================================================================
def _build_do_slip_copy(t, primary, primary_dark, copy_width, copy_label,
                         doc_label, party_role, warehouse_address, logo_path):
    """One copy (Office or Customer) of the D.O. slip, sized to fit
    half a landscape A4 page. Returns a list of flowables."""
    flow = []

    company_block_lines = [f'<font size="12"><b>{_get_company_name()}</b></font>',
                            f'<font size="8" color="{primary_dark}">{doc_label}</font>']
    if warehouse_address:
        company_block_lines.append(f'<font size="7" color="#666666">{warehouse_address}</font>')
    company_para = Paragraph("<br/>".join(company_block_lines),
                              ParagraphStyle("TopCo", parent=styles["Normal"], leading=11))

    if logo_path:
        try:
            logo_img = Image(logo_path, width=12 * mm, height=12 * mm, kind="proportional")
            company_left = Table([[logo_img, company_para]], colWidths=[14 * mm, copy_width * 0.62 - 14 * mm])
            company_left.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        except Exception:
            company_left = company_para
    else:
        company_left = company_para

    copy_badge = Table([[copy_label]], colWidths=[copy_width * 0.26])
    copy_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(primary)),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    top_table = Table(
        [[company_left, copy_badge,
          Table([["Sr."], [str(t["voucher_no"] or "-")]], colWidths=[copy_width * 0.16],
                style=TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (0, 0), 7),
                    ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (0, 1), 13),
                    ("TOPPADDING", (0, 0), (0, 0), 3), ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 1), (0, 1), 0), ("BOTTOMPADDING", (0, 1), (0, 1), 3),
                ]))]],
        colWidths=[copy_width * 0.58, copy_width * 0.26, copy_width * 0.16],
    )
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (2, 0), (2, 0), 1, colors.HexColor(primary)),
    ]))
    flow.append(top_table)
    flow.append(Spacer(1, 2 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor(primary), thickness=1))
    flow.append(Spacer(1, 3 * mm))

    label_style = ParagraphStyle("SlipLabelS", parent=styles["Normal"], fontSize=8,
                                  fontName="Helvetica", textColor=colors.HexColor("#666666"))
    value_style = ParagraphStyle("SlipValueS", parent=styles["Normal"], fontSize=9.5)

    def field_row(label, value_paragraph, label_width=0.26):
        row = Table(
            [[Paragraph(label, label_style), value_paragraph]],
            colWidths=[copy_width * label_width, copy_width * (1 - label_width)],
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LINEBELOW", (1, 0), (1, 0), 0.5, colors.HexColor("#dddddd")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        return row

    flow.append(field_row("Date", Paragraph(t["date"] or "-", value_style)))
    flow.append(Spacer(1, 1 * mm))
    flow.append(field_row(party_role, Paragraph(t["party_name"] or "-", value_style)))
    flow.append(Spacer(1, 1 * mm))
    qty_text = f'{t["qty"]:g} <font size="7" color="#666666">(bags/units)</font>' if t["qty"] else "-"
    flow.append(field_row("Quantity", Paragraph(qty_text, value_style)))
    flow.append(Spacer(1, 1 * mm))
    flow.append(field_row("Quality", Paragraph(t["item_name"] or "-", value_style)))
    flow.append(Spacer(1, 1 * mm))
    # The customer's own copy of a SALE delivery order doesn't show the
    # rate - whoever's physically receiving the goods (a driver, a
    # warehouse hand) doesn't need to see pricing; the office copy still
    # shows it for the business's own records. Purchase D.O.s show the
    # rate on both copies either way, since that's the agreed price with
    # the supplier, not sensitive in the same way.
    show_rate = not (copy_label == "CUSTOMER COPY" and t["voucher_type"] == "SALE")
    if show_rate:
        flow.append(field_row("Rate", Paragraph(fmt_amount(t["rate"]), value_style)))
        flow.append(Spacer(1, 1 * mm))
    flow.append(field_row("Broker", Paragraph(t["broker"] or "-", value_style)))
    flow.append(Spacer(1, 1 * mm))
    flow.append(field_row("D.O. No.", Paragraph(t["do_no"] or "-", value_style)))
    flow.append(Spacer(1, 1 * mm))
    flow.append(field_row("Credit Days", Paragraph(str(t["credit_days"]) if t["credit_days"] else "-", value_style)))

    if t["description"]:
        flow.append(Spacer(1, 3 * mm))
        flow.append(Paragraph(f"<b>Description:</b> {t['description']}",
                               ParagraphStyle("DescS", parent=value_style, fontSize=8)))

    flow.append(Spacer(1, 8 * mm))

    signature_image = _decode_signature_image(t.get("signature_data"))
    sig_font_size = 7
    if signature_image:
        signature_image.drawWidth = 30 * mm
        signature_image.drawHeight = 11 * mm
        sig_table = Table(
            [["____________________", "", signature_image],
             ["Signature Owner", "", "Signature Buyer (e-signed)"]],
            colWidths=[copy_width * 0.42, copy_width * 0.16, copy_width * 0.42],
        )
        sig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (2, 0), (2, 0), "BOTTOM"),
            ("FONTSIZE", (0, 1), (-1, 1), sig_font_size),
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#666666")),
            ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor(primary_dark)),
            ("FONTNAME", (2, 1), (2, 1), "Helvetica-Bold"),
        ]))
    else:
        sig_table = Table(
            [["____________________", "", "____________________"],
             ["Signature Owner", "", "Signature Buyer"]],
            colWidths=[copy_width * 0.42, copy_width * 0.16, copy_width * 0.42],
        )
        sig_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 1), (-1, 1), sig_font_size),
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#666666")),
        ]))
    flow.append(sig_table)
    return flow


def generate_do_invoice_pdf(transaction_id, output_path=None):
    """D.O. slip printed landscape on one A4 sheet with two identical
    copies side by side - one for the office's own records, one to
    hand to the customer - so both copies come off the printer at
    once. Modeled on the mill's own printed delivery order pad: boxed
    serial number, plain underlined fields (Quantity/Quality/etc.),
    and an Owner/Buyer signature line - the physical slip never showed
    money figures beyond the rate, which this keeps too."""
    conn = _get_connection()
    cur = conn.cursor()
    t = _fetch_transaction(cur, transaction_id)
    conn.close()

    if t["voucher_type"] not in ("SALE", "PURCHASE"):
        raise ValueError(f"Transaction {transaction_id} is a {t['voucher_type']}, not a SALE/PURCHASE")

    theme = _get_theme_colors()
    primary = theme["primary"]
    primary_dark = theme["primary_dark"]

    doc_label = "SALE D.O." if t["voucher_type"] == "SALE" else "PURCHASE D.O."
    party_role = "Party Name" if t["voucher_type"] == "SALE" else "Purchased From"
    voucher_str = _format_voucher_no(t["voucher_type"], t["voucher_no"])
    warehouse_address = _get_warehouse_address()
    logo_path = _get_logo_path()

    page_width = landscape(A4)[0] - 24 * mm  # 12mm margins each side
    copy_width = (page_width - 8 * mm) / 2  # 8mm gap between copies for the divider

    office_copy = _build_do_slip_copy(t, primary, primary_dark, copy_width, "OFFICE COPY",
                                       doc_label, party_role, warehouse_address, logo_path)
    customer_copy = _build_do_slip_copy(t, primary, primary_dark, copy_width, "CUSTOMER COPY",
                                         doc_label, party_role, warehouse_address, logo_path)

    combined = Table([[office_copy, customer_copy]], colWidths=[copy_width, copy_width])
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (0, 0), 0.75, colors.HexColor("#cccccc")),
        # split the divider gap evenly - see the identical fix/comment in
        # _build_receipt_payment_pdf
        ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
        ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
    ]))

    flow = [combined, Spacer(1, 4 * mm),
            HRFlowable(width="100%", color=colors.HexColor("#eeeeee"), thickness=0.5),
            Paragraph(f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} — {voucher_str}",
                      ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey))]

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), f"{voucher_str}_{t['voucher_type']}.pdf")
    return _build_pdf(output_path, flow, pagesize=landscape(A4), margins=(12, 12, 12, 12))


# =======================================================================
# VOUCHER FAMILY - Receipt / Payment
# =======================================================================
def _build_voucher_pdf(t, doc_label, party_role, amount_label, output_path_prefix):
    theme = _get_theme_colors()
    primary = theme["primary"]
    primary_dark = theme["primary_dark"]
    light = theme["light"]
    voucher_str = _format_voucher_no(t["voucher_type"], t["voucher_no"])

    page_width = A4[0] - 38 * mm
    flow = []

    stamp_table = Table(
        [[
            Paragraph(f'<font size="14"><b>{_get_company_name()}</b></font>',
                      ParagraphStyle("VCompany", parent=styles["Normal"])),
            Paragraph(f'<font color="white" size="11"><b>{voucher_str}</b></font>',
                      ParagraphStyle("VStamp", parent=styles["Normal"], alignment=TA_CENTER)),
        ]],
        colWidths=[page_width * 0.7, page_width * 0.3],
    )
    stamp_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor(primary_dark)),
        ("TOPPADDING", (1, 0), (1, 0), 8), ("BOTTOMPADDING", (1, 0), (1, 0), 8),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
    ]))
    flow.append(stamp_table)
    flow.append(_ColorBar(page_width, 2, primary))
    flow.append(Spacer(1, 8 * mm))

    title_table = Table(
        [[Paragraph(f'<font color="{primary_dark}" size="15"><b>{doc_label}</b></font>',
                    ParagraphStyle("VTitle", parent=styles["Normal"], alignment=TA_CENTER))]],
        colWidths=[page_width],
    )
    title_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(light)),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor(primary)),
    ]))
    flow.append(title_table)
    flow.append(Spacer(1, 8 * mm))

    value_style = ParagraphStyle("VVal", parent=styles["Normal"], fontSize=10.5)
    meta_rows = [
        ("Date", t["date"] or "-"), ("Mode", t["cash_or_cheque"] or "-"),
        (party_role, t["party_name"] or "-"), ("Cheque No.", t["cheque_no"] or "-"),
        ("City", t["party_city"] or "-"), ("", ""),
    ]
    meta_data = []
    for i in range(0, len(meta_rows), 2):
        left_pair, right_pair = meta_rows[i], meta_rows[i + 1]
        meta_data.append([
            Paragraph(f"<b>{left_pair[0]}:</b> {left_pair[1]}", value_style) if left_pair[0] else "",
            Paragraph(f"<b>{right_pair[0]}:</b> {right_pair[1]}", value_style) if right_pair[0] else "",
        ])
    meta_table = Table(meta_data, colWidths=[page_width * 0.5, page_width * 0.5])
    flow.append(meta_table)
    flow.append(Spacer(1, 8 * mm))

    amount_box = Table(
        [[Paragraph(f'<font size="10">{amount_label}</font>',
                    ParagraphStyle("AmtLbl", parent=styles["Normal"], alignment=TA_CENTER))],
         [Paragraph(f'<font color="{primary_dark}" size="20"><b>Rs. {fmt_amount(t["amount"])}</b></font>',
                    ParagraphStyle("AmtVal", parent=styles["Normal"], alignment=TA_CENTER))]],
        colWidths=[page_width],
    )
    amount_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor(primary)),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2), ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))
    flow.append(amount_box)
    flow.append(Spacer(1, 4 * mm))

    flow.append(Paragraph(f"<i>Amount in words: {amount_to_words(t['amount'])}</i>",
                           ParagraphStyle("VWords", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER)))
    if t["description"]:
        flow.append(Spacer(1, 3 * mm))
        flow.append(Paragraph(f"<b>Against:</b> {t['description']}",
                               ParagraphStyle("VAgainst", parent=value_style, alignment=TA_CENTER)))

    flow.append(Spacer(1, 16 * mm))
    flow.append(_signature_block(page_width))

    flow.append(Spacer(1, 8 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=0.5))
    flow.append(Paragraph(f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} — {voucher_str}",
                           ParagraphStyle("VFooter", parent=styles["Normal"], fontSize=7.5, textColor=colors.grey)))

    output_path = os.path.join(_default_output_dir(), f"{voucher_str}_{output_path_prefix}.pdf")
    return _build_pdf(output_path, flow, margins=(18, 18, 20, 20))


def _build_receipt_payment_copy(t, cheques, copy_width, copy_label, doc_label, party_role, amount_word,
                                 primary, primary_dark, logo_path):
    """One copy (Office or Customer) of the Receipt/Payment voucher,
    sized to fit half a landscape A4 page."""
    flow = []

    company_para = Paragraph(f'<font size="10.5"><b>{_get_company_name()}</b></font>',
                              ParagraphStyle("RVCo", parent=styles["Normal"]))
    if logo_path:
        try:
            logo_img = Image(logo_path, width=11 * mm, height=11 * mm, kind="proportional")
            company_cell = Table([[logo_img, company_para]], colWidths=[13 * mm, copy_width * 0.30])
            company_cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        except Exception:
            company_cell = company_para
    else:
        company_cell = company_para

    copy_badge = Table([[copy_label]], colWidths=[copy_width * 0.24])
    copy_badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(primary)),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    top_table = Table(
        [[company_cell, copy_badge,
          Table([["Sr."], [str(t["voucher_no"] or "-")]], colWidths=[copy_width * 0.16],
                style=TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (0, 0), 6.5),
                    ("FONTNAME", (0, 1), (0, 1), "Helvetica-Bold"), ("FONTSIZE", (0, 1), (0, 1), 11),
                    ("TOPPADDING", (0, 0), (0, 0), 2), ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 1), (0, 1), 0), ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ]))]],
        colWidths=[copy_width * 0.44, copy_width * 0.24, copy_width * 0.16],
    )
    top_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (2, 0), (2, 0), 1, colors.HexColor(primary)),
    ]))
    flow.append(top_table)
    flow.append(Spacer(1, 2 * mm))
    flow.append(Paragraph(f'<font color="{primary_dark}" size="10"><b>{doc_label}</b></font>',
                           ParagraphStyle("RVTitleS", parent=styles["Normal"])))
    flow.append(Spacer(1, 1.5 * mm))
    flow.append(HRFlowable(width="100%", color=colors.HexColor(primary), thickness=1))
    flow.append(Spacer(1, 3 * mm))

    meta_style = ParagraphStyle("RVMetaS", parent=styles["Normal"], fontSize=8.5)
    flow.append(Paragraph(f"<b>Date:</b> {t['date'] or '-'} &nbsp;&nbsp; "
                           f"<b>{party_role}:</b> {t['party_name'] or '-'}", meta_style))
    flow.append(Spacer(1, 3 * mm))

    cheque_data = [["Date", "Bank", "Cheque #", "Amount"]]
    if cheques:
        for c in cheques:
            cheque_data.append([c["date"] or t["date"] or "-", c["bank"] or "-",
                                 c["cheque_no"] or "-", fmt_amount(c["amount"])])
    else:
        mode = t["cash_or_cheque"] or "Cash"
        cheque_data.append([t["date"] or "-", mode, t["cheque_no"] or "-", fmt_amount(t["amount"])])
    cheque_data.append(["", "", "TOTAL", fmt_amount(t["amount"])])

    tbl = Table(cheque_data, colWidths=[copy_width * 0.22, copy_width * 0.28, copy_width * 0.26, copy_width * 0.24],
                repeatRows=1)
    tbl.setStyle(_elegant_table_style())
    tbl.setStyle(TableStyle([
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor(primary_dark)),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ]))
    flow.append(tbl)
    flow.append(Spacer(1, 3 * mm))

    flow.append(Paragraph(f"<i>Amount {amount_word} in words: {amount_to_words(t['amount'])}</i>",
                           ParagraphStyle("RVWordsS", parent=styles["Normal"], fontSize=7.5)))
    if t["description"]:
        flow.append(Spacer(1, 1.5 * mm))
        flow.append(Paragraph(f"<b>Against:</b> {t['description']}",
                               ParagraphStyle("RVAgainstS", parent=styles["Normal"], fontSize=8)))

    flow.append(Spacer(1, 9 * mm))
    signee_label = "Received by:" if t["voucher_type"] == "RECEIPT" else "Paid by:"
    sig_table = Table(
        [[Paragraph(f"<b>{signee_label}</b>", ParagraphStyle("RVSignLblS", parent=styles["Normal"], fontSize=8.5)),
          "__________________", "Sign."]],
        colWidths=[copy_width * 0.24, copy_width * 0.56, copy_width * 0.2],
    )
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (2, 0), (2, 0), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    flow.append(sig_table)
    return flow


def _build_receipt_payment_pdf(t, cheques, doc_label, party_role, amount_word, output_path_prefix):
    """Receipt/Payment voucher printed landscape on one A4 sheet with
    two identical copies side by side - one for the office, one for
    the customer - so both come off the printer together."""
    theme = _get_theme_colors()
    primary = theme["primary"]
    primary_dark = theme["primary_dark"]
    voucher_str = _format_voucher_no(t["voucher_type"], t["voucher_no"])
    logo_path = _get_logo_path()

    page_width = landscape(A4)[0] - 24 * mm
    copy_width = (page_width - 8 * mm) / 2

    office_copy = _build_receipt_payment_copy(t, cheques, copy_width, "OFFICE COPY", doc_label, party_role,
                                               amount_word, primary, primary_dark, logo_path)
    customer_copy = _build_receipt_payment_copy(t, cheques, copy_width, "CUSTOMER COPY", doc_label, party_role,
                                                 amount_word, primary, primary_dark, logo_path)

    combined = Table([[office_copy, customer_copy]], colWidths=[copy_width, copy_width])
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (0, 0), 0.75, colors.HexColor("#cccccc")),
        # split the divider gap evenly between both copies - giving it
        # entirely to one side (as this used to) makes that copy's
        # usable content area narrower than the other's, so despite
        # equal colWidths the two halves don't actually look the same size
        ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
        ("RIGHTPADDING", (0, 0), (0, 0), 4 * mm),
    ]))

    flow = [combined, Spacer(1, 4 * mm),
            HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=0.5),
            Paragraph(f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')} — {voucher_str}",
                      ParagraphStyle("RVFooter", parent=styles["Normal"], fontSize=7, textColor=colors.grey))]

    output_path = os.path.join(_default_output_dir(), f"{voucher_str}_{output_path_prefix}.pdf")
    return _build_pdf(output_path, flow, pagesize=landscape(A4), margins=(12, 12, 12, 12))


def generate_receipt_voucher_pdf(transaction_id, output_path=None):
    conn = _get_connection()
    cur = conn.cursor()
    t = _fetch_transaction(cur, transaction_id)
    cheques = _db_module.get_cheques_for_transaction(transaction_id, conn) if _db_module else []
    conn.close()
    if t["voucher_type"] != "RECEIPT":
        raise ValueError(f"Transaction {transaction_id} is a {t['voucher_type']}, not a RECEIPT")
    path = _build_receipt_payment_pdf(t, cheques, "RECEIPT VOUCHER", "Received From", "Received", "Receipt")
    if output_path:
        os.replace(path, output_path)
        return output_path
    return path


def generate_payment_voucher_pdf(transaction_id, output_path=None):
    conn = _get_connection()
    cur = conn.cursor()
    t = _fetch_transaction(cur, transaction_id)
    cheques = _db_module.get_cheques_for_transaction(transaction_id, conn) if _db_module else []
    conn.close()
    if t["voucher_type"] != "PAYMENT":
        raise ValueError(f"Transaction {transaction_id} is a {t['voucher_type']}, not a PAYMENT")
    path = _build_receipt_payment_pdf(t, cheques, "PAYMENT VOUCHER", "Paid To", "Paid", "PaymentVoucher")
    if output_path:
        os.replace(path, output_path)
        return output_path
    return path


def generate_expense_voucher_pdf(transaction_id, output_path=None):
    """Home/Office Expense voucher - visually part of the 'money going
    out' voucher family, same as Payment."""
    conn = _get_connection()
    cur = conn.cursor()
    t = _fetch_transaction(cur, transaction_id)
    conn.close()
    if t["voucher_type"] != "EXPENSE":
        raise ValueError(f"Transaction {transaction_id} is a {t['voucher_type']}, not an EXPENSE")
    path = _build_voucher_pdf(t, "EXPENSE VOUCHER", "Category", "AMOUNT SPENT", "ExpenseVoucher")
    if output_path:
        os.replace(path, output_path)
        return output_path
    return path


def generate_capital_voucher_pdf(transaction_id, output_path=None):
    """Capital In/Out voucher - In looks like a Receipt, Out looks like
    a Payment, sharing the same voucher-family layout."""
    conn = _get_connection()
    cur = conn.cursor()
    t = _fetch_transaction(cur, transaction_id)
    conn.close()
    if t["voucher_type"] not in ("CAPITAL_IN", "CAPITAL_OUT"):
        raise ValueError(f"Transaction {transaction_id} is a {t['voucher_type']}, not a CAPITAL entry")
    if t["voucher_type"] == "CAPITAL_IN":
        path = _build_voucher_pdf(t, "CAPITAL INTRODUCED", "Account", "AMOUNT INTRODUCED", "CapitalIn")
    else:
        path = _build_voucher_pdf(t, "CAPITAL WITHDRAWN", "Account", "AMOUNT WITHDRAWN", "CapitalOut")
    if output_path:
        os.replace(path, output_path)
        return output_path
    return path


# =======================================================================
# convenience dispatcher
# =======================================================================
def generate_voucher_pdf(transaction_id, output_path=None):
    """Looks up the transaction's voucher_type and calls the matching
    generator above."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT voucher_type FROM transactions WHERE id = ?", (transaction_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Transaction id {transaction_id} not found")
    v_type = row[0]
    if v_type in ("SALE", "PURCHASE"):
        return generate_do_invoice_pdf(transaction_id, output_path)
    elif v_type == "RECEIPT":
        return generate_receipt_voucher_pdf(transaction_id, output_path)
    elif v_type == "PAYMENT":
        return generate_payment_voucher_pdf(transaction_id, output_path)
    elif v_type == "EXPENSE":
        return generate_expense_voucher_pdf(transaction_id, output_path)
    elif v_type in ("CAPITAL_IN", "CAPITAL_OUT"):
        return generate_capital_voucher_pdf(transaction_id, output_path)
    raise ValueError(f"Unknown voucher_type: {v_type}")


if __name__ == "__main__":
    print("This module is meant to be imported from transaction_form.py / recovery_form.py.")
    print("Example: python -c \"import voucher_print; voucher_print.generate_voucher_pdf(1)\"")
