"""
pdf_export.py
--------------
PDF generation for ULTRA ERP.

This file assumes the project layout described in the ULTRA ERP reference
document:

    db.py        -> exposes get_connection() returning a sqlite3.Connection
                     to ultra_erp.db
    settings.py  -> exposes get_company_name() returning the company name
                     string to print on report headers

If your actual db.py / settings.py use different function names, just
adjust the two lines under "PROJECT HOOKS" below - everything else in
this file is self-contained.

WHAT THIS FILE ADDS
--------------------
Printable (PDF) versions of every report in reports_form.py:

    generate_cash_book_pdf(date_from, date_to, output_path=None)
    generate_party_ledger_pdf(party_id, date_from=None, date_to=None, output_path=None)
    generate_receivable_payable_pdf(as_of_date=None, output_path=None)
    generate_trial_balance_pdf(output_path=None)
    generate_stock_report_pdf(output_path=None)

Each function returns the path to the generated PDF file. If output_path
is not given, a sensible default filename is built and the file is placed
next to ultra_erp.db (same folder db.py resolves).

For per-transaction printable vouchers (Sale/Purchase D.O., Receipt,
Payment/Cash Voucher) see voucher_print.py - those are separate documents,
not part of a ledger, and are generated one-per-transaction.

INTEGRATION
-----------
In reports_form.py, each tab (Cash Book / Ledger / Balance Sheet / Stock)
should already have a "generate report" button. Add a second button next
to it, e.g.:

    import pdf_export

    def on_print_cash_book():
        path = pdf_export.generate_cash_book_pdf(date_from_var.get(), date_to_var.get())
        messagebox.showinfo("Saved", f"Cash Book PDF saved to:\\n{path}")
        os.startfile(path)   # Windows: opens the PDF in the default viewer
        # on Mac use: subprocess.run(["open", path])

    tk.Button(tab_cashbook, text="Print / Save PDF", command=on_print_cash_book).pack()
"""

import os
import sqlite3
from datetime import datetime, date as date_cls

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, HRFlowable, KeepTogether
)

# ---------------------------------------------------------------------
# PROJECT HOOKS - adjust these two lines if your real module names differ
# ---------------------------------------------------------------------
try:
    import db as _db_module          # db.get_connection()
except ImportError:
    _db_module = None

try:
    import settings as _settings_module   # settings.get_company_name()
except ImportError:
    _settings_module = None

try:
    import ui_theme as _ui_theme
except ImportError:
    _ui_theme = None


def _get_connection():
    if _db_module is not None and hasattr(_db_module, "get_connection"):
        return _db_module.get_connection()
    # fallback: look for ultra_erp.db next to this file
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultra_erp.db")
    return sqlite3.connect(db_path)


def _get_company_name():
    if _settings_module is not None and hasattr(_settings_module, "get_company_name"):
        return _settings_module.get_company_name()
    return "Company Name"


def _get_theme_colors():
    if _ui_theme is not None:
        try:
            return _ui_theme.get_colors()
        except Exception:
            pass
    return {"primary": "#2563eb", "primary_dark": "#1e40af", "light": "#eff6ff"}


def _format_voucher_no(voucher_type, voucher_no):
    if _db_module is not None and hasattr(_db_module, "format_voucher_no"):
        return _db_module.format_voucher_no(voucher_type, voucher_no)
    prefix = {"SALE": "INV", "PURCHASE": "PINV", "RECEIPT": "RCPT", "PAYMENT": "PAY"}.get(voucher_type, "V")
    return f"{prefix}-{(voucher_no or 0):06d}"


def _default_output_dir():
    if _db_module is not None and hasattr(_db_module, "get_active_db_path"):
        return os.path.dirname(os.path.abspath(_db_module.get_active_db_path()))
    return os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------
# shared formatting helpers
# ---------------------------------------------------------------------
def fmt_amount(value):
    if value is None:
        value = 0
    return f"{value:,.2f}"


def fmt_date(value):
    if not value:
        return ""
    return str(value)


styles = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle(
    "TitleStyle", parent=styles["Title"], fontSize=15, spaceAfter=2, alignment=TA_CENTER
)
SUB_STYLE = ParagraphStyle(
    "SubStyle", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, textColor=colors.grey
)
SECTION_STYLE = ParagraphStyle(
    "SectionStyle", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4
)
SMALL_RIGHT = ParagraphStyle("SmallRight", parent=styles["Normal"], fontSize=9, alignment=TA_RIGHT)


def _header_flowables(report_title, subtitle=None):
    flow = [
        Paragraph(_get_company_name(), TITLE_STYLE),
        Paragraph(report_title, ParagraphStyle("RT", parent=styles["Heading2"], alignment=TA_CENTER, spaceAfter=2)),
    ]
    if subtitle:
        flow.append(Paragraph(subtitle, SUB_STYLE))
    flow.append(Spacer(1, 4 * mm))
    flow.append(HRFlowable(width="100%", color=colors.black, thickness=1))
    flow.append(Spacer(1, 3 * mm))
    return flow


def _footer_flowables():
    return [
        Spacer(1, 6 * mm),
        HRFlowable(width="100%", color=colors.grey, thickness=0.5),
        Paragraph(
            f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}",
            ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey),
        ),
    ]


def _build_pdf(output_path, flowables, landscape_mode=False):
    from reportlab.lib.pagesizes import landscape
    pagesize = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(
        output_path, pagesize=pagesize,
        topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
    )
    doc.build(flowables)
    return output_path


def _standard_table_style(header_bg=None):
    if header_bg is None:
        header_bg = colors.HexColor(_get_theme_colors()["primary_dark"])
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbbbbb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6fa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])


def _elegant_table_style(accent=None):
    """A quieter alternative to _standard_table_style: no solid header
    fill, just a rule under the header row in the theme color, thin
    horizontal-only rules between rows (no vertical grid lines), and
    generous padding. Used for the ledgers and vouchers, which read
    better as clean statements than as boxed spreadsheets."""
    if accent is None:
        accent = colors.HexColor(_get_theme_colors()["primary_dark"])
    return TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, 0), accent),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("LINEBELOW", (0, 0), (-1, 0), 1, accent),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, colors.HexColor("#e5e3df")),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])


# =======================================================================
# 1. CASH BOOK (T-account: Debit left / Credit right)
# =======================================================================
def generate_cash_book_pdf(date_from, date_to, output_path=None):
    """
    Classic two-column T-account. Right side (Credit / money in):
    Opening Balance, Receipts, Capital Introduced. Left side (Debit /
    money out): Payments, Capital Withdrawn, Expense vouchers. Each
    entry carries its own reference (voucher) number. See
    db.get_cash_taccount() for the balancing logic.
    """
    if _db_module is None or not hasattr(_db_module, "get_cash_taccount"):
        raise RuntimeError("db.get_cash_taccount() not available - update db.py")

    t = _db_module.get_cash_taccount(date_from, date_to)

    flow = _header_flowables("Cash Book", f"{fmt_date(date_from)} to {fmt_date(date_to)}")

    cell_style = ParagraphStyle("cbcell", parent=styles["Normal"], fontSize=8)
    header_row = ["Ref #", "Date", "Account", "Remarks", "Amount"]

    debit_rows = [header_row] + [
        [e["ref"], fmt_date(e["date"]), Paragraph(e["party"], cell_style),
         Paragraph(e.get("remarks") or "", cell_style), fmt_amount(e["amount"])]
        for e in t["debit_entries"]
    ]
    debit_rows.append(["", "", "", "TOTAL", fmt_amount(t["total_debit"])])

    credit_rows = [header_row] + [
        [e["ref"], fmt_date(e["date"]), Paragraph(e["party"], cell_style),
         Paragraph(e.get("remarks") or "", cell_style), fmt_amount(e["amount"])]
        for e in t["credit_entries"]
    ]
    credit_rows.append(["", "", "", "TOTAL", fmt_amount(t["total_credit"])])

    # pad the shorter side with blank rows so both tables are the same
    # height and sit level with each other on the page
    while len(debit_rows) < len(credit_rows):
        debit_rows.insert(-1, ["", "", "", "", ""])
    while len(credit_rows) < len(debit_rows):
        credit_rows.insert(-1, ["", "", "", "", ""])

    col_w = [22 * mm, 16 * mm, 26 * mm, 26 * mm, 20 * mm]
    debit_tbl = Table(debit_rows, colWidths=col_w, repeatRows=1)
    debit_tbl.setStyle(_standard_table_style())
    debit_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))
    credit_tbl = Table(credit_rows, colWidths=col_w, repeatRows=1)
    credit_tbl.setStyle(_standard_table_style())
    credit_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (4, 1), (4, -1), "RIGHT"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))

    side_labels = Table(
        [[Paragraph("<b>BANAAM (money out)</b>", ParagraphStyle("DrLbl", parent=styles["Normal"], alignment=TA_CENTER)),
          Paragraph("<b>JAMA (money in)</b>", ParagraphStyle("CrLbl", parent=styles["Normal"], alignment=TA_CENTER))]],
        colWidths=[sum(col_w), sum(col_w)],
    )
    side_labels.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_get_theme_colors()["light"])),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(side_labels)
    flow.append(Spacer(1, 2 * mm))

    combined = Table([[debit_tbl, credit_tbl]], colWidths=[sum(col_w) + 2 * mm, sum(col_w) + 2 * mm])
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEAFTER", (0, 0), (0, 0), 1, colors.black),
        ("LEFTPADDING", (1, 0), (1, 0), 6),
    ]))
    flow.append(combined)

    flow.append(Spacer(1, 5 * mm))
    flow.append(Paragraph(
        f"Opening Balance: Rs. {fmt_amount(t['opening_balance'])}   |   "
        f"<b>Closing Balance: Rs. {fmt_amount(t['closing_balance'])}</b>",
        ParagraphStyle("CBTotals", parent=styles["Normal"], fontSize=10)))
    flow.extend(_footer_flowables())

    if output_path is None:
        output_path = os.path.join(
            _default_output_dir(), f"CashBook_{date_from}_to_{date_to}.pdf"
        )
    return _build_pdf(output_path, flow, landscape_mode=True)


# =======================================================================
# 2. PARTY LEDGER
# =======================================================================
def generate_party_ledger_pdf(party_id, date_from=None, date_to=None, output_path=None):
    """
    Prints the full running-balance ledger for one party (all voucher
    types affecting them: SALE, PURCHASE, RECEIPT, PAYMENT), optionally
    restricted to a date range. Opening balance is carried in as the
    starting row.
    """
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, city, phone, ntn, stn, address, opening_balance, party_type FROM parties WHERE id = ?", (party_id,))
    party = cur.fetchone()
    if not party:
        conn.close()
        raise ValueError(f"Party id {party_id} not found")
    name, city, phone, ntn, stn, address, opening_balance, party_type = party

    query = """
        SELECT t.date, t.voucher_type, t.voucher_no, t.do_no, q.name, t.qty, t.amount, t.description
        FROM transactions t
        LEFT JOIN quality q ON q.id = t.quality_id
        WHERE t.party_id = ?
    """
    params = [party_id]
    if date_from and date_to:
        query += " AND t.date BETWEEN ? AND ?"
        params += [date_from, date_to]
    query += " ORDER BY t.date, t.id"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    subtitle = f"{city or ''}"
    if date_from and date_to:
        subtitle += f" &nbsp;|&nbsp; {fmt_date(date_from)} to {fmt_date(date_to)}"
    flow = _header_flowables(f"Party Ledger — {name}", subtitle)

    info_lines = []
    if phone:
        info_lines.append(f"Phone: {phone}")
    if ntn:
        info_lines.append(f"NTN: {ntn}")
    if stn:
        info_lines.append(f"STN: {stn}")
    if address:
        info_lines.append(f"Address: {address}")
    if info_lines:
        flow.append(Paragraph(" &nbsp;&nbsp;|&nbsp;&nbsp; ".join(info_lines),
                               ParagraphStyle("Info", parent=styles["Normal"], fontSize=9)))
        flow.append(Spacer(1, 3 * mm))

    table_data = [["Date", "Reference", "Voucher", "D.O. #", "Item", "Qty", "Debit", "Credit", "Balance"]]
    balance = opening_balance or 0.0
    table_data.append(["Opening Balance", "", "", "", "", "", "", "", fmt_amount(balance)])

    total_debit = 0.0
    total_credit = 0.0

    for r in rows:
        t_date, v_type, voucher_no, do_no, item_name, qty, amount, desc = r
        amount = amount or 0
        ref = _format_voucher_no(v_type, voucher_no)
        if v_type in ("SALE", "PAYMENT"):
            debit, credit = amount, 0
            balance += amount
            total_debit += amount
        else:  # PURCHASE, RECEIPT
            debit, credit = 0, amount
            balance -= amount
            total_credit += amount
        table_data.append([
            fmt_date(t_date), ref, v_type, do_no or "-", item_name or "-",
            f"{qty:g}" if qty else "-",
            fmt_amount(debit) if debit else "", fmt_amount(credit) if credit else "",
            fmt_amount(balance),
        ])

    table_data.append(["", "", "", "", "", "TOTAL", fmt_amount(total_debit), fmt_amount(total_credit), fmt_amount(balance)])

    col_widths = [18 * mm, 20 * mm, 16 * mm, 18 * mm, 28 * mm, 12 * mm, 20 * mm, 20 * mm, 22 * mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_standard_table_style())
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Oblique"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (5, 1), (8, -1), "RIGHT"),
        ("SPAN", (0, 1), (7, 1)),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
    ]))
    flow.append(tbl)

    status = "Receivable (owes you)" if balance > 0 else ("Payable (you owe)" if balance < 0 else "Settled")
    flow.append(Spacer(1, 4 * mm))
    flow.append(Paragraph(f"Closing status: <b>{status}</b> — Rs. {fmt_amount(abs(balance))}",
                           ParagraphStyle("Status", parent=styles["Normal"], fontSize=10)))
    flow.extend(_footer_flowables())

    if output_path is None:
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in " _-").strip().replace(" ", "_")
        output_path = os.path.join(_default_output_dir(), f"Ledger_{safe_name}_{party_id}.pdf")
    return _build_pdf(output_path, flow)


# =======================================================================
# 3. RECEIVABLE & PAYABLE (BALANCE SHEET)
# =======================================================================
def generate_receivable_payable_pdf(as_of_date=None, output_path=None):
    """
    Two-column report: parties with positive balance (Receivable) vs
    negative balance (Payable), as of a given date (defaults to today,
    i.e. all transactions).
    """
    if as_of_date is None:
        as_of_date = date_cls.today().isoformat()

    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, opening_balance, party_type FROM parties WHERE is_gl = 0 ORDER BY name")
    parties = cur.fetchall()

    receivables, payables = [], []
    total_receivable, total_payable = 0.0, 0.0

    for party_id, name, opening_balance, party_type in parties:
        cur.execute(
            """
            SELECT voucher_type, SUM(amount) FROM transactions
            WHERE party_id = ? AND date <= ?
            GROUP BY voucher_type
            """,
            (party_id, as_of_date),
        )
        sums = {row[0]: (row[1] or 0) for row in cur.fetchall()}
        balance = (opening_balance or 0) + sums.get("SALE", 0) + sums.get("PAYMENT", 0) \
            - sums.get("PURCHASE", 0) - sums.get("RECEIPT", 0)
        if abs(balance) < 0.005:
            continue
        if balance > 0:
            receivables.append((name, balance))
            total_receivable += balance
        else:
            payables.append((name, -balance))
            total_payable += -balance
    conn.close()

    flow = _header_flowables("Receivable & Payable Statement", f"As of {fmt_date(as_of_date)}")

    max_len = max(len(receivables), len(payables), 1)
    receivables += [("", "")] * (max_len - len(receivables))
    payables += [("", "")] * (max_len - len(payables))

    table_data = [["Receivable (owes you)", "Amount", "Payable (you owe)", "Amount"]]
    for (rname, ramt), (pname, pamt) in zip(receivables, payables):
        table_data.append([
            rname, fmt_amount(ramt) if ramt != "" else "",
            pname, fmt_amount(pamt) if pamt != "" else "",
        ])
    table_data.append(["TOTAL", fmt_amount(total_receivable), "TOTAL", fmt_amount(total_payable)])

    col_widths = [55 * mm, 30 * mm, 55 * mm, 30 * mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_standard_table_style())
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
    ]))
    flow.append(tbl)

    net = total_receivable - total_payable
    flow.append(Spacer(1, 4 * mm))
    flow.append(Paragraph(
        f"Net position: <b>{'Receivable' if net >= 0 else 'Payable'} of Rs. {fmt_amount(abs(net))}</b>",
        ParagraphStyle("Net", parent=styles["Normal"], fontSize=10)))
    flow.extend(_footer_flowables())

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), f"ReceivablePayable_{as_of_date}.pdf")
    return _build_pdf(output_path, flow)


# =======================================================================
# 4. TRIAL BALANCE (all-time, all parties)
# =======================================================================
def generate_trial_balance_pdf(output_path=None):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, opening_balance FROM parties WHERE is_gl = 0 ORDER BY name")
    parties = cur.fetchall()

    table_data = [["Party", "Debit (Sale + Payment)", "Credit (Purchase + Receipt)", "Balance"]]
    total_debit, total_credit, total_balance = 0.0, 0.0, 0.0

    for party_id, name, opening_balance in parties:
        cur.execute(
            "SELECT voucher_type, SUM(amount) FROM transactions WHERE party_id = ? GROUP BY voucher_type",
            (party_id,),
        )
        sums = {row[0]: (row[1] or 0) for row in cur.fetchall()}
        debit = (opening_balance or 0 if (opening_balance or 0) > 0 else 0) + sums.get("SALE", 0) + sums.get("PAYMENT", 0)
        credit = (abs(opening_balance) if (opening_balance or 0) < 0 else 0) + sums.get("PURCHASE", 0) + sums.get("RECEIPT", 0)
        balance = (opening_balance or 0) + sums.get("SALE", 0) + sums.get("PAYMENT", 0) \
            - sums.get("PURCHASE", 0) - sums.get("RECEIPT", 0)
        if debit == 0 and credit == 0 and (opening_balance or 0) == 0:
            continue
        total_debit += debit
        total_credit += credit
        total_balance += balance
        table_data.append([name, fmt_amount(debit), fmt_amount(credit), fmt_amount(balance)])

    conn.close()
    table_data.append(["TOTAL", fmt_amount(total_debit), fmt_amount(total_credit), fmt_amount(total_balance)])

    flow = _header_flowables("Trial Balance", "All parties, all-time")
    col_widths = [55 * mm, 45 * mm, 45 * mm, 34 * mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_standard_table_style())
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    flow.append(tbl)
    flow.extend(_footer_flowables())

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), "TrialBalance.pdf")
    return _build_pdf(output_path, flow)


# =======================================================================
# 5. STOCK REPORT
# =======================================================================
def generate_stock_report_pdf(output_path=None):
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, city_area, purchase_rate, sale_rate, opening_balance FROM quality ORDER BY name")
    items = cur.fetchall()

    table_data = [["Item / Quality", "Area", "Purch. Rate", "Sale Rate", "Opening Qty", "Purchased", "Sold", "Closing Qty"]]
    total_closing = 0.0

    for q_id, name, city_area, purchase_rate, sale_rate, opening_balance in items:
        cur.execute(
            "SELECT voucher_type, SUM(qty) FROM transactions WHERE quality_id = ? GROUP BY voucher_type",
            (q_id,),
        )
        sums = {row[0]: (row[1] or 0) for row in cur.fetchall()}
        purchased = sums.get("PURCHASE", 0)
        sold = sums.get("SALE", 0)
        closing = (opening_balance or 0) + purchased - sold
        total_closing += closing
        table_data.append([
            name, city_area or "-", fmt_amount(purchase_rate), fmt_amount(sale_rate),
            f"{(opening_balance or 0):g}", f"{purchased:g}", f"{sold:g}", f"{closing:g}",
        ])

    conn.close()
    table_data.append(["", "", "", "", "", "", "TOTAL", f"{total_closing:g}"])

    flow = _header_flowables("Stock Report", f"As of {date_cls.today().isoformat()}")
    col_widths = [35 * mm, 22 * mm, 20 * mm, 20 * mm, 20 * mm, 18 * mm, 18 * mm, 20 * mm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(_standard_table_style())
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
    ]))
    flow.append(tbl)
    flow.extend(_footer_flowables())

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), "StockReport.pdf")
    return _build_pdf(output_path, flow)


# =======================================================================
# 6. RECEIVABLE LEDGER (grouped by party, net of all payments - FIFO)
# =======================================================================
def _generate_aging_ledger_pdf(title, subtitle_label, aging_rows, voucher_type, filename, output_path=None):
    """Shared renderer for the Receivable and Payable ledgers.

    Portrait A4, laid out newspaper-style in two fixed-width columns
    side by side (left, then right). Each PARTY gets its own compact
    block - name, a small table of their outstanding invoices, and a
    subtotal - never split across a wide row the way a normal table
    would. A party's block only grows taller as they have more
    invoices; the column width never changes. Once a page's two
    columns are full, parties keep flowing onto the next page the same
    way, automatically.
    """
    theme = _get_theme_colors()
    accent = colors.HexColor(theme["primary_dark"])
    light_bg = colors.HexColor(theme["light"])

    parties_seen = []
    by_party = {}
    for r in aging_rows:
        key = r["party_id"]
        if key not in by_party:
            by_party[key] = []
            parties_seen.append(key)
        by_party[key].append(r)

    # phone numbers aren't part of the aging data itself - one small
    # lookup covering every party on this report at once
    phones = {}
    if _db_module is not None and parties_seen:
        conn = _db_module.get_connection()
        cur = conn.cursor()
        placeholders = ",".join("?" * len(parties_seen))
        cur.execute(f"SELECT id, phone FROM parties WHERE id IN ({placeholders})", parties_seen)
        phones = {pid: phone for pid, phone in cur.fetchall()}
        conn.close()

    grand_total = 0.0
    grand_overdue = 0.0

    party_name_style = ParagraphStyle("PartyColName", parent=styles["Normal"], fontSize=8.3,
                                       fontName="Helvetica-Bold", textColor=accent, spaceBefore=7, spaceAfter=2)
    cell_style = ParagraphStyle("AgeColCell", parent=styles["Normal"], fontSize=6.3, leading=7.4)
    cell_style_red = ParagraphStyle("AgeColCellRed", parent=cell_style, textColor=colors.red)
    phone_style = ParagraphStyle("AgeColPhone", parent=styles["Normal"], fontSize=6.3, textColor=colors.grey)

    story = []
    for party_id in parties_seen:
        rows_for_party = by_party[party_id]
        party_name = rows_for_party[0]["party_name"]
        party_total = sum(r["outstanding"] for r in rows_for_party)
        party_overdue = sum(r["outstanding"] for r in rows_for_party if r["is_overdue"])
        grand_total += party_total
        grand_overdue += party_overdue

        table_data = [["Ref #", "Date", "Item", "Amt", "Status"]]
        row_is_overdue = [False]
        for r in rows_for_party:
            inv_no = r.get("voucher_display") or _format_voucher_no(voucher_type, r["voucher_no"])
            status_text = (f"{r['days']}d OD" if r["is_overdue"]
                            else "Today" if r["status"] == "Due today"
                            else f"OK {r['days']}d")
            style = cell_style_red if r["is_overdue"] else cell_style
            table_data.append([
                Paragraph(inv_no, style), fmt_date(r["date"])[5:] if fmt_date(r["date"]) else "-",
                Paragraph(r["item_name"] or "-", style),
                fmt_amount(r["outstanding"]), Paragraph(status_text, style),
            ])
            row_is_overdue.append(r["is_overdue"])

        phone = phones.get(party_id)
        subtotal_label = Paragraph(f"Ph: {phone}" if phone else "", phone_style)
        table_data.append([subtotal_label, "", "Subtotal", fmt_amount(party_total), ""])
        row_is_overdue.append(False)

        col_w = [16 * mm, 9 * mm, 20 * mm, 16 * mm, 13 * mm]  # fixed - never changes regardless of row count
        party_table = Table(table_data, colWidths=col_w, repeatRows=1)
        style_cmds = [
            ("SPAN", (0, -1), (1, -1)),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 6.3),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), accent),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("FONTSIZE", (0, 1), (-1, -1), 6.3),
            ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.HexColor("#e5e3df")),
            ("LINEABOVE", (0, -1), (-1, -1), 0.75, accent),
            ("FONTNAME", (2, -1), (3, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), light_bg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2.5), ("RIGHTPADDING", (0, 0), (-1, -1), 2.5),
        ]
        party_table.setStyle(TableStyle(style_cmds))

        block = [Paragraph(party_name, party_name_style), party_table]
        # KeepTogether does its best to avoid splitting a party's block
        # across the column boundary - if a party genuinely has too many
        # invoices to fit in one column's remaining height, ReportLab
        # still flows it rather than erroring, it just starts the block
        # at the top of the next column/page instead of straining to
        # keep it together, which is the same "grow vertically, never
        # sideways" behavior asked for.
        story.append(KeepTogether(block))

    total_line = (f"<b>Grand Total Outstanding: Rs. {fmt_amount(grand_total)}</b>"
                  + (f'  <font color="red">(Overdue: Rs. {fmt_amount(grand_overdue)})</font>' if grand_overdue else ""))

    def _draw_header(canvas, doc, continued=False):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawCentredString(A4[0] / 2, A4[1] - 16 * mm, _get_company_name())
        canvas.setFont("Helvetica-Bold", 10.5)
        header_title = f"{title} (continued)" if continued else title
        canvas.drawCentredString(A4[0] / 2, A4[1] - 22 * mm, header_title)
        if not continued:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawCentredString(A4[0] / 2, A4[1] - 27 * mm, subtitle_label)
        canvas.setStrokeColor(colors.black)
        canvas.line(15 * mm, A4[1] - 30 * mm, A4[0] - 15 * mm, A4[1] - 30 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(15 * mm, 10 * mm, f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def _on_first_page(canvas, doc):
        _draw_header(canvas, doc, continued=False)

    def _on_later_pages(canvas, doc):
        _draw_header(canvas, doc, continued=True)

    margin = 15 * mm
    gutter = 8 * mm
    top_margin = 34 * mm
    bottom_margin = 16 * mm
    col_width = (A4[0] - 2 * margin - gutter) / 2
    frame_height = A4[1] - top_margin - bottom_margin

    left_frame = Frame(margin, bottom_margin, col_width, frame_height, id="left",
                        leftPadding=0, rightPadding=6, topPadding=0, bottomPadding=0)
    right_frame = Frame(margin + col_width + gutter, bottom_margin, col_width, frame_height, id="right",
                         leftPadding=6, rightPadding=0, topPadding=0, bottomPadding=0)

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), filename)

    doc = BaseDocTemplate(output_path, pagesize=A4,
                           leftMargin=margin, rightMargin=margin,
                           topMargin=top_margin, bottomMargin=bottom_margin)

    def _on_page(canvas, doc):
        if canvas.getPageNumber() == 1:
            _on_first_page(canvas, doc)
        else:
            _on_later_pages(canvas, doc)

    doc.addPageTemplates([
        PageTemplate(id="Aging", frames=[left_frame, right_frame], onPage=_on_page),
    ])

    story.append(Paragraph(total_line, ParagraphStyle("AgeTotalsCol", parent=styles["Normal"], fontSize=8, spaceBefore=6)))
    doc.build(story)
    return output_path


def generate_receivable_ledger_pdf(as_of_date=None, output_path=None):
    """Every SALE invoice still outstanding as of as_of_date, net of
    every RECEIPT posted against that party (oldest invoice paid
    first), grouped by party with a subtotal each - this is the true,
    up-to-date amount customers currently owe, not just a raw list of
    every sale ever made. Each line still shows item/qty/rate, credit
    days, due date, and Not due / Due today / Overdue status."""
    if _db_module is None or not hasattr(_db_module, "get_receivable_aging"):
        raise RuntimeError("db.get_receivable_aging() not available - update db.py")

    as_of = as_of_date or date_cls.today().isoformat()
    aging_rows = _db_module.get_receivable_aging(as_of)
    return _generate_aging_ledger_pdf(
        "Receivable Ledger", f"Outstanding sale invoices, net of receipts — as of {fmt_date(as_of)}",
        aging_rows, "SALE", "ReceivableLedger.pdf", output_path,
    )


# =======================================================================
# 7. PAYABLE LEDGER (grouped by party, net of all payments - FIFO)
# =======================================================================
def generate_payable_ledger_pdf(as_of_date=None, output_path=None):
    """Same idea for the other side of the ledger: every PURCHASE
    invoice still outstanding, net of every PAYMENT, oldest-first."""
    if _db_module is None or not hasattr(_db_module, "get_payable_aging"):
        raise RuntimeError("db.get_payable_aging() not available - update db.py")

    as_of = as_of_date or date_cls.today().isoformat()
    aging_rows = _db_module.get_payable_aging(as_of)
    return _generate_aging_ledger_pdf(
        "Payable Ledger", f"Outstanding purchase invoices, net of payments — as of {fmt_date(as_of)}",
        aging_rows, "PURCHASE", "PayableLedger.pdf", output_path,
    )


# =======================================================================
# 8. PROFIT & CAPITAL SUMMARY
# =======================================================================
def generate_profit_report_pdf(date_from, date_to, output_path=None):
    """Gross Profit = Total Sales - Total Purchases for the period.
    Net Profit = Gross Profit - Home Expense - Office Expense for the
    same period. Also lists Capital In/Out entries (all-time, since
    capital is a running balance, not a period figure)."""
    if _db_module is None or not hasattr(_db_module, "get_profit_summary"):
        raise RuntimeError("db.get_profit_summary() not available - update db.py")

    profit = _db_module.get_profit_summary(date_from, date_to)
    capital = _db_module.get_capital_summary()

    flow = _header_flowables("Profit & Capital Summary", f"{fmt_date(date_from)} to {fmt_date(date_to)}")

    profit_data = [
        ["Total Sales", fmt_amount(profit["total_sales"])],
        ["Total Purchases", fmt_amount(profit["total_purchases"])],
        ["Opening Stock Value (at purchase rate)", fmt_amount(profit["opening_stock_value"])],
        ["Closing Stock Value (at purchase rate)", fmt_amount(profit["closing_stock_value"])],
        ["Cost of Goods Sold", fmt_amount(profit["cogs"])],
        ["Gross Profit (Sales − COGS)", fmt_amount(profit["gross_profit"])],
        ["Home Expense", fmt_amount(profit["home_expense"])],
        ["Office Expense", fmt_amount(profit["office_expense"])],
        ["Zakat", fmt_amount(profit["zakat_expense"])],
        ["Net Profit", fmt_amount(profit["net_profit"])],
    ]
    tbl = Table(profit_data, colWidths=[100 * mm, 60 * mm])
    tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 4), (-1, 4), 0.5, colors.grey),
        ("LINEABOVE", (0, 5), (-1, 5), 1, colors.black),
        ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
        ("LINEABOVE", (0, 9), (-1, 9), 1, colors.black),
        ("FONTNAME", (0, 9), (-1, 9), "Helvetica-Bold"),
        ("FONTSIZE", (0, 9), (-1, 9), 11),
    ]))
    flow.append(tbl)

    flow.append(Spacer(1, 8 * mm))
    flow.append(Paragraph("Capital Account", ParagraphStyle("CapHead", parent=styles["Heading3"])))
    cap_data = [["Total Capital Introduced", fmt_amount(capital["total_in"])],
                ["Total Capital Withdrawn", fmt_amount(capital["total_out"])],
                ["Net Capital", fmt_amount(capital["net_capital"])]]
    cap_tbl = Table(cap_data, colWidths=[100 * mm, 60 * mm])
    cap_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.black),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
    ]))
    flow.append(cap_tbl)
    flow.extend(_footer_flowables())

    if output_path is None:
        output_path = os.path.join(_default_output_dir(), f"ProfitSummary_{date_from}_to_{date_to}.pdf")
    return _build_pdf(output_path, flow)


if __name__ == "__main__":
    print("This module is meant to be imported from reports_form.py.")
    print("Example: python -c \"import pdf_export; pdf_export.generate_trial_balance_pdf()\"")
