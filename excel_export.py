"""
excel_export.py
------------------
Excel (.xlsx) versions of every report - "Export to Excel" next to the
existing "Print / Save PDF" button on each ledger. Deliberately reuses
the exact same data-fetching functions in db.py that the web pages and
PDF exports already use (db.get_receivable_aging, get_cash_taccount,
etc.) so the numbers can never drift between the three formats.
"""

import os
from datetime import date as date_cls

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

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


def _get_company_name():
    if _settings_module is not None and hasattr(_settings_module, "get_company_name"):
        return _settings_module.get_company_name()
    return "Company Name"


def _get_header_color():
    if _ui_theme is not None:
        try:
            return _ui_theme.get_colors()["primary"].lstrip("#").upper()
        except Exception:
            pass
    return "2563EB"


def _default_output_dir():
    if _db_module is not None and hasattr(_db_module, "get_active_db_path"):
        return os.path.dirname(os.path.abspath(_db_module.get_active_db_path()))
    return os.path.dirname(os.path.abspath(__file__))


HEADER_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=14)
SUBTITLE_FONT = Font(italic=True, size=9, color="666666")
BOLD = Font(bold=True)
MONEY_FORMAT = "#,##0.00"


def _new_workbook(title):
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    return wb, ws


def _write_title(ws, title, subtitle=""):
    ws["A1"] = _get_company_name()
    ws["A1"].font = TITLE_FONT
    ws["A2"] = title
    ws["A2"].font = Font(bold=True, size=12)
    if subtitle:
        ws["A3"] = subtitle
        ws["A3"].font = SUBTITLE_FONT
    return 5


def _write_header_row(ws, row, headers, start_col=1):
    fill = PatternFill(start_color=_get_header_color(), end_color=_get_header_color(), fill_type="solid")
    for i, h in enumerate(headers, start=start_col):
        cell = ws.cell(row=row, column=i, value=h)
        cell.font = HEADER_FONT
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")


def _autosize(ws, n_cols, min_width=10, max_width=40):
    for col in range(1, n_cols + 1):
        letter = get_column_letter(col)
        max_len = 0
        for cell in ws[letter]:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[letter].width = max(min_width, min(max_width, max_len + 2))


def _save(wb, filename):
    output_path = os.path.join(_default_output_dir(), filename)
    wb.save(output_path)
    return output_path


def _aging_excel(aging_rows, title, filename, output_path=None):
    wb, ws = _new_workbook(title)
    row = _write_title(ws, title, f"as of {date_cls.today().isoformat()}")
    headers = ["Party", "Inv #", "Date", "D.O.#", "Item", "Qty", "Rate", "Outstanding",
               "Credit Days", "Due Date", "Status"]
    _write_header_row(ws, row, headers)
    row += 1

    grand_total = 0.0
    for r in aging_rows:
        status = (f"Overdue by {r['days']}d" if r["is_overdue"]
                  else "Due today" if r["status"] == "Due today" else f"Not due ({r['days']}d)")
        ws.append([r["party_name"], r.get("voucher_display", ""), r["date"], r["do_no"] or "",
                   r["item_name"] or "", r["qty"] or "", r["rate"] or "", r["outstanding"],
                   r["credit_days"], r["due_date"] or "", status])
        grand_total += r["outstanding"]
        if r["is_overdue"]:
            for c in range(1, len(headers) + 1):
                ws.cell(row=ws.max_row, column=c).font = Font(color="DC2626")
        ws.cell(row=ws.max_row, column=8).number_format = MONEY_FORMAT
        ws.cell(row=ws.max_row, column=7).number_format = MONEY_FORMAT

    ws.append([])
    ws.append(["", "", "", "", "", "", "GRAND TOTAL", grand_total])
    ws.cell(row=ws.max_row, column=7).font = BOLD
    ws.cell(row=ws.max_row, column=8).font = BOLD
    ws.cell(row=ws.max_row, column=8).number_format = MONEY_FORMAT

    _autosize(ws, len(headers))
    if output_path is None:
        output_path = _save(wb, filename)
    else:
        wb.save(output_path)
    return output_path


def generate_receivable_excel(as_of_date=None, output_path=None):
    aging = _db_module.get_receivable_aging(as_of_date)
    return _aging_excel(aging, "Receivable Ledger", "ReceivableLedger.xlsx", output_path)


def generate_payable_excel(as_of_date=None, output_path=None):
    aging = _db_module.get_payable_aging(as_of_date)
    return _aging_excel(aging, "Payable Ledger", "PayableLedger.xlsx", output_path)


def generate_cashbook_excel(date_from, date_to, output_path=None):
    t = _db_module.get_cash_taccount(date_from, date_to)
    wb, ws = _new_workbook("Cash Book")
    row = _write_title(ws, "Cash Book", f"{date_from} to {date_to}")

    ws.cell(row=row, column=1, value="BANAAM (money out)").font = BOLD
    ws.cell(row=row, column=6, value="JAMA (money in)").font = BOLD
    row += 1
    headers = ["Ref #", "Date", "Account", "Remarks", "Amount"]
    _write_header_row(ws, row, headers, start_col=1)
    _write_header_row(ws, row, headers, start_col=6)
    row += 1

    max_rows = max(len(t["debit_entries"]), len(t["credit_entries"]))
    for i in range(max_rows):
        if i < len(t["debit_entries"]):
            e = t["debit_entries"][i]
            ws.cell(row=row, column=1, value=e["ref"])
            ws.cell(row=row, column=2, value=e["date"])
            ws.cell(row=row, column=3, value=e["party"])
            ws.cell(row=row, column=4, value=e.get("remarks", ""))
            ws.cell(row=row, column=5, value=e["amount"]).number_format = MONEY_FORMAT
        if i < len(t["credit_entries"]):
            e = t["credit_entries"][i]
            ws.cell(row=row, column=6, value=e["ref"])
            ws.cell(row=row, column=7, value=e["date"])
            ws.cell(row=row, column=8, value=e["party"])
            ws.cell(row=row, column=9, value=e.get("remarks", ""))
            ws.cell(row=row, column=10, value=e["amount"]).number_format = MONEY_FORMAT
        row += 1

    ws.cell(row=row, column=4, value="TOTAL").font = BOLD
    ws.cell(row=row, column=5, value=t["total_debit"]).font = BOLD
    ws.cell(row=row, column=5).number_format = MONEY_FORMAT
    ws.cell(row=row, column=9, value="TOTAL").font = BOLD
    ws.cell(row=row, column=10, value=t["total_credit"]).font = BOLD
    ws.cell(row=row, column=10).number_format = MONEY_FORMAT
    row += 2
    ws.cell(row=row, column=1, value=f"Opening Balance: {t['opening_balance']:,.2f}   Closing Balance: {t['closing_balance']:,.2f}")

    _autosize(ws, 10)
    if output_path is None:
        output_path = _save(wb, "CashBook.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_ledger_excel(party_id, date_from=None, date_to=None, output_path=None):
    conn = _db_module.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, opening_balance FROM parties WHERE id = ?", (party_id,))
    party_row = cur.fetchone()
    party_name = party_row[0] if party_row else "Unknown"
    opening_balance = (party_row[1] or 0.0) if party_row else 0.0

    query = """SELECT t.date, t.voucher_type, t.voucher_no, t.do_no, q.name, t.qty, t.rate, t.amount
               FROM transactions t LEFT JOIN quality q ON q.id = t.quality_id
               WHERE t.party_id = ?"""
    params = [party_id]
    if date_from and date_to:
        query += " AND t.date BETWEEN ? AND ?"
        params += [date_from, date_to]
    query += " ORDER BY t.date, t.id"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    wb, ws = _new_workbook("Party Ledger")
    subtitle = f"{party_name}" + (f" - {date_from} to {date_to}" if date_from else "")
    row = _write_title(ws, "Party Ledger", subtitle)
    headers = ["Date", "Voucher", "Ref #", "D.O.#", "Item", "Qty", "Debit", "Credit", "Balance"]
    _write_header_row(ws, row, headers)
    row += 1

    balance = opening_balance
    ws.append(["", "Opening Balance", "", "", "", "", "", "", balance])
    ws.cell(row=ws.max_row, column=9).number_format = MONEY_FORMAT
    ws.cell(row=ws.max_row, column=2).font = Font(italic=True)

    for t_date, v_type, vno, do_no, item_name, qty, rate, amount in rows:
        amount = amount or 0
        ref = _db_module.format_voucher_no(v_type, vno)
        if v_type in ("SALE", "PAYMENT", "CONTRA_DR", "EXPENSE", "CAPITAL_OUT"):
            debit, credit = amount, 0
            balance += amount
        else:
            debit, credit = 0, amount
            balance -= amount
        ws.append([t_date, v_type, ref, do_no or "", item_name or "", qty or "",
                   debit or "", credit or "", balance])
        for c in (7, 8, 9):
            ws.cell(row=ws.max_row, column=c).number_format = MONEY_FORMAT

    _autosize(ws, len(headers))
    if output_path is None:
        safe_name = "".join(ch for ch in party_name if ch.isalnum() or ch in " _-").strip().replace(" ", "_")
        output_path = _save(wb, f"Ledger_{safe_name}.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_trial_balance_excel(output_path=None):
    rows, total_debit, total_credit = _db_module.get_trial_balance()

    wb, ws = _new_workbook("Trial Balance")
    row = _write_title(ws, "Trial Balance", "All parties, all-time")
    headers = ["Account", "Debit", "Credit", "Balance"]
    _write_header_row(ws, row, headers)
    row += 1

    for r in rows:
        ws.append([r["name"], r["debit"], r["credit"], r["balance"]])
        for c in (2, 3, 4):
            ws.cell(row=ws.max_row, column=c).number_format = MONEY_FORMAT

    ws.append(["TOTAL", total_debit, total_credit, total_debit - total_credit])
    for c in range(1, 5):
        ws.cell(row=ws.max_row, column=c).font = BOLD
    for c in (2, 3, 4):
        ws.cell(row=ws.max_row, column=c).number_format = MONEY_FORMAT

    _autosize(ws, len(headers))
    if output_path is None:
        output_path = _save(wb, "TrialBalance.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_balance_sheet_excel(as_of_date=None, output_path=None):
    bs = _db_module.get_balance_sheet(as_of_date)

    wb, ws = _new_workbook("Balance Sheet")
    row = _write_title(ws, "Balance Sheet", f"As of {bs['as_of_date']}")
    headers = ["Account", "Amount"]
    _write_header_row(ws, row, headers)
    row += 1

    def section(label):
        ws.append([label, None])
        ws.cell(row=ws.max_row, column=1).font = BOLD

    def line(label, amount, indent=True):
        ws.append(["    " + label if indent else label, amount])
        ws.cell(row=ws.max_row, column=2).number_format = MONEY_FORMAT

    def total(label, amount):
        ws.append([label, amount])
        ws.cell(row=ws.max_row, column=1).font = BOLD
        ws.cell(row=ws.max_row, column=2).font = BOLD
        ws.cell(row=ws.max_row, column=2).number_format = MONEY_FORMAT

    section("ASSETS")
    line("Cash", bs["cash_balance"])
    for r in bs["receivables"]:
        line(f"Receivable — {r['name']}", r["amount"])
    line("Stock / Inventory", bs["stock_value"])
    total("TOTAL ASSETS", bs["total_assets"])

    section("LIABILITIES")
    if not bs["payables"]:
        line("(none)", 0)
    for p in bs["payables"]:
        line(f"Payable — {p['name']}", p["amount"])
    total("TOTAL LIABILITIES", bs["total_liabilities"])

    section("EQUITY")
    line("Capital Account", bs["capital"])
    line("Opening Balance Equity", bs["opening_balance_equity"])
    line("Retained Earnings", bs["retained_earnings"])
    total("TOTAL EQUITY", bs["total_equity"])

    total("TOTAL LIABILITIES + EQUITY", bs["total_liabilities_and_equity"])

    _autosize(ws, len(headers))
    if output_path is None:
        output_path = _save(wb, "BalanceSheet.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_stock_excel(with_value=True, output_path=None):
    conn = _db_module.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, city_area FROM quality ORDER BY name")
    items = cur.fetchall()
    conn.close()

    wb, ws = _new_workbook("Stock")
    subtitle = f"As of {date_cls.today().isoformat()}" + ("" if with_value else " (quantities only)")
    row = _write_title(ws, "Stock Report", subtitle)
    headers = ["Item / Quality", "Area", "Closing Qty", "Purch. Rate (avg)", "Stock Value"] if with_value \
        else ["Item / Quality", "Area", "Closing Qty"]
    _write_header_row(ws, row, headers)

    total_closing = 0.0
    total_value = 0.0
    for qid, name, area in items:
        stock = _db_module.get_stock_qty(qid)
        total_closing += stock
        if with_value:
            rate = _db_module.get_weighted_avg_purchase_rate(qid)
            value = stock * rate
            total_value += value
            ws.append([name, area or "", stock, rate, value])
            ws.cell(row=ws.max_row, column=4).number_format = MONEY_FORMAT
            ws.cell(row=ws.max_row, column=5).number_format = MONEY_FORMAT
        else:
            ws.append([name, area or "", stock])

    if with_value:
        ws.append(["", "TOTAL", total_closing, "", total_value])
        for c in (1, 5):
            ws.cell(row=ws.max_row, column=c).font = BOLD
        ws.cell(row=ws.max_row, column=5).number_format = MONEY_FORMAT
    else:
        ws.append(["", "TOTAL", total_closing])
        for c in (1, 3):
            ws.cell(row=ws.max_row, column=c).font = BOLD

    _autosize(ws, len(headers))
    if output_path is None:
        suffix = "" if with_value else "_NoValue"
        output_path = _save(wb, f"StockReport{suffix}.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_profit_excel(date_from, date_to, output_path=None):
    profit = _db_module.get_profit_summary(date_from, date_to)
    capital = _db_module.get_capital_summary()

    wb, ws = _new_workbook("Profit")
    row = _write_title(ws, "Profit & Capital Summary", f"{date_from} to {date_to}")
    rows_data = [
        ("Total Sales", profit["total_sales"]), ("Total Purchases", profit["total_purchases"]),
        ("Opening Stock Value", profit["opening_stock_value"]), ("Closing Stock Value", profit["closing_stock_value"]),
        ("Cost of Goods Sold", profit["cogs"]), ("Gross Profit", profit["gross_profit"]),
        ("Home Expense", profit["home_expense"]), ("Office Expense", profit["office_expense"]),
        ("Net Profit", profit["net_profit"]),
    ]
    for label, value in rows_data:
        ws.append([label, value])
        ws.cell(row=ws.max_row, column=2).number_format = MONEY_FORMAT
    ws.cell(row=ws.max_row, column=1).font = BOLD
    ws.cell(row=ws.max_row, column=2).font = BOLD

    ws.append([])
    ws.append(["Capital Account (all-time)"])
    ws.cell(row=ws.max_row, column=1).font = BOLD
    ws.append(["Zakat is a personal draw against capital, not a business expense - it reduces Capital here, not Net Profit above."])
    for label, value in [("Total Introduced", capital["total_in"]),
                          ("Total Withdrawn", capital["total_out"] - capital["zakat_total"]),
                          ("Zakat Paid", capital["zakat_total"]),
                          ("Net Capital", capital["net_capital"])]:
        ws.append([label, value])
        ws.cell(row=ws.max_row, column=2).number_format = MONEY_FORMAT

    _autosize(ws, 2)
    if output_path is None:
        output_path = _save(wb, f"ProfitSummary_{date_from}_to_{date_to}.xlsx")
    else:
        wb.save(output_path)
    return output_path


def generate_brokerage_excel(broker_party_id=None, output_path=None):
    rows = _db_module.get_brokerage_report(broker_party_id=broker_party_id)
    summary = _db_module.get_brokerage_summary(broker_party_id=broker_party_id)

    wb, ws = _new_workbook("Brokerage")
    row = _write_title(ws, "Brokerage Report", date_cls.today().isoformat())

    if summary:
        ws.cell(row=row, column=1, value="Owed / Paid / Balance by broker").font = BOLD
        row += 1
        _write_header_row(ws, row, ["Broker", "Owed", "Paid", "Balance"])
        row += 1
        for s in summary:
            ws.cell(row=row, column=1, value=s["broker_name"])
            ws.cell(row=row, column=2, value=s["owed"]).number_format = MONEY_FORMAT
            ws.cell(row=row, column=3, value=s["paid"]).number_format = MONEY_FORMAT
            ws.cell(row=row, column=4, value=s["balance"]).number_format = MONEY_FORMAT
            row += 1
        row += 1

    headers = ["Broker", "Voucher #", "Date", "D.O.#", "Party", "Item", "Qty", "Amount", "Brokerage"]
    _write_header_row(ws, row, headers)

    total = 0.0
    for r in rows:
        ws.append([r["broker_name"], r["voucher_display"], r["date"], r["do_no"] or "",
                   r["party_name"] or "", r["item_name"] or "", r["qty"] or "", r["amount"], r["brokerage"]])
        ws.cell(row=ws.max_row, column=8).number_format = MONEY_FORMAT
        ws.cell(row=ws.max_row, column=9).number_format = MONEY_FORMAT
        total += r["brokerage"]

    ws.append(["", "", "", "", "", "", "", "TOTAL", total])
    ws.cell(row=ws.max_row, column=8).font = BOLD
    ws.cell(row=ws.max_row, column=9).font = BOLD
    ws.cell(row=ws.max_row, column=9).number_format = MONEY_FORMAT

    _autosize(ws, len(headers))
    if output_path is None:
        output_path = _save(wb, "BrokerageReport.xlsx")
    else:
        wb.save(output_path)
    return output_path
