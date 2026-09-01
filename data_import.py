"""
data_import.py
------------------
Bulk-import Parties and Quality/Items from an Excel or CSV file, so
customers moving from another (often offline) system can bring their
existing master data over in one go instead of retyping everything.

Deliberately imports MASTER DATA and current balances only, not a full
transaction history - the standard way to migrate accounting software:
set correct starting (opening) balances and continue forward from
there, rather than re-entering years of individual invoices. This
matches exactly what the "Opening Balance" field on each party/item is
already for.

Duplicate names are skipped, never overwritten, so a customer can
safely re-upload a corrected file without risking clobbering data
they've already fixed by hand in the app.
"""

import os
import csv
import io
from openpyxl import Workbook, load_workbook


PARTY_HEADERS = ["Name", "Type", "City", "Phone", "NTN", "STN", "Address",
                  "Credit Limit", "Opening Balance", "Brokerage Type", "Brokerage Rate"]
PARTY_TYPES = {"Customer", "Supplier", "Broker", "Expense", "Bank"}

QUALITY_HEADERS = ["Name", "City / Area", "Sale Rate", "Opening Balance (Stock Qty)"]

OPENING_ENTRY_HEADERS = ["Party Name", "Type", "Date", "Reference / Invoice #",
                          "Item", "Qty", "Rate", "Outstanding Amount", "Credit Days"]
OPENING_ENTRY_TYPES = {"Receivable": "receivable", "Payable": "payable"}


def generate_party_template(output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Parties"
    ws.append(PARTY_HEADERS)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    ws.append(["Al-Faisal Traders", "Customer", "Lahore", "0300-1234567", "", "",
               "Main Market, Lahore", 500000, 125000, "", ""])
    ws.append(["Yasir Ginners", "Supplier", "Multan", "", "", "", "", 0, -80000, "", ""])
    ws.append(["Tariq Bhai", "Broker", "", "", "", "", "", 0, 0, "per_unit", 50])
    notes = ws.cell(row=6, column=1,
                     value="Type must be exactly one of: Customer, Supplier, Broker, Expense, Bank. "
                           "Opening Balance: positive = they owe you (receivable), negative = you owe them (payable). "
                           "Brokerage columns only apply to Type=Broker. Delete these three example rows before importing your real data.")
    notes.font = notes.font.copy(italic=True, size=9)
    for col, width in zip("ABCDEFGHIJK", [22, 12, 14, 15, 12, 12, 26, 13, 15, 15, 14]):
        ws.column_dimensions[col].width = width
    wb.save(output_path)
    return output_path


def generate_quality_template(output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Items"
    ws.append(QUALITY_HEADERS)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    ws.append(["30s Combed Cotton Yarn", "Faisalabad", 450, 120])
    ws.append(["20s Carded Yarn", "", 380, 0])
    notes = ws.cell(row=4, column=1,
                     value="Opening Balance is your current stock quantity on hand for this item, as of today. "
                           "Delete these example rows before importing your real data.")
    notes.font = notes.font.copy(italic=True, size=9)
    for col, width in zip("ABCD", [28, 16, 12, 22]):
        ws.column_dimensions[col].width = width
    wb.save(output_path)
    return output_path


def generate_opening_entries_template(output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Outstanding Invoices"
    ws.append(OPENING_ENTRY_HEADERS)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)
    ws.append(["Al-Faisal Traders", "Receivable", "2026-06-15", "INV-2044",
               "30s Combed Cotton Yarn", 50, 450, 22500, 30])
    ws.append(["Al-Faisal Traders", "Receivable", "2026-07-02", "INV-2078",
               "20s Carded Yarn", 30, 380, 11400, 30])
    ws.append(["Yasir Ginners", "Payable", "2026-06-20", "BILL-891",
               "Raw Cotton", 200, 150, 30000, 15])
    notes = ws.cell(row=6, column=1,
                     value="Party Name must exactly match a party you've already imported or created. "
                           "Type must be exactly 'Receivable' (they owe you) or 'Payable' (you owe them). "
                           "Outstanding Amount is what's still unpaid on that invoice/bill today, not "
                           "necessarily its original full amount. One row per outstanding invoice - a "
                           "single party can have many rows here, e.g. every unpaid sale to them. "
                           "Delete these three example rows before importing your real data.")
    notes.font = notes.font.copy(italic=True, size=9)
    for col, width in zip("ABCDEFGHI", [22, 12, 12, 18, 26, 8, 10, 16, 12]):
        ws.column_dimensions[col].width = width
    wb.save(output_path)
    return output_path


def _read_rows(file_storage):
    """Reads an uploaded .xlsx or .csv file into a list of dict rows
    keyed by header name. Returns (rows, error_message_or_None)."""
    filename = (file_storage.filename or "").lower()
    if filename.endswith(".csv"):
        raw = file_storage.read().decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
    elif filename.endswith(".xlsx"):
        wb = load_workbook(file_storage, data_only=True)
        ws = wb.active
        rows = [[c.value for c in row] for row in ws.iter_rows()]
    else:
        return None, "Please upload a .xlsx or .csv file."

    if not rows:
        return None, "The file is empty."
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    data_rows = []
    for raw_row in rows[1:]:
        if not any(c is not None and str(c).strip() for c in raw_row):
            continue  # skip fully blank rows
        row_dict = {}
        for i, h in enumerate(headers):
            row_dict[h] = raw_row[i] if i < len(raw_row) else None
        data_rows.append(row_dict)
    return data_rows, None


def import_parties(file_storage, conn):
    """Returns a summary dict: {created, skipped_duplicate, errors: [...]}."""
    rows, err = _read_rows(file_storage)
    if err:
        return {"created": 0, "skipped_duplicate": 0, "errors": [err]}

    cur = conn.cursor()
    cur.execute("SELECT LOWER(name) FROM parties")
    existing_names = {r[0] for r in cur.fetchall()}

    created = skipped = 0
    errors = []
    for i, row in enumerate(rows, start=2):  # row 2 = first data row (after header)
        name = str(row.get("Name") or "").strip()
        if not name:
            errors.append(f"Row {i}: missing Name, skipped.")
            continue
        if name.lower() in existing_names:
            skipped += 1
            continue

        party_type = str(row.get("Type") or "Customer").strip() or "Customer"
        if party_type not in PARTY_TYPES:
            errors.append(f"Row {i} ('{name}'): unknown Type '{party_type}', imported as Customer instead.")
            party_type = "Customer"

        def as_float(v):
            try:
                return float(v) if v not in (None, "") else 0.0
            except (TypeError, ValueError):
                return 0.0

        brokerage_type = str(row.get("Brokerage Type") or "").strip() or None
        if brokerage_type and brokerage_type not in ("percentage", "per_unit"):
            brokerage_type = None
        brokerage_rate = as_float(row.get("Brokerage Rate")) if party_type == "Broker" else None
        if party_type != "Broker":
            brokerage_type = None

        cur.execute(
            """INSERT INTO parties (name, city, phone, ntn, stn, address, credit_limit,
               opening_balance, party_type, is_gl, brokerage_type, brokerage_rate, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,0,?,?,datetime('now'))""",
            (name, str(row.get("City") or "").strip(), str(row.get("Phone") or "").strip(),
             str(row.get("NTN") or "").strip(), str(row.get("STN") or "").strip(),
             str(row.get("Address") or "").strip(), as_float(row.get("Credit Limit")),
             as_float(row.get("Opening Balance")), party_type, brokerage_type, brokerage_rate),
        )
        existing_names.add(name.lower())
        created += 1

    conn.commit()
    return {"created": created, "skipped_duplicate": skipped, "errors": errors}


def import_quality(file_storage, conn):
    rows, err = _read_rows(file_storage)
    if err:
        return {"created": 0, "skipped_duplicate": 0, "errors": [err]}

    cur = conn.cursor()
    cur.execute("SELECT LOWER(name) FROM quality")
    existing_names = {r[0] for r in cur.fetchall()}

    created = skipped = 0
    errors = []
    for i, row in enumerate(rows, start=2):
        name = str(row.get("Name") or "").strip()
        if not name:
            errors.append(f"Row {i}: missing Name, skipped.")
            continue
        if name.lower() in existing_names:
            skipped += 1
            continue

        def as_float(v):
            try:
                return float(v) if v not in (None, "") else 0.0
            except (TypeError, ValueError):
                return 0.0

        cur.execute(
            "INSERT INTO quality (name, city_area, sale_rate, opening_balance, created_at) "
            "VALUES (?,?,?,?,datetime('now'))",
            (name, str(row.get("City / Area") or "").strip(),
             as_float(row.get("Sale Rate")), as_float(row.get("Opening Balance (Stock Qty)"))),
        )
        existing_names.add(name.lower())
        created += 1

    conn.commit()
    return {"created": created, "skipped_duplicate": skipped, "errors": errors}


def import_opening_entries(file_storage, conn):
    """Imports detailed outstanding invoices/bills against existing
    parties (matched by exact name). Unlike party/item import, there's
    no meaningful 'duplicate' concept here - the same party can
    legitimately have many outstanding invoices - so every valid row
    is imported; only rows with real problems (unknown party, bad
    type, missing amount) are skipped and reported."""
    rows, err = _read_rows(file_storage)
    if err:
        return {"created": 0, "skipped_duplicate": 0, "errors": [err]}

    cur = conn.cursor()
    cur.execute("SELECT id, LOWER(name) FROM parties WHERE is_gl = 0")
    party_by_name = {name: pid for pid, name in cur.fetchall()}

    created = 0
    errors = []
    for i, row in enumerate(rows, start=2):
        party_name = str(row.get("Party Name") or "").strip()
        if not party_name:
            errors.append(f"Row {i}: missing Party Name, skipped.")
            continue
        party_id = party_by_name.get(party_name.lower())
        if not party_id:
            errors.append(f"Row {i}: no party named '{party_name}' found - import parties first, skipped.")
            continue

        type_raw = str(row.get("Type") or "").strip()
        entry_type = OPENING_ENTRY_TYPES.get(type_raw)
        if not entry_type:
            errors.append(f"Row {i} ('{party_name}'): Type must be 'Receivable' or 'Payable', got '{type_raw}', skipped.")
            continue

        def as_float(v, default=None):
            try:
                return float(v) if v not in (None, "") else default
            except (TypeError, ValueError):
                return default

        amount = as_float(row.get("Outstanding Amount"))
        if amount is None or amount <= 0:
            errors.append(f"Row {i} ('{party_name}'): Outstanding Amount must be a positive number, skipped.")
            continue

        date_val = row.get("Date")
        date_str = str(date_val)[:10] if date_val else None
        if date_str and hasattr(date_val, "strftime"):
            date_str = date_val.strftime("%Y-%m-%d")

        cur.execute(
            """INSERT INTO opening_entries (party_id, entry_type, date, reference, item_name,
               qty, rate, amount, credit_days, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (party_id, entry_type, date_str, str(row.get("Reference / Invoice #") or "").strip(),
             str(row.get("Item") or "").strip(), as_float(row.get("Qty")), as_float(row.get("Rate")),
             amount, int(as_float(row.get("Credit Days"), 0) or 0)),
        )
        created += 1

    conn.commit()
    return {"created": created, "skipped_duplicate": 0, "errors": errors}
