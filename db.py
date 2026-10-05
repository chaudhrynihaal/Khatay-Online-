"""
db.py
------
Database connection + schema for ULTRA ERP.

Web-app version: each company (tenant) gets its own SQLite file under
tenants/<company_slug>/ultra_erp.db. Every request sets which file is
"active" for that request via set_active_db_path() (see auth.py's
before_request hook) using a thread-local, so concurrent requests from
different companies never cross-talk. All the business logic below
(the FIFO aging, profit calculation, etc.) is completely unchanged
from the desktop app - only get_connection() and the default DB_PATH
resolution are different.
"""

import os
import sqlite3
import threading
from datetime import datetime, date, timedelta

# Fallback path when nothing else is set (e.g. running db.py directly,
# or a single-tenant deployment that never calls set_active_db_path).
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultra_erp.db")

_local = threading.local()


def set_active_db_path(path):
    """Called once per web request (or once at startup for the desktop
    app) to say which tenant's database file subsequent get_connection()
    calls in this thread should use."""
    _local.db_path = path


def get_active_db_path():
    return getattr(_local, "db_path", None) or DB_PATH


def get_connection():
    """Return a new sqlite3 connection with foreign keys enabled, to
    whichever database is active for the current thread/request.

    Two settings matter once more than one person is using the app at
    the same time (e.g. from different office computers):

    - WAL (write-ahead log) journal mode lets reads and writes happen
      concurrently instead of a write blocking every reader.
    - busy_timeout tells SQLite to wait and quietly retry for up to a
      few seconds if it finds the database briefly locked by another
      request, instead of immediately raising
      "sqlite3.OperationalError: database is locked" - which is what
      was happening before this fix, on routes like deleting an entry,
      whenever two requests landed at almost the same moment.
    """
    conn = sqlite3.connect(get_active_db_path(), timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 8000")
    return conn


def init_db():
    """Create tables if they don't already exist. Safe to call every
    time the app starts."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_urdu TEXT,
            city TEXT,
            phone TEXT,
            ntn TEXT,
            stn TEXT,
            address TEXT,
            broker TEXT,
            credit_limit REAL DEFAULT 0,
            opening_balance REAL DEFAULT 0,
            party_type TEXT NOT NULL DEFAULT 'Customer',
            is_gl INTEGER DEFAULT 0,
            created_at TEXT,
            brokerage_type TEXT,
            brokerage_rate REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city_area TEXT,
            purchase_rate REAL DEFAULT 0,
            sale_rate REAL DEFAULT 0,
            opening_balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            voucher_type TEXT NOT NULL,
            voucher_no INTEGER,
            do_no TEXT,
            party_id INTEGER NOT NULL,
            broker TEXT,
            quality_id INTEGER,
            qty REAL,
            rate REAL,
            amount REAL NOT NULL,
            cash_or_cheque TEXT,
            cheque_no TEXT,
            description TEXT,
            credit_days INTEGER,
            created_at TEXT,
            signature_data TEXT,
            booking_id INTEGER,
            broker_party_id INTEGER,
            FOREIGN KEY (party_id) REFERENCES parties (id),
            FOREIGN KEY (quality_id) REFERENCES quality (id)
        )
    """)

    # --- migration: older databases missing columns added over time ---
    cur.execute("PRAGMA table_info(transactions)")
    existing_cols = {row[1] for row in cur.fetchall()}
    cur.execute("PRAGMA table_info(parties)")
    existing_party_cols = {row[1] for row in cur.fetchall()}

    if "voucher_no" not in existing_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN voucher_no INTEGER")
        conn.commit()
        # backfill: number existing rows sequentially per voucher_type, in id order,
        # so old data gets clean 1, 2, 3... numbering instead of being left blank
        for v_type in ("SALE", "PURCHASE", "RECEIPT", "PAYMENT"):
            cur.execute(
                "SELECT id FROM transactions WHERE voucher_type = ? ORDER BY id", (v_type,)
            )
            ids = [r[0] for r in cur.fetchall()]
            for i, txn_id in enumerate(ids, start=1):
                cur.execute("UPDATE transactions SET voucher_no = ? WHERE id = ?", (i, txn_id))

    # --- e-signature capture: an optional signature image (base64 PNG
    # data URI) captured from the receiver at the time of a Sale, shown
    # on the printed D.O. in place of the blank "Signature Buyer" line. ---
    if "signature_data" not in existing_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN signature_data TEXT")
        conn.commit()

    # --- booking breakout: which booking (if any) a Sale/Purchase
    # delivery came from, so every delivery against a booking can be
    # listed on that booking's own detail page. ---
    if "booking_id" not in existing_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN booking_id INTEGER")
        conn.commit()

    # --- brokerage: which Broker-type party (if any) is owed
    # brokerage on this transaction, calculated automatically from
    # that broker's configured rate at the time of entry. ---
    if "broker_party_id" not in existing_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN broker_party_id INTEGER")
        conn.commit()

    if "brokerage_type" not in existing_party_cols:
        cur.execute("ALTER TABLE parties ADD COLUMN brokerage_type TEXT")
        conn.commit()
    if "brokerage_rate" not in existing_party_cols:
        cur.execute("ALTER TABLE parties ADD COLUMN brokerage_rate REAL")
        conn.commit()

    # --- multi-cheque support: a Receipt or Payment voucher can list
    # several cheques (each with its own bank/cheque number/amount)
    # under the one voucher number. Older transaction rows that predate
    # this just keep using their single cash_or_cheque/cheque_no/amount
    # fields directly - voucher_print.py falls back to that when a
    # transaction has no rows here. ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transaction_cheques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            date TEXT,
            bank TEXT,
            cheque_no TEXT,
            amount REAL NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cheques_txn ON transaction_cheques(transaction_id)")

    # --- bookings: a forward contract/booking made now for delivery
    # later - doesn't touch stock or the party's balance until it's
    # actually converted into a real Sale/Purchase transaction (see
    # deliver_booking()). Kept as its own numbered series, separate
    # from D.O./invoice numbers. ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_no INTEGER,
            voucher_type TEXT NOT NULL,
            date TEXT NOT NULL,
            party_id INTEGER NOT NULL,
            quality_id INTEGER NOT NULL,
            qty REAL NOT NULL,
            rate REAL NOT NULL,
            amount REAL NOT NULL,
            delivery_terms TEXT,
            status TEXT NOT NULL DEFAULT 'Open',
            delivered_qty REAL NOT NULL DEFAULT 0,
            transaction_id INTEGER,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES parties (id),
            FOREIGN KEY (quality_id) REFERENCES quality (id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_party ON bookings(party_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)")

    # --- opening_entries: detailed outstanding invoices/bills imported
    # from a previous system, one row per still-unpaid item - richer
    # than the single lump-sum "opening_balance" number on the party
    # itself. When these exist for a party, they replace that single
    # number in the Receivable/Payable Ledger and Party Ledger, so the
    # actual breakdown (what was sold, when, for how much) carries
    # forward instead of just one opaque total. ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS opening_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            entry_type TEXT NOT NULL,
            date TEXT,
            reference TEXT,
            item_name TEXT,
            qty REAL,
            rate REAL,
            amount REAL NOT NULL,
            credit_days INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES parties (id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_opening_entries_party ON opening_entries(party_id)")

    # Helpful indexes for the reports (ledger / cash book / stock all
    # filter or group by these columns).
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_party ON transactions(party_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_quality ON transactions(quality_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_voucher_type ON transactions(voucher_type)")

    conn.commit()
    _ensure_gl_parties(conn)
    _init_kiryana_schema(conn)
    _init_hardware_schema(conn)
    conn.close()


# ---------------------------------------------------------------------
# GL (general ledger) accounts - not real customers/suppliers, just
# bookkeeping buckets for Home Expense, Office Expense, and Capital.
# is_gl=1 keeps them out of the normal Parties list (party_form.py and
# every party-facing report already filter WHERE is_gl = 0).
# ---------------------------------------------------------------------
GL_HOME_EXPENSE = "Home Expense"
GL_OFFICE_EXPENSE = "Office Expense"
GL_ZAKAT = "Zakat"
GL_CAPITAL = "Capital Account"


def _ensure_gl_parties(conn):
    cur = conn.cursor()
    for name in (GL_HOME_EXPENSE, GL_OFFICE_EXPENSE, GL_ZAKAT, GL_CAPITAL):
        cur.execute("SELECT id FROM parties WHERE name = ? AND is_gl = 1", (name,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO parties (name, opening_balance, party_type, is_gl, created_at) "
                "VALUES (?, 0, 'GL', 1, ?)",
                (name, now_iso()),
            )
    conn.commit()


def get_gl_party_id(name, conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM parties WHERE name = ? AND is_gl = 1", (name,))
    row = cur.fetchone()
    if owns_conn:
        conn.close()
    return row[0] if row else None


# ---------------------------------------------------------------------
# Multi-cheque support for Receipt/Payment vouchers - one voucher
# number can cover several cheques, each with its own bank and cheque
# number. The parent transactions.amount is always kept as the sum of
# its cheque lines (or the single manually-entered cash amount when
# there are no cheque lines at all).
# ---------------------------------------------------------------------
def save_cheques(transaction_id, cheque_rows, conn=None):
    """cheque_rows: list of dicts with keys date, bank, cheque_no, amount.
    Replaces any existing cheque rows for this transaction."""
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM transaction_cheques WHERE transaction_id = ?", (transaction_id,))
    for row in cheque_rows:
        cur.execute(
            "INSERT INTO transaction_cheques (transaction_id, date, bank, cheque_no, amount) VALUES (?,?,?,?,?)",
            (transaction_id, row.get("date"), row.get("bank"), row.get("cheque_no"), row.get("amount", 0)),
        )
    if owns_conn:
        conn.commit()
        conn.close()


def get_cheques_for_transaction(transaction_id, conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, bank, cheque_no, amount FROM transaction_cheques "
        "WHERE transaction_id = ? ORDER BY id",
        (transaction_id,),
    )
    rows = cur.fetchall()
    if owns_conn:
        conn.close()
    return [{"id": r[0], "date": r[1], "bank": r[2], "cheque_no": r[3], "amount": r[4]} for r in rows]


def now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------
# sequential invoice/voucher numbering - each voucher_type (SALE,
# PURCHASE, RECEIPT, PAYMENT) gets its own 1, 2, 3... sequence that
# never reuses a number, even if an earlier entry is later deleted.
# ---------------------------------------------------------------------
def get_next_voucher_no(voucher_type, conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(voucher_no) FROM transactions WHERE voucher_type = ?", (voucher_type,))
    row = cur.fetchone()
    if owns_conn:
        conn.close()
    return (row[0] or 0) + 1


VOUCHER_PREFIXES = {
    "SALE": "INV",
    "PURCHASE": "PINV",
    "RECEIPT": "RCPT",
    "PAYMENT": "PAY",
    "EXPENSE": "EXP",
    "CAPITAL_IN": "CAPIN",
    "CAPITAL_OUT": "CAPOUT",
    "CONTRA_DR": "CONTRA",
    "CONTRA_CR": "CONTRA",
    "BROKERAGE": "BROK",
}


def format_voucher_no(voucher_type, voucher_no):
    """e.g. format_voucher_no('SALE', 7) -> 'INV-000007'"""
    prefix = VOUCHER_PREFIXES.get(voucher_type, "V")
    if voucher_no is None:
        return f"{prefix}-?"
    return f"{prefix}-{int(voucher_no):06d}"


# ---------------------------------------------------------------------
# due-date / overdue status - used by the Receivable and Payable
# ledgers. Pure date math off (transaction date + credit_days); does
# NOT try to net off partial payments against a specific invoice,
# since payments are recorded against the party as a whole, not
# against one invoice, in this schema.
# ---------------------------------------------------------------------
def compute_due_status(txn_date_str, credit_days, as_of=None):
    """Returns (due_date_iso, status_text, days_over_or_under, is_overdue).
    status_text is one of: 'Not due', 'Due today', 'Overdue'."""
    if as_of is None:
        as_of = date.today()
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)

    try:
        txn_date = date.fromisoformat(str(txn_date_str)[:10])
    except (ValueError, TypeError):
        return None, "Unknown", 0, False

    credit_days = credit_days or 0
    due_date = txn_date + timedelta(days=int(credit_days))
    delta_days = (as_of - due_date).days

    if delta_days > 0:
        return due_date.isoformat(), "Overdue", delta_days, True
    elif delta_days == 0:
        return due_date.isoformat(), "Due today", 0, False
    else:
        return due_date.isoformat(), "Not due", -delta_days, False


# ---------------------------------------------------------------------
# shared calculations - used by the Party form (live balance) and the
# Quality form (live stock), and mirrored in pdf_export.py so every
# screen and every report agree on the same numbers.
# ---------------------------------------------------------------------
def get_party_balance(party_id):
    """opening_balance + SUM(SALE + PAYMENT) - SUM(PURCHASE + RECEIPT)
    Positive = Receivable (they owe you). Negative = Payable (you owe them)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT opening_balance FROM parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 0.0
    balance = row[0] or 0.0
    cur.execute(
        "SELECT voucher_type, SUM(amount) FROM transactions WHERE party_id = ? GROUP BY voucher_type",
        (party_id,),
    )
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()
    balance += sums.get("SALE", 0.0) + sums.get("PAYMENT", 0.0) + sums.get("CONTRA_DR", 0.0)
    balance -= sums.get("PURCHASE", 0.0) + sums.get("RECEIPT", 0.0) + sums.get("CONTRA_CR", 0.0)
    return balance


# ---------------------------------------------------------------------
# Brokerage - automatically calculated whenever a transaction has a
# broker (Broker-type party) assigned, using that broker's own
# configured rate (set once on their party record). Never shows up in
# the Payable Ledger - it's tracked completely separately, in its own
# report, since brokerage owed isn't the same thing as money owed to a
# supplier for goods.
# ---------------------------------------------------------------------
def calculate_brokerage(broker_party_id, qty, amount, conn=None):
    """Returns the brokerage amount owed to this broker for one
    transaction, based on their configured rate. Returns 0 if the
    broker has no rate configured, or isn't actually a Broker party."""
    if not broker_party_id:
        return 0.0
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT party_type, brokerage_type, brokerage_rate FROM parties WHERE id = ?", (broker_party_id,))
    row = cur.fetchone()
    if owns_conn:
        conn.close()
    if not row or row[0] != "Broker" or not row[1] or not row[2]:
        return 0.0
    brokerage_type, rate = row[1], row[2]
    if brokerage_type == "per_unit":
        return (qty or 0) * rate
    else:  # percentage
        return (amount or 0) * rate / 100.0


def get_brokerage_report(broker_party_id=None, date_from=None, date_to=None):
    """Every Sale/Purchase transaction that has a broker assigned, with
    the brokerage amount earned on each - grouped by broker. This is
    its own report, deliberately separate from the Payable Ledger."""
    conn = get_connection()
    cur = conn.cursor()
    query = """SELECT t.id, t.voucher_type, t.voucher_no, t.date, t.do_no, t.qty, t.rate, t.amount,
                      t.broker_party_id, bp.name, p.name, q.name
               FROM transactions t
               LEFT JOIN parties bp ON bp.id = t.broker_party_id
               LEFT JOIN parties p ON p.id = t.party_id
               LEFT JOIN quality q ON q.id = t.quality_id
               WHERE t.broker_party_id IS NOT NULL AND t.voucher_type IN ('SALE', 'PURCHASE')"""
    params = []
    if broker_party_id:
        query += " AND t.broker_party_id = ?"
        params.append(broker_party_id)
    if date_from and date_to:
        query += " AND t.date BETWEEN ? AND ?"
        params += [date_from, date_to]
    query += " ORDER BY bp.name, t.date, t.id"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results = []
    for (tid, vtype, vno, tdate, do_no, qty, rate, amount, bpid, broker_name,
         party_name, item_name) in rows:
        brokerage = calculate_brokerage(bpid, qty, amount)
        results.append({
            "transaction_id": tid, "voucher_display": format_voucher_no(vtype, vno),
            "voucher_type": vtype, "date": tdate, "do_no": do_no, "qty": qty, "rate": rate,
            "amount": amount, "broker_party_id": bpid, "broker_name": broker_name,
            "party_name": party_name, "item_name": item_name, "brokerage": brokerage,
        })
    return results


def get_brokerage_paid(broker_party_id):
    """All-time total actually paid to this broker - see
    record_brokerage_payment(). Brokerage stays its own isolated system
    (never touches the Payable Ledger, Cash Book, or Trial Balance/
    Balance Sheet, same as the amount owed itself never has) - this is
    purely for the Brokerage report to show Owed / Paid / Balance."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT SUM(amount) FROM transactions WHERE voucher_type = 'BROKERAGE' AND party_id = ?",
                (broker_party_id,))
    total = cur.fetchone()[0] or 0.0
    conn.close()
    return total


def record_brokerage_payment(broker_party_id, date_, amount, description=""):
    conn = get_connection()
    cur = conn.cursor()
    voucher_no = get_next_voucher_no("BROKERAGE", conn)
    cur.execute(
        """INSERT INTO transactions (date, voucher_type, voucher_no, party_id, amount, description, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (date_, "BROKERAGE", voucher_no, broker_party_id, amount, description, now_iso()),
    )
    conn.commit()
    conn.close()
    return voucher_no


def get_brokerage_summary(broker_party_id=None):
    """One row per broker: total owed (calculated from Sale/Purchase
    entries), total paid (see record_brokerage_payment), and the
    balance still outstanding."""
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT id, name FROM parties WHERE party_type = 'Broker'"
    params = []
    if broker_party_id:
        query += " AND id = ?"
        params.append(broker_party_id)
    query += " ORDER BY name"
    cur.execute(query, params)
    brokers = cur.fetchall()
    conn.close()

    detail_rows = get_brokerage_report(broker_party_id=broker_party_id)
    owed_by_broker = {}
    for r in detail_rows:
        owed_by_broker[r["broker_party_id"]] = owed_by_broker.get(r["broker_party_id"], 0.0) + r["brokerage"]

    results = []
    for bid, name in brokers:
        owed = owed_by_broker.get(bid, 0.0)
        paid = get_brokerage_paid(bid)
        if owed == 0 and paid == 0:
            continue
        results.append({"broker_id": bid, "broker_name": name, "owed": owed, "paid": paid, "balance": owed - paid})
    return results


def get_stock_qty(quality_id):
    """opening_balance (qty) + SUM(PURCHASE qty) - SUM(SALE qty)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT opening_balance FROM quality WHERE id = ?", (quality_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return 0.0
    qty = row[0] or 0.0
    cur.execute(
        "SELECT voucher_type, SUM(qty) FROM transactions WHERE quality_id = ? GROUP BY voucher_type",
        (quality_id,),
    )
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()
    qty += sums.get("PURCHASE", 0.0)
    qty -= sums.get("SALE", 0.0)
    return qty


def get_stock_qty_as_of(quality_id, as_of_date, conn=None):
    """Same as get_stock_qty but only counting PURCHASE/SALE transactions
    up to and including as_of_date - used for stock valuation at a
    specific point in time (Profit calculation's opening/closing stock)."""
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT opening_balance FROM quality WHERE id = ?", (quality_id,))
    row = cur.fetchone()
    if not row:
        if owns_conn:
            conn.close()
        return 0.0
    qty = row[0] or 0.0
    cur.execute(
        "SELECT voucher_type, SUM(qty) FROM transactions WHERE quality_id = ? AND date <= ? GROUP BY voucher_type",
        (quality_id, as_of_date),
    )
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    if owns_conn:
        conn.close()
    qty += sums.get("PURCHASE", 0.0)
    qty -= sums.get("SALE", 0.0)
    return qty


def get_weighted_avg_purchase_rate(quality_id, as_of_date=None, conn=None):
    """The item's purchase rate is mostly derived from actual PURCHASE
    transactions (which includes purchases that came from a delivered
    booking, since delivering a booking creates a normal PURCHASE
    transaction) - quantity-weighted average, standard practice for
    valuing mixed-cost stock. The opening stock quantity is blended in
    too, but ONLY when it was given a Purchase Rate at add/edit time
    (quality.purchase_rate > 0) - opening stock entered before that
    field existed defaults to 0 and is deliberately left out of the
    blend rather than dragging the average down toward a rate nobody
    actually set. Returns 0 if there's nothing to derive a rate from at
    all (no real purchases, and no priced opening stock)."""
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT opening_balance, purchase_rate FROM quality WHERE id = ?", (quality_id,))
    row = cur.fetchone()
    opening_qty, opening_rate = (row[0] or 0.0, row[1] or 0.0) if row else (0.0, 0.0)

    query = "SELECT qty, rate FROM transactions WHERE quality_id = ? AND voucher_type = 'PURCHASE'"
    params = [quality_id]
    if as_of_date:
        query += " AND date <= ?"
        params.append(as_of_date)
    cur.execute(query, params)
    rows = cur.fetchall()
    if owns_conn:
        conn.close()

    total_qty = sum((r[0] or 0) for r in rows)
    total_cost = sum((r[0] or 0) * (r[1] or 0) for r in rows)
    if opening_qty > 0 and opening_rate > 0:
        total_qty += opening_qty
        total_cost += opening_qty * opening_rate
    if total_qty <= 1e-9:
        return 0.0
    return total_cost / total_qty


def get_stock_value_as_of(as_of_date):
    """Total stock-on-hand across every item, valued at each item's
    weighted-average actual purchase rate (see
    get_weighted_avg_purchase_rate) - derived from real purchase
    history rather than a manually-maintained master rate."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM quality")
    items = cur.fetchall()
    total = 0.0
    for (quality_id,) in items:
        qty = get_stock_qty_as_of(quality_id, as_of_date, conn)
        rate = get_weighted_avg_purchase_rate(quality_id, as_of_date, conn)
        total += qty * rate
    conn.close()
    return total


# ---------------------------------------------------------------------
# Purchase/Sale ledger - three views of the same Purchase/Sale history,
# grouped by item instead of by party. "Overall" (get_quality_ledger) is
# one item's full chronological history with a running quantity
# balance, same idea as the Party Ledger. "By count" and "By rate"
# (get_quality_ledger_summary) are the same one-row-per-item rollup,
# just showing different columns from it - quantity totals for
# spotting your biggest-volume items, or rate min/avg/max for spotting
# your most price-variable ones.
# ---------------------------------------------------------------------
def get_quality_ledger(quality_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, city_area, sale_rate, opening_balance FROM quality WHERE id = ?", (quality_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    item = {"id": row[0], "name": row[1], "area": row[2], "sale_rate": row[3], "opening_balance": row[4] or 0.0}

    cur.execute(
        """SELECT t.id, t.date, t.voucher_type, t.voucher_no, p.name, t.qty, t.rate, t.amount, t.do_no
           FROM transactions t LEFT JOIN parties p ON p.id = t.party_id
           WHERE t.quality_id = ? AND t.voucher_type IN ('SALE', 'PURCHASE')
           ORDER BY t.date, t.id""",
        (quality_id,),
    )
    txns = cur.fetchall()
    conn.close()

    balance = item["opening_balance"]
    rows = []
    for tid, tdate, vtype, vno, pname, qty, rate, amount, do_no in txns:
        qty = qty or 0.0
        balance += qty if vtype == "PURCHASE" else -qty
        rows.append({
            "id": tid, "date": tdate, "voucher_type": vtype,
            "voucher_display": format_voucher_no(vtype, vno), "do_no": do_no,
            "party_name": pname, "qty": qty, "rate": rate, "amount": amount, "balance": balance,
        })
    return {"item": item, "rows": rows, "closing_balance": balance}


def get_quality_ledger_summary():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, city_area FROM quality ORDER BY name")
    items = cur.fetchall()

    cur.execute(
        "SELECT quality_id, voucher_type, SUM(qty), MIN(rate), AVG(rate), MAX(rate) "
        "FROM transactions WHERE voucher_type IN ('SALE', 'PURCHASE') AND quality_id IS NOT NULL "
        "GROUP BY quality_id, voucher_type"
    )
    agg = {}
    for qid, vtype, sum_qty, min_rate, avg_rate, max_rate in cur.fetchall():
        agg.setdefault(qid, {})[vtype] = {
            "qty": sum_qty or 0.0, "min_rate": min_rate or 0.0,
            "avg_rate": avg_rate or 0.0, "max_rate": max_rate or 0.0,
        }
    conn.close()

    empty = {"qty": 0.0, "min_rate": 0.0, "avg_rate": 0.0, "max_rate": 0.0}
    results = []
    for qid, name, area in items:
        a = agg.get(qid, {})
        purchase = a.get("PURCHASE", empty)
        sale = a.get("SALE", empty)
        if purchase["qty"] == 0 and sale["qty"] == 0:
            continue
        results.append({
            "id": qid, "name": name, "area": area,
            "purchased_qty": purchase["qty"], "sold_qty": sale["qty"], "net_qty": purchase["qty"] - sale["qty"],
            "purchase_rate_min": purchase["min_rate"], "purchase_rate_avg": purchase["avg_rate"], "purchase_rate_max": purchase["max_rate"],
            "sale_rate_min": sale["min_rate"], "sale_rate_avg": sale["avg_rate"], "sale_rate_max": sale["max_rate"],
        })
    return results


def suggest_next_do_no(voucher_type="SALE"):
    """The next D.O. number to pre-fill in the entry form - reuses the
    same 1, 2, 3... sequence as the invoice numbering (see
    get_next_voucher_no) so it starts at 1 and always moves forward,
    while staying a plain editable number the user can override."""
    return str(get_next_voucher_no(voucher_type))


# ---------------------------------------------------------------------
# Bookings - a forward contract/deal struck now ("sauda") for delivery
# later. Recording a booking does NOT move stock or touch either
# party's balance; only actually delivering against it (in full or in
# part) creates a real Sale/Purchase transaction, exactly like walking
# into the Purchase & Sale entry screen normally would. A booking can
# be partially delivered more than once - it stays "Open" with a
# shrinking remaining quantity until fully delivered or cancelled.
# ---------------------------------------------------------------------
def get_next_booking_no(conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(booking_no) FROM bookings")
    row = cur.fetchone()
    if owns_conn:
        conn.close()
    return (row[0] or 0) + 1


def format_booking_no(booking_no):
    if booking_no is None:
        return "BK-?"
    return f"BK-{int(booking_no):06d}"


def create_booking(voucher_type, date_, party_id, quality_id, qty, rate, delivery_terms=""):
    conn = get_connection()
    cur = conn.cursor()
    booking_no = get_next_booking_no(conn)
    amount = qty * rate
    cur.execute(
        """INSERT INTO bookings
           (booking_no, voucher_type, date, party_id, quality_id, qty, rate, amount,
            delivery_terms, status, delivered_qty, created_at)
           VALUES (?,?,?,?,?,?,?,?,?, 'Open', 0, ?)""",
        (booking_no, voucher_type, date_, party_id, quality_id, qty, rate, amount,
         delivery_terms, now_iso()),
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    return booking_id


def list_bookings(status=None):
    conn = get_connection()
    cur = conn.cursor()
    query = """SELECT b.id, b.booking_no, b.voucher_type, b.date, p.name, q.name,
                      b.qty, b.rate, b.amount, b.delivery_terms, b.status, b.delivered_qty
               FROM bookings b
               LEFT JOIN parties p ON p.id = b.party_id
               LEFT JOIN quality q ON q.id = b.quality_id"""
    params = []
    if status:
        query += " WHERE b.status = ?"
        params.append(status)
    query += " ORDER BY b.id DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    results = []
    for (bid, bno, vtype, bdate, party_name, item_name, qty, rate, amount,
         terms, status_, delivered_qty) in rows:
        results.append({
            "id": bid, "booking_display": format_booking_no(bno), "voucher_type": vtype,
            "date": bdate, "party_name": party_name, "item_name": item_name,
            "qty": qty, "rate": rate, "amount": amount, "delivery_terms": terms,
            "status": status_, "delivered_qty": delivered_qty, "remaining_qty": qty - delivered_qty,
        })
    return results


def get_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT b.id, b.booking_no, b.voucher_type, b.date, b.party_id, b.quality_id,
                  p.name, q.name, b.qty, b.rate, b.amount, b.delivery_terms, b.status, b.delivered_qty
           FROM bookings b
           LEFT JOIN parties p ON p.id = b.party_id
           LEFT JOIN quality q ON q.id = b.quality_id
           WHERE b.id = ?""",
        (booking_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    (bid, bno, vtype, bdate, party_id, quality_id, party_name, item_name,
     qty, rate, amount, terms, status_, delivered_qty) = row
    return {
        "id": bid, "booking_display": format_booking_no(bno), "voucher_type": vtype,
        "date": bdate, "party_id": party_id, "quality_id": quality_id,
        "party_name": party_name, "item_name": item_name, "qty": qty, "rate": rate,
        "amount": amount, "delivery_terms": terms, "status": status_,
        "delivered_qty": delivered_qty, "remaining_qty": qty - delivered_qty,
    }


def deliver_booking(booking_id, deliver_qty, do_no="", credit_days=0, mode="Cash",
                     cheque_no="", description="", delivery_date=None):
    """Converts (all or part of) a booking into a real Sale/Purchase
    transaction - the same kind of transaction the Purchase & Sale
    entry screen creates, so it flows into stock, the receivable/
    payable ledgers, and everywhere else normally. Uses the booking's
    original rate. Returns the new transaction id."""
    booking = get_booking(booking_id)
    if not booking:
        raise ValueError("Booking not found")
    if booking["status"] == "Cancelled":
        raise ValueError("This booking was cancelled")
    if deliver_qty <= 0 or deliver_qty > booking["remaining_qty"] + 1e-9:
        raise ValueError(f"Delivery quantity must be between 0 and {booking['remaining_qty']:g}")

    if delivery_date is None:
        delivery_date = date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()
    voucher_no = get_next_voucher_no(booking["voucher_type"], conn)
    amount = deliver_qty * booking["rate"]
    cur.execute(
        """INSERT INTO transactions
           (date, voucher_type, voucher_no, do_no, party_id, broker, quality_id, qty, rate, amount,
            cash_or_cheque, cheque_no, description, credit_days, booking_id, created_at)
           VALUES (?,?,?,?,?,NULL,?,?,?,?,?,?,?,?,?,?)""",
        (delivery_date, booking["voucher_type"], voucher_no, do_no or booking["booking_display"],
         booking["party_id"], booking["quality_id"], deliver_qty, booking["rate"], amount,
         mode, cheque_no, description or f"Delivery against {booking['booking_display']}",
         credit_days, booking_id, now_iso()),
    )
    new_txn_id = cur.lastrowid

    new_delivered = booking["delivered_qty"] + deliver_qty
    new_status = "Delivered" if new_delivered >= booking["qty"] - 1e-9 else "Open"
    cur.execute(
        "UPDATE bookings SET delivered_qty = ?, status = ?, transaction_id = ? WHERE id = ?",
        (new_delivered, new_status, new_txn_id, booking_id),
    )
    conn.commit()
    conn.close()
    return new_txn_id


def get_booking_deliveries(booking_id):
    """Every individual delivery ever made against this booking - the
    full breakout, not just the running delivered_qty total."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT id, voucher_type, voucher_no, date, do_no, qty, rate, amount, cash_or_cheque, description
           FROM transactions WHERE booking_id = ? ORDER BY date, id""",
        (booking_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"transaction_id": r[0], "voucher_display": format_voucher_no(r[1], r[2]), "date": r[3],
         "do_no": r[4], "qty": r[5], "rate": r[6], "amount": r[7], "mode": r[8], "description": r[9]}
        for r in rows
    ]


def cancel_booking(booking_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ? AND delivered_qty = 0", (booking_id,))
    changed = cur.rowcount
    conn.commit()
    conn.close()
    return changed > 0


# ---------------------------------------------------------------------
# Invoice aging (FIFO settlement) - the accurate, up-to-date version of
# the Receivable/Payable ledgers. RECEIPTs/PAYMENTs aren't linked to a
# specific invoice in this schema (they're recorded against the party
# as a whole), so to know which invoices are actually still unpaid -
# and by how much - we apply each payment against that party's oldest
# still-open invoice first (first-in, first-out), same as standard
# accounting practice. What's left in the queue after processing every
# payment up to as_of_date is the real, current outstanding balance,
# invoice by invoice.
# ---------------------------------------------------------------------
def _fifo_aging(invoice_voucher_type, settling_voucher_type, as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today().isoformat()
    elif hasattr(as_of_date, "isoformat"):
        as_of_date = as_of_date.isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, opening_balance, created_at, phone FROM parties "
        "WHERE is_gl = 0 AND party_type NOT IN ('Expense', 'Bank') ORDER BY name"
    )
    parties = cur.fetchall()

    results = []
    for party_id, party_name, opening_balance, created_at, party_phone in parties:
        cur.execute(
            """SELECT id, voucher_no, date, voucher_type, do_no, quality_id, qty, rate, amount, credit_days
               FROM transactions
               WHERE party_id = ? AND voucher_type IN (?, ?) AND date <= ?
               ORDER BY date, id""",
            (party_id, invoice_voucher_type, settling_voucher_type, as_of_date),
        )
        rows = cur.fetchall()

        queue = []  # open invoices, oldest first

        # detailed imported opening entries (individual outstanding
        # invoices from a previous system) take priority over the
        # single lump-sum opening_balance number, since they carry the
        # actual breakdown - date, reference, item - forward. Only fall
        # back to the single number if no detailed entries exist for
        # this party in this direction, so existing users who set
        # opening_balance the simple way aren't affected.
        entry_type = "receivable" if invoice_voucher_type == "SALE" else "payable"
        cur.execute(
            "SELECT id, date, reference, item_name, qty, rate, amount, credit_days "
            "FROM opening_entries WHERE party_id = ? AND entry_type = ? AND date <= ? ORDER BY date, id",
            (party_id, entry_type, as_of_date),
        )
        opening_rows = cur.fetchall()

        if opening_rows:
            for (oe_id, oe_date, reference, item_name, qty, rate, amount, credit_days) in opening_rows:
                queue.append({
                    "id": None, "voucher_no": None, "date": oe_date or as_of_date,
                    "do_no": reference or "Opening", "quality_id": None, "qty": qty, "rate": rate,
                    "full_amount": amount or 0.0, "remaining": amount or 0.0,
                    "credit_days": credit_days or 0, "opening_item_name": item_name,
                })
        else:
            # the party's starting balance when they were first added (an
            # existing debt from before this software was used) counts as
            # the very first "invoice" in the FIFO queue, same as a real
            # opening balance carried into a ledger
            opening_balance = opening_balance or 0.0
            relevant_opening = 0.0
            if invoice_voucher_type == "SALE" and opening_balance > 1e-9:
                relevant_opening = opening_balance
            elif invoice_voucher_type == "PURCHASE" and opening_balance < -1e-9:
                relevant_opening = -opening_balance
            if relevant_opening > 1e-9:
                opening_date = str(created_at)[:10] if created_at else as_of_date
                queue.append({
                    "id": None, "voucher_no": None, "date": opening_date, "do_no": "Opening Balance",
                    "quality_id": None, "qty": None, "rate": None,
                    "full_amount": relevant_opening, "remaining": relevant_opening,
                    "credit_days": 0, "opening_item_name": None,
                })

        for (txn_id, voucher_no, t_date, v_type, do_no, quality_id, qty, rate,
             amount, credit_days) in rows:
            if v_type == invoice_voucher_type:
                queue.append({
                    "id": txn_id, "voucher_no": voucher_no, "date": t_date, "do_no": do_no,
                    "quality_id": quality_id, "qty": qty, "rate": rate,
                    "full_amount": amount or 0.0, "remaining": amount or 0.0,
                    "credit_days": credit_days,
                })
            else:  # settling payment (RECEIPT or PAYMENT)
                remaining_payment = amount or 0.0
                i = 0
                while remaining_payment > 1e-9 and i < len(queue):
                    inv = queue[i]
                    if inv["remaining"] > 1e-9:
                        applied = min(inv["remaining"], remaining_payment)
                        inv["remaining"] -= applied
                        remaining_payment -= applied
                    i += 1

        # look up item names in one go
        quality_ids = {inv["quality_id"] for inv in queue if inv["quality_id"]}
        item_names = {}
        if quality_ids:
            qmarks = ",".join("?" * len(quality_ids))
            cur.execute(f"SELECT id, name FROM quality WHERE id IN ({qmarks})", tuple(quality_ids))
            item_names = dict(cur.fetchall())

        for inv in queue:
            if inv["remaining"] <= 1e-9:
                continue  # fully paid, not outstanding
            voucher_str_no = (format_voucher_no(invoice_voucher_type, inv["voucher_no"])
                               if inv["voucher_no"] is not None else (inv["do_no"] or "Opening Balance"))
            due_date, status, days, is_overdue = compute_due_status(inv["date"], inv["credit_days"], as_of_date)
            item_display = item_names.get(inv["quality_id"], "-") if inv["quality_id"] else (inv.get("opening_item_name") or "-")
            results.append({
                "party_id": party_id, "party_name": party_name, "party_phone": party_phone,
                "voucher_no": inv["voucher_no"], "voucher_display": voucher_str_no,
                "date": inv["date"], "do_no": inv["do_no"],
                "item_name": item_display,
                "qty": inv["qty"], "rate": inv["rate"],
                "full_amount": inv["full_amount"], "outstanding": inv["remaining"],
                "credit_days": inv["credit_days"] or 0, "due_date": due_date,
                "status": status, "days": days, "is_overdue": is_overdue,
            })

    conn.close()
    results.sort(key=lambda r: (r["party_name"], r["date"]))
    return results


def get_receivable_aging(as_of_date=None):
    """Every SALE invoice still (fully or partially) unpaid as of
    as_of_date, net of every RECEIPT posted against that party,
    applied oldest-invoice-first. This is the true, up-to-date
    receivable position - not just a raw list of every sale ever
    made."""
    return _fifo_aging("SALE", "RECEIPT", as_of_date)


def get_payable_aging(as_of_date=None):
    """Same idea for what you owe suppliers: every PURCHASE invoice
    still unpaid, net of every PAYMENT, oldest-first."""
    return _fifo_aging("PURCHASE", "PAYMENT", as_of_date)


# ---------------------------------------------------------------------
# Cash position - used by the Cash Book's opening/closing balance.
# Cash actually moves on RECEIPT, PAYMENT, EXPENSE, CAPITAL_IN /
# CAPITAL_OUT, and CONTRA_DR / CONTRA_CR (Sale/Purchase on their own are
# just invoices - the cash only moves when a Receipt or Payment is later
# recorded against them). Contra entries are treated as real cash
# movement here (e.g. "Cash to Bank") - every contra entry balances
# Dr == Cr across its own legs by construction, so including them never
# changes the ALL-TIME closing balance, only which period an in-range
# movement is counted in and whether it's visible in the Cash Book at all.
# ---------------------------------------------------------------------
CASH_IN_TYPES = ("RECEIPT", "CAPITAL_IN", "CONTRA_CR")
CASH_OUT_TYPES = ("PAYMENT", "EXPENSE", "CAPITAL_OUT", "CONTRA_DR")


def get_cash_movement(date_from=None, date_to=None):
    """Net cash movement (in - out) for transactions strictly between
    date_from and date_to inclusive. Pass None for an open-ended side."""
    conn = get_connection()
    cur = conn.cursor()
    all_types = list(CASH_IN_TYPES) + list(CASH_OUT_TYPES)
    query = f"SELECT voucher_type, SUM(amount) FROM transactions WHERE voucher_type IN ({','.join('?' * len(all_types))})"
    params = list(all_types)
    if date_from is not None:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to is not None:
        query += " AND date <= ?"
        params.append(date_to)
    query += " GROUP BY voucher_type"
    cur.execute(query, params)
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()
    cash_in = sum(sums.get(t, 0.0) for t in CASH_IN_TYPES)
    cash_out = sum(sums.get(t, 0.0) for t in CASH_OUT_TYPES)
    return cash_in - cash_out


def get_cash_opening_balance(as_of_date):
    """Opening cash balance for a Cash Book period starting at
    as_of_date: the user's manually-set starting cash figure (see
    settings.get_opening_cash_balance), plus every cash movement from
    that starting date up to (but not including) as_of_date."""
    try:
        import settings as _settings
        opening_amount, opening_date = _settings.get_opening_cash_balance()
    except Exception:
        opening_amount, opening_date = 0.0, None

    if not opening_date:
        # no manual starting point set - just derive purely from history
        return get_cash_movement(date_from=None, date_to=_day_before(as_of_date))
    return opening_amount + get_cash_movement(date_from=opening_date, date_to=_day_before(as_of_date))


def _day_before(iso_date_str):
    try:
        d = date.fromisoformat(str(iso_date_str)[:10])
        return (d - timedelta(days=1)).isoformat()
    except (ValueError, TypeError):
        return iso_date_str


# ---------------------------------------------------------------------
# T-account view of the Cash Book: classic two-column ledger. Right
# side (credit / money in) = Opening Balance, Receipts, Capital
# Introduced. Left side (debit / money out) = Payments, Capital
# Withdrawn, Expense vouchers. Each entry carries its own reference
# (invoice/voucher) number. If one side totals more than the other,
# a "Balance c/d" (carried down) line is added to the smaller side so
# both columns foot to the same total - the standard way a T-account
# is squared off at period end.
# ---------------------------------------------------------------------
def get_cash_taccount(date_from, date_to):
    opening_balance = get_cash_opening_balance(date_from)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.id, t.voucher_type, t.voucher_no, t.date, p.name, t.amount, t.description
           FROM transactions t LEFT JOIN parties p ON p.id = t.party_id
           WHERE t.voucher_type IN ('RECEIPT','PAYMENT','EXPENSE','CAPITAL_IN','CAPITAL_OUT','CONTRA_DR','CONTRA_CR')
             AND t.date BETWEEN ? AND ?
           ORDER BY t.date, t.id""",
        (date_from, date_to),
    )
    rows = cur.fetchall()
    conn.close()

    credit_entries = []  # right side: money in
    debit_entries = []   # left side: money out

    if opening_balance >= 0:
        credit_entries.append({"ref": "b/f", "date": date_from, "party": "Opening Balance",
                                "amount": opening_balance, "remarks": ""})
    else:
        debit_entries.append({"ref": "b/f", "date": date_from, "party": "Opening Balance (overdrawn)",
                               "amount": -opening_balance, "remarks": ""})

    for txn_id, v_type, voucher_no, t_date, party_name, amount, desc in rows:
        amount = amount or 0.0
        ref = format_voucher_no(v_type, voucher_no)
        entry = {"ref": ref, "date": t_date, "party": party_name or desc or "-",
                 "amount": amount, "remarks": desc or ""}
        if v_type in CASH_IN_TYPES:
            credit_entries.append(entry)
        else:
            debit_entries.append(entry)

    total_credit = sum(e["amount"] for e in credit_entries)
    total_debit = sum(e["amount"] for e in debit_entries)

    if total_credit > total_debit:
        debit_entries.append({"ref": "c/d", "date": date_to, "party": "Balance carried down",
                               "amount": total_credit - total_debit, "remarks": ""})
    elif total_debit > total_credit:
        credit_entries.append({"ref": "c/d", "date": date_to, "party": "Balance carried down",
                                "amount": total_debit - total_credit, "remarks": ""})

    closing_balance = total_credit - sum(
        e["amount"] for e in debit_entries if e["ref"] != "c/d"
    )

    return {
        "credit_entries": credit_entries, "debit_entries": debit_entries,
        "total_credit": max(total_credit, total_debit), "total_debit": max(total_credit, total_debit),
        "opening_balance": opening_balance, "closing_balance": closing_balance,
    }


# ---------------------------------------------------------------------
# Profit calculation. Gross Profit = Sales - Cost of Goods Sold, where
# COGS = Purchases + Opening Stock Value - Closing Stock Value (both
# valued at each item's purchase rate - see get_stock_value_as_of).
# This is the standard trading-account adjustment: goods bought but
# still sitting in the warehouse unsold shouldn't count against
# profit, since they're still an asset, not a cost, until they're
# actually sold. Net Profit = Gross Profit - Home Expense - Office
# Expense for the same period.
# ---------------------------------------------------------------------
def get_profit_summary(date_from, date_to):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT voucher_type, SUM(amount) FROM transactions WHERE date BETWEEN ? AND ? GROUP BY voucher_type",
        (date_from, date_to),
    )
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()

    total_sales = sums.get("SALE", 0.0)
    total_purchases = sums.get("PURCHASE", 0.0)

    opening_stock_value = get_stock_value_as_of(_day_before(date_from))
    closing_stock_value = get_stock_value_as_of(date_to)
    cogs = total_purchases + opening_stock_value - closing_stock_value
    gross_profit = total_sales - cogs

    conn = get_connection()
    cur = conn.cursor()
    home_id = get_gl_party_id(GL_HOME_EXPENSE, conn)
    office_id = get_gl_party_id(GL_OFFICE_EXPENSE, conn)
    zakat_id = get_gl_party_id(GL_ZAKAT, conn)
    cur.execute(
        "SELECT party_id, SUM(amount) FROM transactions WHERE voucher_type = 'EXPENSE' "
        "AND party_id IN (?, ?, ?) AND date BETWEEN ? AND ? GROUP BY party_id",
        (home_id, office_id, zakat_id, date_from, date_to),
    )
    expense_sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()

    home_expense = expense_sums.get(home_id, 0.0)
    office_expense = expense_sums.get(office_id, 0.0)
    zakat_expense = expense_sums.get(zakat_id, 0.0)
    # Zakat is a personal draw against capital, not a business cost - it
    # does NOT reduce trading profit (see get_capital_summary, where it
    # reduces the Capital Account balance directly instead). Still
    # returned here for reference/display.
    net_profit = gross_profit - home_expense - office_expense

    return {
        "total_sales": total_sales, "total_purchases": total_purchases,
        "opening_stock_value": opening_stock_value, "closing_stock_value": closing_stock_value,
        "cogs": cogs, "gross_profit": gross_profit, "home_expense": home_expense,
        "office_expense": office_expense, "zakat_expense": zakat_expense, "net_profit": net_profit,
    }


def get_capital_summary(date_from=None, date_to=None):
    """Capital introduced vs withdrawn by the owner, and the running
    capital account balance (all-time, regardless of date filter - the
    date filter only limits which entries are listed). Zakat (paid from
    the Zakat GL party, tracked separately - see get_gl_party_id) is a
    personal draw against capital, not a business expense, so its
    all-time total reduces net_capital directly here rather than
    reducing Net Profit (see get_profit_summary)."""
    conn = get_connection()
    cur = conn.cursor()
    capital_id = get_gl_party_id(GL_CAPITAL, conn)
    zakat_id = get_gl_party_id(GL_ZAKAT, conn)

    query = "SELECT id, voucher_no, date, voucher_type, amount, description FROM transactions WHERE party_id = ?"
    params = [capital_id]
    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params += [date_from, date_to]
    query += " ORDER BY date, id"
    cur.execute(query, params)
    rows = cur.fetchall()

    cur.execute(
        "SELECT voucher_type, SUM(amount) FROM transactions WHERE party_id = ? GROUP BY voucher_type",
        (capital_id,),
    )
    sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    cur.execute("SELECT SUM(amount) FROM transactions WHERE party_id = ? AND voucher_type = 'EXPENSE'", (zakat_id,))
    zakat_total = cur.fetchone()[0] or 0.0
    conn.close()

    total_in = sums.get("CAPITAL_IN", 0.0)
    total_out = sums.get("CAPITAL_OUT", 0.0) + zakat_total
    return {
        "entries": rows, "total_in": total_in, "total_out": total_out,
        "zakat_total": zakat_total, "net_capital": total_in - total_out,
    }


# ---------------------------------------------------------------------
# Balance sheet - Assets = Liabilities + Equity, as of a given date
# (defaults to today). Reuses the same building blocks the Trial
# Balance and Profit & Capital reports already use and that are already
# covered by their own tests - get_party_balance for each party's AR/AP
# position, get_profit_summary (called across ALL of history) for the
# stock-adjusted Retained Earnings figure and today's Closing Stock
# Value, get_capital_summary for the Capital Account, get_cash_movement
# for the Cash position - so nothing here is calculated a fourth
# different way that could quietly drift out of sync with those.
#
# Same idea as the Trial Balance's Opening Balance Equity plug, extended
# to cover the one more starting point a balance sheet actually needs:
# each item's PRICED opening stock (quality.purchase_rate - see
# get_weighted_avg_purchase_rate) is inventory that existed before this
# system started tracking it, with no recorded transaction behind it -
# exactly like an opening party balance or the manually-set opening
# cash figure, it needs its own equity plug or Assets won't equal
# Liabilities + Equity once Closing Stock Value is included as an asset.
# ---------------------------------------------------------------------
def get_balance_sheet(as_of_date=None):
    if as_of_date is None:
        as_of_date = date.today().isoformat()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM parties WHERE is_gl = 0")
    party_rows = cur.fetchall()
    cur.execute("SELECT COALESCE(SUM(opening_balance), 0) FROM parties WHERE is_gl = 0")
    total_party_opening = cur.fetchone()[0] or 0.0
    cur.execute("SELECT COALESCE(SUM(opening_balance * purchase_rate), 0) FROM quality "
                "WHERE opening_balance > 0 AND purchase_rate > 0")
    opening_stock_equity = cur.fetchone()[0] or 0.0
    conn.close()

    receivables, payables = [], []
    for party_id, name in party_rows:
        balance = get_party_balance(party_id)
        if balance > 1e-9:
            receivables.append({"name": name, "amount": balance})
        elif balance < -1e-9:
            payables.append({"name": name, "amount": -balance})
    receivables.sort(key=lambda r: -r["amount"])
    payables.sort(key=lambda p: -p["amount"])

    opening_cash, opening_cash_date = 0.0, None
    try:
        import settings as _settings
        opening_cash, opening_cash_date = _settings.get_opening_cash_balance()
    except Exception:
        pass
    opening_cash = opening_cash or 0.0
    cash_balance = opening_cash + get_cash_movement(date_from=opening_cash_date, date_to=as_of_date)

    stock_value = get_stock_value_as_of(as_of_date)
    # "since inception" sentinel for get_profit_summary's date_from - far
    # enough back that no real business predates it, but not so early
    # that _day_before()'s date arithmetic underflows Python's date range
    profit = get_profit_summary("1901-01-01", as_of_date)
    capital = get_capital_summary()

    total_assets = cash_balance + sum(r["amount"] for r in receivables) + stock_value
    total_liabilities = sum(p["amount"] for p in payables)
    opening_balance_equity = total_party_opening + opening_cash + opening_stock_equity
    total_equity = capital["net_capital"] + opening_balance_equity + profit["net_profit"]

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash_balance,
        "receivables": receivables,
        "stock_value": stock_value,
        "total_assets": total_assets,
        "payables": payables,
        "total_liabilities": total_liabilities,
        "capital": capital["net_capital"],
        "opening_balance_equity": opening_balance_equity,
        "retained_earnings": profit["net_profit"],
        "total_equity": total_equity,
        "total_liabilities_and_equity": total_liabilities + total_equity,
    }


# ---------------------------------------------------------------------
# Trial balance - a REAL one: every account shown once, its net balance
# in whichever column (Debit/Credit) matches its sign, and the two
# columns always foot to the same total. That last part isn't optional
# for something calling itself a trial balance, so it's worth spelling
# out why this needs more than "sum up what's in the parties table":
#
# Every party row (customer/supplier/Bank/Expense-type, plus the
# hardcoded GL rows - Home/Office Expense, Zakat, Capital Account) only
# ever records ONE side of a transaction. A Sale debits the customer,
# but nothing anywhere records the matching credit to a "Sales" account;
# a Receipt credits the customer, but nothing records the matching debit
# to "Cash". Add up only the party sides and the two columns will never
# balance - not a bug in the arithmetic, just half the ledger missing.
#
# So this function adds the three counter-accounts this app never
# stores as rows - Sales, Purchases, Cash (derived exactly like the Cash
# Book's own balance - see get_cash_movement/get_cash_opening_balance) -
# plus one more: every party's opening_balance (and the manually-set
# opening cash figure) is itself a starting number with no recorded
# origin, so it needs its own counter-entry too, same as any other
# opening balance in a real set of books. That's "Opening Balance
# Equity" below. With all four included, the columns are guaranteed to
# foot to the same total (each of Sale/Purchase/Receipt/Payment/opening/
# opening-cash appears exactly once as a debit somewhere and once as a
# credit somewhere else, across the whole set of rows).
# ---------------------------------------------------------------------
def get_trial_balance():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, opening_balance FROM parties ORDER BY name")
    party_rows = cur.fetchall()

    cur.execute("SELECT party_id, voucher_type, SUM(amount) FROM transactions GROUP BY party_id, voucher_type")
    per_party_sums = {}
    for party_id, v_type, total in cur.fetchall():
        per_party_sums.setdefault(party_id, {})[v_type] = total or 0.0

    cur.execute("SELECT voucher_type, SUM(amount) FROM transactions GROUP BY voucher_type")
    global_sums = {r[0]: (r[1] or 0.0) for r in cur.fetchall()}
    conn.close()

    rows = []
    total_debit = total_credit = 0.0

    def add_row(name, debit, credit):
        nonlocal total_debit, total_credit
        if abs(debit) < 0.005 and abs(credit) < 0.005:
            return
        total_debit += debit
        total_credit += credit
        rows.append({"name": name, "debit": debit, "credit": credit, "balance": debit - credit})

    total_opening = 0.0
    for party_id, name, opening_balance in party_rows:
        opening_balance = opening_balance or 0.0
        total_opening += opening_balance
        sums = per_party_sums.get(party_id, {})
        # CONTRA_DR/EXPENSE/CAPITAL_OUT sit on the debit side (same
        # direction as Sale/Payment against whichever party they landed
        # on); CONTRA_CR/CAPITAL_IN sit on the credit side. For an
        # ordinary customer/supplier these are all just 0.
        debit = (max(opening_balance, 0)
                 + sums.get("SALE", 0.0) + sums.get("PAYMENT", 0.0)
                 + sums.get("CONTRA_DR", 0.0) + sums.get("EXPENSE", 0.0) + sums.get("CAPITAL_OUT", 0.0))
        credit = (max(-opening_balance, 0)
                  + sums.get("PURCHASE", 0.0) + sums.get("RECEIPT", 0.0)
                  + sums.get("CONTRA_CR", 0.0) + sums.get("CAPITAL_IN", 0.0))
        add_row(name, debit, credit)

    # --- the missing counter-accounts (see docstring-style comment above) ---
    add_row("Sales Account", 0.0, global_sums.get("SALE", 0.0))
    add_row("Purchase Account", global_sums.get("PURCHASE", 0.0), 0.0)

    opening_cash, opening_cash_date = 0.0, None
    try:
        import settings as _settings
        opening_cash, opening_cash_date = _settings.get_opening_cash_balance()
    except Exception:
        pass
    opening_cash = opening_cash or 0.0
    cash_balance = opening_cash + get_cash_movement(date_from=opening_cash_date, date_to=None)
    add_row("Cash Account", max(cash_balance, 0), max(-cash_balance, 0))

    opening_equity = total_opening + opening_cash
    add_row("Opening Balance Equity", max(-opening_equity, 0), max(opening_equity, 0))

    return rows, total_debit, total_credit


# ---------------------------------------------------------------------
# Contra entries - an internal transfer between two or more of your own
# parties (e.g. moving a balance from one account to another, or Cash
# to Bank) with no real sale/purchase behind it. Every leg of one
# contra entry shares the same reference number; the total Dr must
# equal the total Cr, same as a real double-entry contra voucher.
# Deliberately excluded from the Cash Book (it's a balance transfer,
# not a real cash-in/cash-out event) and from Receivable/Payable aging
# (only SALE/PURCHASE + RECEIPT/PAYMENT are considered there).
# ---------------------------------------------------------------------
def get_next_contra_no(conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(voucher_no) FROM transactions WHERE voucher_type IN ('CONTRA_DR','CONTRA_CR')")
    row = cur.fetchone()
    if owns_conn:
        conn.close()
    return (row[0] or 0) + 1


def create_contra_entry(date_, legs, description=""):
    """legs: list of dicts {party_id, direction ('DR' or 'CR'), amount}.
    Every leg shares one reference number. Raises ValueError if the
    entry doesn't balance (total Dr must equal total Cr)."""
    total_dr = sum(l["amount"] for l in legs if l["direction"] == "DR")
    total_cr = sum(l["amount"] for l in legs if l["direction"] == "CR")
    if abs(total_dr - total_cr) > 0.01:
        raise ValueError(f"Entry doesn't balance: Dr {total_dr:,.2f} vs Cr {total_cr:,.2f}")
    if len(legs) < 2:
        raise ValueError("A contra entry needs at least two parties.")

    conn = get_connection()
    cur = conn.cursor()
    voucher_no = get_next_contra_no(conn)
    for leg in legs:
        voucher_type = "CONTRA_DR" if leg["direction"] == "DR" else "CONTRA_CR"
        cur.execute(
            """INSERT INTO transactions
               (date, voucher_type, voucher_no, party_id, amount, description, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (date_, voucher_type, voucher_no, leg["party_id"], leg["amount"], description, now_iso()),
        )
    conn.commit()
    conn.close()
    return voucher_no


def list_contra_entries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.voucher_no, t.date, t.voucher_type, p.name, t.amount, t.description
           FROM transactions t LEFT JOIN parties p ON p.id = t.party_id
           WHERE t.voucher_type IN ('CONTRA_DR','CONTRA_CR')
           ORDER BY t.voucher_no DESC, t.voucher_type"""
    )
    rows = cur.fetchall()
    conn.close()
    groups = {}
    order = []
    for vno, d, vtype, pname, amount, desc in rows:
        if vno not in groups:
            groups[vno] = {"voucher_no": vno, "voucher_display": format_voucher_no("CONTRA_DR", vno),
                           "date": d, "description": desc, "legs": []}
            order.append(vno)
        groups[vno]["legs"].append({
            "party_name": pname, "direction": "Dr" if vtype == "CONTRA_DR" else "Cr", "amount": amount,
        })
    return [groups[v] for v in order]


# =======================================================================
# KIRYANA MODULE — a separate, simpler inventory/sales/purchases/cash
# engine for grocery-store style businesses selected from the post-login
# business-type picker. Deliberately independent of the parties/quality/
# transactions tables above (no D.O. numbers, brokers, or weighted-average
# purchase rate) since a Kiryana store's needs are much simpler than the
# yarn-trading workflow those tables were built for - it only shares the
# tenant database file, not the schema. Both Sales and Purchases can be
# Cash or Credit; credit balances (receivable from customers, payable to
# suppliers) are settled via kiryana_payments and viewable on the Ledger
# page for either party type.
# =======================================================================
def _init_kiryana_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kiryana_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT,
            purchase_rate REAL DEFAULT 0,
            sale_rate REAL DEFAULT 0,
            stock_qty REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    # --- migration: barcode, added after kiryana_items already shipped ---
    cur.execute("PRAGMA table_info(kiryana_items)")
    existing_item_cols = {row[1] for row in cur.fetchall()}
    if "barcode" not in existing_item_cols:
        cur.execute("ALTER TABLE kiryana_items ADD COLUMN barcode TEXT")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_items_barcode ON kiryana_items(barcode)")
    # --- migration: reorder_level (low-stock alerts), category, and bulk
    # purchase-unit conversion (e.g. buy by the carton, sell by the piece) ---
    if "reorder_level" not in existing_item_cols:
        cur.execute("ALTER TABLE kiryana_items ADD COLUMN reorder_level REAL DEFAULT 0")
        conn.commit()
    if "category" not in existing_item_cols:
        cur.execute("ALTER TABLE kiryana_items ADD COLUMN category TEXT")
        conn.commit()
    if "purchase_unit" not in existing_item_cols:
        cur.execute("ALTER TABLE kiryana_items ADD COLUMN purchase_unit TEXT")
        conn.commit()
    if "conversion_factor" not in existing_item_cols:
        cur.execute("ALTER TABLE kiryana_items ADD COLUMN conversion_factor REAL DEFAULT 1")
        conn.commit()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kiryana_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            party_type TEXT NOT NULL DEFAULT 'Customer',
            opening_balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kiryana_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            party_id INTEGER,
            item_id INTEGER NOT NULL,
            qty REAL NOT NULL,
            rate REAL NOT NULL,
            amount REAL NOT NULL,
            mode TEXT NOT NULL DEFAULT 'Cash',
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES kiryana_parties (id),
            FOREIGN KEY (item_id) REFERENCES kiryana_items (id)
        )
    """)
    # --- migration: invoice_no, added so one Sale/Purchase can cover
    # multiple line items (each still its own row, sharing one number) ---
    cur.execute("PRAGMA table_info(kiryana_transactions)")
    existing_txn_cols = {row[1] for row in cur.fetchall()}
    if "invoice_no" not in existing_txn_cols:
        cur.execute("ALTER TABLE kiryana_transactions ADD COLUMN invoice_no INTEGER")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_txn_invoice ON kiryana_transactions(txn_type, invoice_no)")
    # --- migration: expiry_date, set on a PURCHASE line to track when
    # that batch of stock expires (informational - not consumed FIFO
    # against sales, just surfaced on an "Expiring Soon" dashboard card) ---
    if "expiry_date" not in existing_txn_cols:
        cur.execute("ALTER TABLE kiryana_transactions ADD COLUMN expiry_date TEXT")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_txn_expiry ON kiryana_transactions(expiry_date)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kiryana_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            party_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES kiryana_parties (id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kiryana_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT,
            description TEXT,
            amount REAL NOT NULL,
            created_at TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_txn_party ON kiryana_transactions(party_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_txn_item ON kiryana_transactions(item_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kiryana_payments_party ON kiryana_payments(party_id)")
    conn.commit()


_ITEM_COLUMNS = ("id, name, unit, purchase_rate, sale_rate, stock_qty, barcode, "
                 "reorder_level, category, purchase_unit, conversion_factor")


def _item_row_to_dict(row):
    return {"id": row[0], "name": row[1], "unit": row[2], "purchase_rate": row[3], "sale_rate": row[4],
            "stock_qty": row[5], "barcode": row[6], "reorder_level": row[7] or 0, "category": row[8],
            "purchase_unit": row[9], "conversion_factor": row[10] or 1}


def kiryana_list_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {_ITEM_COLUMNS} FROM kiryana_items ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_item_row_to_dict(r) for r in rows]


def kiryana_list_categories():
    """Distinct categories already in use, for the Category field's
    autocomplete suggestions - not a fixed list, since what makes sense
    varies shop to shop."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM kiryana_items WHERE category IS NOT NULL AND category != '' ORDER BY category")
    cats = [r[0] for r in cur.fetchall()]
    conn.close()
    return cats


def kiryana_add_item(name, unit, purchase_rate, sale_rate, opening_qty, barcode=None,
                      reorder_level=0, category=None, purchase_unit=None, conversion_factor=1):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kiryana_items (name, unit, purchase_rate, sale_rate, stock_qty, barcode,
               reorder_level, category, purchase_unit, conversion_factor, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (name, unit, purchase_rate, sale_rate, opening_qty, barcode or None,
             reorder_level or 0, category or None, purchase_unit or None, conversion_factor or 1, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_get_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_ITEM_COLUMNS} FROM kiryana_items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        return _item_row_to_dict(row) if row else None
    finally:
        conn.close()


def kiryana_get_item_by_barcode(barcode):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_ITEM_COLUMNS} FROM kiryana_items WHERE barcode = ?", (barcode,))
        row = cur.fetchone()
        return _item_row_to_dict(row) if row else None
    finally:
        conn.close()


def kiryana_update_item(item_id, name, unit, purchase_rate, sale_rate, stock_qty, barcode=None,
                         reorder_level=0, category=None, purchase_unit=None, conversion_factor=1):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE kiryana_items SET name = ?, unit = ?, purchase_rate = ?, sale_rate = ?, stock_qty = ?,
               barcode = ?, reorder_level = ?, category = ?, purchase_unit = ?, conversion_factor = ? WHERE id = ?""",
            (name, unit, purchase_rate, sale_rate, stock_qty, barcode or None,
             reorder_level or 0, category or None, purchase_unit or None, conversion_factor or 1, item_id),
        )
        conn.commit()
    finally:
        conn.close()


def kiryana_item_has_transactions(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM kiryana_transactions WHERE item_id = ?", (item_id,))
        return cur.fetchone()[0] > 0
    finally:
        conn.close()


def kiryana_delete_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kiryana_items WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()


def kiryana_list_parties(party_type=None):
    conn = get_connection()
    cur = conn.cursor()
    if party_type:
        cur.execute("SELECT id, name, phone, party_type, opening_balance FROM kiryana_parties "
                    "WHERE party_type = ? ORDER BY name", (party_type,))
    else:
        cur.execute("SELECT id, name, phone, party_type, opening_balance FROM kiryana_parties ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "phone": r[2], "party_type": r[3], "opening_balance": r[4]} for r in rows]


def kiryana_add_party(name, phone, party_type, opening_balance=0):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO kiryana_parties (name, phone, party_type, opening_balance, created_at) VALUES (?,?,?,?,?)",
            (name, phone, party_type, opening_balance, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_get_party(party_id, conn=None):
    own = conn is None
    conn = conn or get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, phone, party_type, opening_balance FROM kiryana_parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    if own:
        conn.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "phone": row[2], "party_type": row[3], "opening_balance": row[4]}


def kiryana_get_next_invoice_no(txn_type):
    """One invoice number per Save click, shared by every line item in
    that sale/purchase (each line is still its own kiryana_transactions
    row - see kiryana_record_sale/kiryana_record_purchase)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MAX(invoice_no) FROM kiryana_transactions WHERE txn_type = ?", (txn_type,))
        row = cur.fetchone()
        return (row[0] or 0) + 1
    finally:
        conn.close()


_INVOICE_PREFIXES = {"SALE": "SALE", "PURCHASE": "PUR", "SALE_RETURN": "SR", "PURCHASE_RETURN": "PR"}


def kiryana_format_invoice_no(txn_type, invoice_no):
    if not invoice_no:
        return "—"
    return f"{_INVOICE_PREFIXES.get(txn_type, txn_type)}-{invoice_no:06d}"


def kiryana_record_sale(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kiryana_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "SALE", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty - ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_record_purchase(date_, party_id, item_id, qty, rate, mode="Cash", description="", sale_rate=None,
                             invoice_no=None, expiry_date=None):
    """Records a Purchase, adds the qty to stock, and fixes the item's
    Purchase Rate to the rate just paid (same field shown on the
    Inventory page - a Purchase entry IS how you'd know the current
    buying price, so it should always reflect the latest one). When
    sale_rate is given, fixes the item's Sale Rate the same way -
    restocking and re-pricing happen in one step instead of needing a
    separate trip to Inventory. expiry_date (optional) marks this
    specific batch of stock for the Expiring Soon dashboard card - it's
    informational only, not consumed FIFO against later sales."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kiryana_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, expiry_date, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "PURCHASE", party_id, item_id, qty, rate, amount, mode, description, invoice_no,
             expiry_date or None, now_iso()),
        )
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty + ?, purchase_rate = ? WHERE id = ?",
                    (qty, rate, item_id))
        if sale_rate is not None:
            cur.execute("UPDATE kiryana_items SET sale_rate = ? WHERE id = ?", (sale_rate, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_record_sale_return(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    """A customer returning something they bought - the mirror image of
    kiryana_record_sale: stock comes back instead of leaving, and on
    Credit mode it reduces (rather than adds to) what the customer owes,
    via kiryana_party_ledger treating SALE_RETURN as a credit-side entry."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kiryana_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "SALE_RETURN", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty + ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_record_purchase_return(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    """Sending something back to a supplier - the mirror image of
    kiryana_record_purchase: stock leaves instead of arriving, and on
    Credit mode it reduces what's owed to that supplier."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO kiryana_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "PURCHASE_RETURN", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty - ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def kiryana_list_transactions(txn_type, limit=50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.id, t.date, t.party_id, p.name, t.item_id, i.name, t.qty, t.rate, t.amount, t.mode, t.description, t.invoice_no
           FROM kiryana_transactions t
           LEFT JOIN kiryana_parties p ON p.id = t.party_id
           LEFT JOIN kiryana_items i ON i.id = t.item_id
           WHERE t.txn_type = ?
           ORDER BY t.id DESC LIMIT ?""",
        (txn_type, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "party_id": r[2], "party": r[3] or "Walk-in", "item_id": r[4],
             "item": r[5], "qty": r[6], "rate": r[7], "amount": r[8], "mode": r[9], "description": r[10],
             "invoice_no": r[11], "invoice": kiryana_format_invoice_no(txn_type, r[11])}
            for r in rows]


def kiryana_list_invoices(txn_type, limit=50):
    """Recent Sale/Purchase entries grouped by invoice - one row per Save
    click, even though a multi-item sale/purchase is still one
    kiryana_transactions row per line underneath. Rows saved before
    invoice_no existed (or with no lines sharing a number for some other
    reason) each just become their own single-line 'invoice' here."""
    txns = kiryana_list_transactions(txn_type, limit=max(limit * 6, 100))
    groups, order = {}, []
    for t in txns:
        key = t["invoice_no"] if t["invoice_no"] is not None else f"single-{t['id']}"
        if key not in groups:
            groups[key] = {"invoice_no": t["invoice_no"], "invoice": t["invoice"], "date": t["date"],
                           "party": t["party"], "party_id": t["party_id"], "mode": t["mode"],
                           "description": t["description"], "total_amount": 0.0, "lines": []}
            order.append(key)
        groups[key]["total_amount"] += t["amount"]
        groups[key]["lines"].append(t)
    return [groups[k] for k in order[:limit]]


def kiryana_get_bill(txn_type, anchor_txn_id):
    """Every line item belonging to the same bill as anchor_txn_id - i.e.
    everything sharing its invoice_no, or just that one row if it predates
    invoice_no (or was never grouped). Used for the per-bill Print button
    on the Recent Sales/Purchases list, which only needs to know one line
    item's id to reprint the whole thing."""
    anchor = kiryana_get_transaction(anchor_txn_id)
    if not anchor or anchor["txn_type"] != txn_type:
        return None
    conn = get_connection()
    cur = conn.cursor()
    if anchor["invoice_no"] is not None:
        cur.execute(
            """SELECT t.id, t.date, t.qty, t.rate, t.amount, i.name
               FROM kiryana_transactions t LEFT JOIN kiryana_items i ON i.id = t.item_id
               WHERE t.txn_type = ? AND t.invoice_no = ? ORDER BY t.id""",
            (txn_type, anchor["invoice_no"]),
        )
        rows = cur.fetchall()
    else:
        cur.execute(
            """SELECT t.id, t.date, t.qty, t.rate, t.amount, i.name
               FROM kiryana_transactions t LEFT JOIN kiryana_items i ON i.id = t.item_id
               WHERE t.id = ?""",
            (anchor_txn_id,),
        )
        rows = cur.fetchall()
    conn.close()
    lines = [{"id": r[0], "date": r[1], "qty": r[2], "rate": r[3], "amount": r[4], "item": r[5]} for r in rows]
    party = kiryana_get_party(anchor["party_id"]) if anchor["party_id"] else None
    return {
        "invoice": kiryana_format_invoice_no(txn_type, anchor["invoice_no"]),
        "date": anchor["date"], "mode": anchor["mode"], "description": anchor["description"],
        "party": party, "lines": lines, "total": sum(l["amount"] for l in lines),
    }


def kiryana_party_ledger(party_id):
    """Chronological T-account statement for one party (Customer or
    Supplier): opening balance, every credit sale/purchase on their
    account (adds to what they owe / what's owed to them) as a debit,
    every payment AND every credit-mode return (reduces it) as a credit.
    Works for either party type - a Customer's debits come from credit
    Sales and credits from Payments Received + Sale Returns; a Supplier's
    debits come from credit Purchases and credits from Payments Made +
    Purchase Returns - but the shape returned is identical so one
    template can render both."""
    conn = get_connection()
    cur = conn.cursor()
    party = kiryana_get_party(party_id, conn)
    if not party:
        conn.close()
        return None

    is_customer = party["party_type"] == "Customer"
    txn_type = "SALE" if is_customer else "PURCHASE"
    return_type = "SALE_RETURN" if is_customer else "PURCHASE_RETURN"
    txn_label = "Sale (Credit)" if is_customer else "Purchase (Credit)"
    return_label = "Sale Return" if is_customer else "Purchase Return"

    cur.execute(
        """SELECT t.id, t.date, i.name, t.qty, t.rate, t.amount, t.created_at
           FROM kiryana_transactions t LEFT JOIN kiryana_items i ON i.id = t.item_id
           WHERE t.party_id = ? AND t.txn_type = ? AND t.mode = 'Credit'""",
        (party_id, txn_type),
    )
    entries = [{"kind": "transaction", "id": r[0], "date": r[1], "type": txn_label, "detail": r[2],
                "qty": r[3], "rate": r[4], "debit": r[5], "credit": 0, "sort": r[6]}
               for r in cur.fetchall()]

    cur.execute(
        """SELECT t.id, t.date, i.name, t.qty, t.rate, t.amount, t.created_at
           FROM kiryana_transactions t LEFT JOIN kiryana_items i ON i.id = t.item_id
           WHERE t.party_id = ? AND t.txn_type = ? AND t.mode = 'Credit'""",
        (party_id, return_type),
    )
    entries += [{"kind": "return", "id": r[0], "date": r[1], "type": return_label, "detail": r[2],
                 "qty": r[3], "rate": r[4], "debit": 0, "credit": r[5], "sort": r[6]}
                for r in cur.fetchall()]

    cur.execute("SELECT id, date, description, amount, created_at FROM kiryana_payments WHERE party_id = ?", (party_id,))
    label = "Payment Received" if is_customer else "Payment Made"
    entries += [{"kind": "payment", "id": r[0], "date": r[1], "type": label, "detail": r[2] or "",
                 "qty": None, "rate": None, "debit": 0, "credit": r[3], "sort": r[4]}
                for r in cur.fetchall()]
    conn.close()

    entries.sort(key=lambda e: (e["date"], e["sort"]))
    running = party["opening_balance"]
    for e in entries:
        running += e["debit"] - e["credit"]
        e["balance"] = running
    return {"party": party, "entries": entries, "closing_balance": running}


def kiryana_party_balance(party_id):
    ledger = kiryana_party_ledger(party_id)
    return ledger["closing_balance"] if ledger else 0


def kiryana_record_payment(date_, party_id, amount, description=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO kiryana_payments (date, party_id, amount, description, created_at) VALUES (?,?,?,?,?)",
            (date_, party_id, amount, description, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def kiryana_get_payment(payment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, party_id, amount, description FROM kiryana_payments WHERE id = ?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "date": row[1], "party_id": row[2], "amount": row[3], "description": row[4]}


def kiryana_update_payment(payment_id, date_, amount, description=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE kiryana_payments SET date = ?, amount = ?, description = ? WHERE id = ?",
                    (date_, amount, description, payment_id))
        conn.commit()
    finally:
        conn.close()


def kiryana_delete_payment(payment_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kiryana_payments WHERE id = ?", (payment_id,))
        conn.commit()
    finally:
        conn.close()


def kiryana_get_transaction(txn_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no FROM kiryana_transactions WHERE id = ?",
        (txn_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "date": row[1], "txn_type": row[2], "party_id": row[3], "item_id": row[4],
            "qty": row[5], "rate": row[6], "amount": row[7], "mode": row[8], "description": row[9],
            "invoice_no": row[10]}


# txn types that ADD to stock when recorded (a Purchase brings stock in;
# a Sale Return brings it back) - everything else (Sale, Purchase Return)
# removes stock. Used to get the sign right when editing/deleting any of
# the four transaction types generically.
_STOCK_INCREASING_TXN_TYPES = ("PURCHASE", "SALE_RETURN")


def kiryana_update_transaction(txn_id, date_, qty, rate, description=""):
    """Corrects date/qty/rate/description on an existing Sale, Purchase,
    or Return row (item and party stay the same - editing which
    item/party a past entry belongs to isn't supported, just fixing a
    mistyped number). Adjusts stock by the qty delta so it stays
    accurate either way."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT txn_type, item_id, qty FROM kiryana_transactions WHERE id = ?", (txn_id,))
        row = cur.fetchone()
        if not row:
            return
        txn_type, item_id, old_qty = row
        amount = qty * rate
        cur.execute("UPDATE kiryana_transactions SET date = ?, qty = ?, rate = ?, amount = ?, description = ? WHERE id = ?",
                    (date_, qty, rate, amount, description, txn_id))
        qty_delta = qty - old_qty
        stock_delta = qty_delta if txn_type in _STOCK_INCREASING_TXN_TYPES else -qty_delta
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty + ? WHERE id = ?", (stock_delta, item_id))
        conn.commit()
    finally:
        conn.close()


def kiryana_delete_transaction(txn_id):
    """Removes a Sale/Purchase/Return entry and reverses its effect on stock."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT txn_type, item_id, qty FROM kiryana_transactions WHERE id = ?", (txn_id,))
        row = cur.fetchone()
        if not row:
            return
        txn_type, item_id, qty = row
        stock_delta = -qty if txn_type in _STOCK_INCREASING_TXN_TYPES else qty
        cur.execute("UPDATE kiryana_items SET stock_qty = stock_qty + ? WHERE id = ?", (stock_delta, item_id))
        cur.execute("DELETE FROM kiryana_transactions WHERE id = ?", (txn_id,))
        conn.commit()
    finally:
        conn.close()


def kiryana_cash_book():
    """Every cash-affecting event across sales/purchases/returns/payments,
    oldest first, with a running balance. Cash-mode sales, payments
    received from customers, and Cash-mode purchase returns (supplier
    refunding us) are inflows; Cash-mode purchases, supplier payments,
    Cash-mode sale returns (refunding a customer), and expenses are
    outflows. Credit-mode entries don't move cash until a payment is
    recorded against them."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.date, t.txn_type, t.amount, i.name, p.name, t.created_at
           FROM kiryana_transactions t
           LEFT JOIN kiryana_items i ON i.id = t.item_id
           LEFT JOIN kiryana_parties p ON p.id = t.party_id
           WHERE t.mode = 'Cash'"""
    )
    events = []
    for date_, txn_type, amount, item_name, party_name, created_at in cur.fetchall():
        if txn_type == "SALE":
            events.append({"date": date_, "description": f"Sale — {item_name} to {party_name or 'Walk-in'}",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})
        elif txn_type == "PURCHASE":
            events.append({"date": date_, "description": f"Purchase — {item_name} from {party_name or 'supplier'}",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        elif txn_type == "SALE_RETURN":
            events.append({"date": date_, "description": f"Sale Return — {item_name} from {party_name or 'Walk-in'} (refunded)",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        elif txn_type == "PURCHASE_RETURN":
            events.append({"date": date_, "description": f"Purchase Return — {item_name} to {party_name or 'supplier'} (refunded)",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})

    cur.execute(
        """SELECT pay.date, pay.amount, pay.description, pty.name, pty.party_type, pay.created_at
           FROM kiryana_payments pay LEFT JOIN kiryana_parties pty ON pty.id = pay.party_id"""
    )
    for date_, amount, description, party_name, party_type, created_at in cur.fetchall():
        extra = f" — {description}" if description else ""
        if party_type == "Supplier":
            events.append({"date": date_, "description": f"Payment made to {party_name}{extra}",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        else:
            events.append({"date": date_, "description": f"Payment received from {party_name}{extra}",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})

    cur.execute("SELECT date, category, description, amount, created_at FROM kiryana_expenses")
    for date_, category, description, amount, created_at in cur.fetchall():
        label = f"Expense — {category or 'General'}" + (f": {description}" if description else "")
        events.append({"date": date_, "description": label, "in_amount": 0, "out_amount": amount, "sort": created_at})
    conn.close()

    events.sort(key=lambda e: (e["date"], e["sort"]))
    running = 0
    for e in events:
        running += e["in_amount"] - e["out_amount"]
        e["balance"] = running
    return events


def kiryana_stock_summary():
    """Total stock quantity and total stock value (qty * purchase rate)
    across every item, plus the per-item breakdown behind those totals."""
    items = kiryana_list_items()
    breakdown = [{"name": i["name"], "unit": i["unit"], "stock_qty": i["stock_qty"],
                  "value": i["stock_qty"] * (i["purchase_rate"] or 0)} for i in items]
    return {"total_qty": sum(i["stock_qty"] for i in items),
            "total_value": sum(b["value"] for b in breakdown),
            "breakdown": breakdown}


def kiryana_low_stock_summary():
    """Items at or below their own reorder level - only items with a
    reorder_level actually set (> 0) are considered, since 0 means "no
    alert configured" for that item."""
    items = kiryana_list_items()
    breakdown = [{"id": i["id"], "name": i["name"], "unit": i["unit"], "stock_qty": i["stock_qty"],
                  "reorder_level": i["reorder_level"]}
                 for i in items if i["reorder_level"] > 0 and i["stock_qty"] <= i["reorder_level"]]
    breakdown.sort(key=lambda b: b["stock_qty"])
    return {"count": len(breakdown), "breakdown": breakdown}


def kiryana_expiring_batches(days=30):
    """Purchase lines with an expiry_date within the next N days (or
    already expired), soonest first - each is one batch of stock bought
    on one Purchase entry. Informational: doesn't know how much of that
    specific batch has since been sold, since stock isn't tracked by
    batch - just a checklist of what to go physically inspect."""
    conn = get_connection()
    cur = conn.cursor()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    cur.execute(
        """SELECT t.id, t.date, t.qty, i.name, i.unit, t.expiry_date
           FROM kiryana_transactions t LEFT JOIN kiryana_items i ON i.id = t.item_id
           WHERE t.txn_type = 'PURCHASE' AND t.expiry_date IS NOT NULL AND t.expiry_date <= ?
           ORDER BY t.expiry_date ASC""",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()
    today_iso = date.today().isoformat()
    breakdown = []
    for txn_id, purchase_date, qty, item_name, unit, expiry_date in rows:
        breakdown.append({"id": txn_id, "purchase_date": purchase_date, "qty": qty, "item": item_name,
                           "unit": unit, "expiry_date": expiry_date, "expired": expiry_date < today_iso})
    return {"count": len(breakdown), "breakdown": breakdown}


def kiryana_balance_summary(party_type):
    """Total outstanding balance across every party of one type (positive
    balances only - a party who's overpaid isn't 'owed' anything), plus
    the per-party breakdown behind that total. Customer balances are
    receivable (they owe the business); Supplier balances are payable
    (the business owes them)."""
    parties = kiryana_list_parties(party_type)
    breakdown = []
    total = 0
    for p in parties:
        balance = kiryana_party_balance(p["id"])
        if balance > 0:
            breakdown.append({"id": p["id"], "name": p["name"], "balance": balance})
            total += balance
    breakdown.sort(key=lambda b: -b["balance"])
    return {"total": total, "breakdown": breakdown}


def kiryana_total_sales(date_from=None, date_to=None):
    """Net sales (Sale amount minus Sale Return amount) - returns reduce
    revenue for Net Profit purposes, standard accounting treatment."""
    conn = get_connection()
    cur = conn.cursor()
    net_expr = "SUM(CASE WHEN txn_type = 'SALE' THEN amount ELSE -amount END)"
    if date_from and date_to:
        cur.execute(f"SELECT COALESCE({net_expr},0) FROM kiryana_transactions "
                    f"WHERE txn_type IN ('SALE','SALE_RETURN') AND date BETWEEN ? AND ?", (date_from, date_to))
    else:
        cur.execute(f"SELECT COALESCE({net_expr},0) FROM kiryana_transactions WHERE txn_type IN ('SALE','SALE_RETURN')")
    total = cur.fetchone()[0]
    conn.close()
    return total


def kiryana_add_expense(date_, category, description, amount):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO kiryana_expenses (date, category, description, amount, created_at) VALUES (?,?,?,?,?)",
            (date_, category, description, amount, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def kiryana_list_expenses(limit=200):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, category, description, amount FROM kiryana_expenses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "category": r[2], "description": r[3], "amount": r[4]} for r in rows]


def kiryana_get_expense(expense_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, date, category, description, amount FROM kiryana_expenses WHERE id = ?", (expense_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "date": row[1], "category": row[2], "description": row[3], "amount": row[4]}
    finally:
        conn.close()


def kiryana_update_expense(expense_id, date_, category, description, amount):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE kiryana_expenses SET date = ?, category = ?, description = ?, amount = ? WHERE id = ?",
                    (date_, category, description, amount, expense_id))
        conn.commit()
    finally:
        conn.close()


def kiryana_delete_expense(expense_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kiryana_expenses WHERE id = ?", (expense_id,))
        conn.commit()
    finally:
        conn.close()


def kiryana_total_expenses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM kiryana_expenses")
    total = cur.fetchone()[0]
    conn.close()
    return total



# =======================================================================
# HARDWARE MODULE — a separate, simpler inventory/sales/purchases/cash
# engine for hardware-store style businesses selected from the post-login
# business-type picker. Deliberately independent of the parties/quality/
# transactions tables above (no D.O. numbers, brokers, or weighted-average
# purchase rate) since a Hardware store's needs are much simpler than the
# yarn-trading workflow those tables were built for - it only shares the
# tenant database file, not the schema (and is a fully separate dataset
# from the Kiryana module too, even though the feature set is identical -
# a company running both keeps two completely independent books). Both
# Sales and Purchases can be Cash or Credit; credit balances (receivable
# from customers, payable to suppliers) are settled via hardware_payments
# and viewable on the Ledger page for either party type.
# =======================================================================
def _init_hardware_schema(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT,
            purchase_rate REAL DEFAULT 0,
            sale_rate REAL DEFAULT 0,
            stock_qty REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    # --- migration: barcode, added after hardware_items already shipped ---
    cur.execute("PRAGMA table_info(hardware_items)")
    existing_item_cols = {row[1] for row in cur.fetchall()}
    if "barcode" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN barcode TEXT")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_items_barcode ON hardware_items(barcode)")
    # --- migration: reorder_level (low-stock alerts), category, and bulk
    # purchase-unit conversion (e.g. buy by the carton, sell by the piece) ---
    if "reorder_level" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN reorder_level REAL DEFAULT 0")
        conn.commit()
    if "category" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN category TEXT")
        conn.commit()
    if "purchase_unit" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN purchase_unit TEXT")
        conn.commit()
    if "conversion_factor" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN conversion_factor REAL DEFAULT 1")
        conn.commit()
    # --- migration: item variants (e.g. "Screws" with 1in/2in/3in
    # variants) - a variant is a fully independent, fully stock-tracked
    # item that's also tagged with which parent item it belongs to, purely
    # for grouped display/picking. No change to any transaction logic. ---
    if "parent_item_id" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN parent_item_id INTEGER REFERENCES hardware_items(id)")
        conn.commit()
    if "variant_name" not in existing_item_cols:
        cur.execute("ALTER TABLE hardware_items ADD COLUMN variant_name TEXT")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_items_parent ON hardware_items(parent_item_id)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            party_type TEXT NOT NULL DEFAULT 'Customer',
            opening_balance REAL DEFAULT 0,
            created_at TEXT
        )
    """)
    # --- migration: credit_limit (Customers only - warns rather than
    # blocks when a credit sale would push them over it) and gst_number
    # (for tax invoicing) ---
    cur.execute("PRAGMA table_info(hardware_parties)")
    existing_party_cols = {row[1] for row in cur.fetchall()}
    if "credit_limit" not in existing_party_cols:
        cur.execute("ALTER TABLE hardware_parties ADD COLUMN credit_limit REAL DEFAULT 0")
        conn.commit()
    if "gst_number" not in existing_party_cols:
        cur.execute("ALTER TABLE hardware_parties ADD COLUMN gst_number TEXT")
        conn.commit()
    # --- customer-specific negotiated pricing: an override on top of an
    # item's normal Sale Rate, only for the customers who have one ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_customer_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            rate REAL NOT NULL,
            created_at TEXT,
            UNIQUE(party_id, item_id),
            FOREIGN KEY (party_id) REFERENCES hardware_parties (id),
            FOREIGN KEY (item_id) REFERENCES hardware_items (id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            party_id INTEGER,
            item_id INTEGER NOT NULL,
            qty REAL NOT NULL,
            rate REAL NOT NULL,
            amount REAL NOT NULL,
            mode TEXT NOT NULL DEFAULT 'Cash',
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES hardware_parties (id),
            FOREIGN KEY (item_id) REFERENCES hardware_items (id)
        )
    """)
    # --- migration: invoice_no, added so one Sale/Purchase can cover
    # multiple line items (each still its own row, sharing one number) ---
    cur.execute("PRAGMA table_info(hardware_transactions)")
    existing_txn_cols = {row[1] for row in cur.fetchall()}
    if "invoice_no" not in existing_txn_cols:
        cur.execute("ALTER TABLE hardware_transactions ADD COLUMN invoice_no INTEGER")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_txn_invoice ON hardware_transactions(txn_type, invoice_no)")
    # --- migration: expiry_date, set on a PURCHASE line to track when
    # that batch of stock expires (informational - not consumed FIFO
    # against sales, just surfaced on an "Expiring Soon" dashboard card) ---
    if "expiry_date" not in existing_txn_cols:
        cur.execute("ALTER TABLE hardware_transactions ADD COLUMN expiry_date TEXT")
        conn.commit()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_txn_expiry ON hardware_transactions(expiry_date)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            party_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY (party_id) REFERENCES hardware_parties (id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT,
            description TEXT,
            amount REAL NOT NULL,
            created_at TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_txn_party ON hardware_transactions(party_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_txn_item ON hardware_transactions(item_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hardware_payments_party ON hardware_payments(party_id)")
    conn.commit()


_HW_ITEM_COLUMNS = ("id, name, unit, purchase_rate, sale_rate, stock_qty, barcode, "
                 "reorder_level, category, purchase_unit, conversion_factor, parent_item_id, variant_name")


def _hw_item_row_to_dict(row):
    return {"id": row[0], "name": row[1], "unit": row[2], "purchase_rate": row[3], "sale_rate": row[4],
            "stock_qty": row[5], "barcode": row[6], "reorder_level": row[7] or 0, "category": row[8],
            "purchase_unit": row[9], "conversion_factor": row[10] or 1, "parent_item_id": row[11],
            "variant_name": row[12]}


def hardware_list_items():
    """Every item, each carrying a display_name that folds in the variant
    name (e.g. "Screws — 1 inch") when it has a parent, so callers that
    just want something to show in a dropdown/table don't need to know
    about the variant relationship at all."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""SELECT {', '.join('i.' + c.strip() for c in _HW_ITEM_COLUMNS.split(','))}, p.name
                    FROM hardware_items i LEFT JOIN hardware_items p ON p.id = i.parent_item_id
                    ORDER BY COALESCE(p.name, i.name), i.parent_item_id IS NULL DESC, i.name""")
    rows = cur.fetchall()
    conn.close()
    items = []
    for r in rows:
        item = _hw_item_row_to_dict(r[:-1])
        parent_name = r[-1]
        item["parent_name"] = parent_name
        item["display_name"] = f"{parent_name} — {item['variant_name']}" if parent_name and item["variant_name"] else item["name"]
        items.append(item)
    return items


def hardware_list_parent_items():
    """Items that can act as a parent for variants - i.e. everything
    that isn't itself already a variant (no nested variants)."""
    return [i for i in hardware_list_items() if not i["parent_item_id"]]


def hardware_list_categories():
    """Distinct categories already in use, for the Category field's
    autocomplete suggestions - not a fixed list, since what makes sense
    varies shop to shop."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM hardware_items WHERE category IS NOT NULL AND category != '' ORDER BY category")
    cats = [r[0] for r in cur.fetchall()]
    conn.close()
    return cats


def hardware_add_item(name, unit, purchase_rate, sale_rate, opening_qty, barcode=None,
                      reorder_level=0, category=None, purchase_unit=None, conversion_factor=1,
                      parent_item_id=None, variant_name=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_items (name, unit, purchase_rate, sale_rate, stock_qty, barcode,
               reorder_level, category, purchase_unit, conversion_factor, parent_item_id, variant_name, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, unit, purchase_rate, sale_rate, opening_qty, barcode or None,
             reorder_level or 0, category or None, purchase_unit or None, conversion_factor or 1,
             parent_item_id or None, variant_name or None, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_get_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_HW_ITEM_COLUMNS} FROM hardware_items WHERE id = ?", (item_id,))
        row = cur.fetchone()
        return _hw_item_row_to_dict(row) if row else None
    finally:
        conn.close()


def hardware_get_item_by_barcode(barcode):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {_HW_ITEM_COLUMNS} FROM hardware_items WHERE barcode = ?", (barcode,))
        row = cur.fetchone()
        return _hw_item_row_to_dict(row) if row else None
    finally:
        conn.close()


def hardware_update_item(item_id, name, unit, purchase_rate, sale_rate, stock_qty, barcode=None,
                         reorder_level=0, category=None, purchase_unit=None, conversion_factor=1,
                         parent_item_id=None, variant_name=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE hardware_items SET name = ?, unit = ?, purchase_rate = ?, sale_rate = ?, stock_qty = ?,
               barcode = ?, reorder_level = ?, category = ?, purchase_unit = ?, conversion_factor = ?,
               parent_item_id = ?, variant_name = ? WHERE id = ?""",
            (name, unit, purchase_rate, sale_rate, stock_qty, barcode or None,
             reorder_level or 0, category or None, purchase_unit or None, conversion_factor or 1,
             parent_item_id or None, variant_name or None, item_id),
        )
        conn.commit()
    finally:
        conn.close()


def hardware_item_has_transactions(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE item_id = ?", (item_id,))
        return cur.fetchone()[0] > 0
    finally:
        conn.close()


def hardware_delete_item(item_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM hardware_items WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()


_HW_PARTY_COLUMNS = "id, name, phone, party_type, opening_balance, credit_limit, gst_number"


def _hw_party_row_to_dict(row):
    return {"id": row[0], "name": row[1], "phone": row[2], "party_type": row[3], "opening_balance": row[4],
            "credit_limit": row[5] or 0, "gst_number": row[6]}


def hardware_list_parties(party_type=None):
    conn = get_connection()
    cur = conn.cursor()
    if party_type:
        cur.execute(f"SELECT {_HW_PARTY_COLUMNS} FROM hardware_parties WHERE party_type = ? ORDER BY name", (party_type,))
    else:
        cur.execute(f"SELECT {_HW_PARTY_COLUMNS} FROM hardware_parties ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [_hw_party_row_to_dict(r) for r in rows]


def hardware_add_party(name, phone, party_type, opening_balance=0, credit_limit=0, gst_number=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_parties (name, phone, party_type, opening_balance, credit_limit, gst_number, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (name, phone, party_type, opening_balance, credit_limit or 0, gst_number or None, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_update_party(party_id, name, phone, opening_balance, credit_limit=0, gst_number=None):
    """Party type isn't editable here - a Customer becoming a Supplier
    (or vice versa) would orphan their ledger history, so that's not
    supported; delete and re-add if it was set up wrong."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE hardware_parties SET name = ?, phone = ?, opening_balance = ?, credit_limit = ?, gst_number = ?
               WHERE id = ?""",
            (name, phone, opening_balance, credit_limit or 0, gst_number or None, party_id),
        )
        conn.commit()
    finally:
        conn.close()


def hardware_get_party(party_id, conn=None):
    own = conn is None
    conn = conn or get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {_HW_PARTY_COLUMNS} FROM hardware_parties WHERE id = ?", (party_id,))
    row = cur.fetchone()
    if own:
        conn.close()
    return _hw_party_row_to_dict(row) if row else None


def hardware_party_has_activity(party_id):
    """True if this party has any transactions, payments, or price
    overrides against them - used to block deletion, same guard pattern
    as items."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM hardware_transactions WHERE party_id = ?", (party_id,))
    has_txn = cur.fetchone()[0] > 0
    cur.execute("SELECT COUNT(*) FROM hardware_payments WHERE party_id = ?", (party_id,))
    has_pay = cur.fetchone()[0] > 0
    conn.close()
    return has_txn or has_pay


def hardware_delete_party(party_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM hardware_customer_prices WHERE party_id = ?", (party_id,))
        cur.execute("DELETE FROM hardware_parties WHERE id = ?", (party_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Hardware: customer-specific negotiated pricing - an override on top of
# an item's normal Sale Rate, only for the customers who have one set.
# ---------------------------------------------------------------------
def hardware_list_customer_prices(party_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT cp.id, cp.item_id, i.name, cp.rate FROM hardware_customer_prices cp
           LEFT JOIN hardware_items i ON i.id = cp.item_id WHERE cp.party_id = ? ORDER BY i.name""",
        (party_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "item_id": r[1], "item_name": r[2], "rate": r[3]} for r in rows]


def hardware_set_customer_price(party_id, item_id, rate):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_customer_prices (party_id, item_id, rate, created_at) VALUES (?,?,?,?)
               ON CONFLICT(party_id, item_id) DO UPDATE SET rate = excluded.rate""",
            (party_id, item_id, rate, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def hardware_delete_customer_price(price_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM hardware_customer_prices WHERE id = ?", (price_id,))
        conn.commit()
    finally:
        conn.close()


def hardware_all_customer_prices_map():
    """{"partyId_itemId": rate} for every override in one shot - embedded
    into the Sale form at page load so the JS can auto-fill the rate the
    instant both Customer and Item are picked, no round trip needed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT party_id, item_id, rate FROM hardware_customer_prices")
    rows = cur.fetchall()
    conn.close()
    return {f"{r[0]}_{r[1]}": r[2] for r in rows}


def hardware_get_next_invoice_no(txn_type):
    """One invoice number per Save click, shared by every line item in
    that sale/purchase (each line is still its own hardware_transactions
    row - see hardware_record_sale/hardware_record_purchase). Quotations
    are numbered against BOTH 'QUOTATION' and 'QUOTATION_CONVERTED' rows,
    since converting one changes its txn_type but must keep its number -
    numbering against 'QUOTATION' alone would let a later quotation reuse
    a number an earlier, already-converted one still holds."""
    types = ("QUOTATION", "QUOTATION_CONVERTED") if txn_type in ("QUOTATION", "QUOTATION_CONVERTED") else (txn_type,)
    conn = get_connection()
    try:
        cur = conn.cursor()
        placeholders = ",".join("?" * len(types))
        cur.execute(f"SELECT MAX(invoice_no) FROM hardware_transactions WHERE txn_type IN ({placeholders})", types)
        row = cur.fetchone()
        return (row[0] or 0) + 1
    finally:
        conn.close()


_HW_INVOICE_PREFIXES = {"SALE": "SALE", "PURCHASE": "PUR", "SALE_RETURN": "SR", "PURCHASE_RETURN": "PR",
                         "QUOTATION": "QT", "QUOTATION_CONVERTED": "QT"}


def hardware_format_invoice_no(txn_type, invoice_no):
    if not invoice_no:
        return "—"
    return f"{_HW_INVOICE_PREFIXES.get(txn_type, txn_type)}-{invoice_no:06d}"


def hardware_record_sale(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "SALE", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty - ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Hardware: Quotations/Estimates - a non-binding price quote for a
# customer that touches neither stock nor the ledger until it's actually
# converted into a real Sale. Reuses hardware_transactions with its own
# txn_type ('QUOTATION' while open, 'QUOTATION_CONVERTED' once turned
# into a sale) rather than a separate table - every existing generic
# helper (list/format/edit/delete/print) already works on any txn_type
# without modification, and neither the party ledger nor the cash book
# ever look for these two types, so a quotation is automatically inert
# everywhere that matters until it's converted.
# ---------------------------------------------------------------------
def hardware_record_quotation_line(date_, party_id, item_id, qty, rate, description="", invoice_no=None):
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "QUOTATION", party_id, item_id, qty, rate, amount, "N/A", description, invoice_no, now_iso()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_convert_quotation(invoice_no, sale_date, mode="Cash"):
    """Turns every open line of one quotation into a real Sale (with its
    own new invoice number, stock deducted, ledger updated as normal),
    then marks the quotation's lines as converted so they drop off the
    open-quotations list. Returns the new Sale's invoice number."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, party_id, item_id, qty, rate, description FROM hardware_transactions "
        "WHERE txn_type = 'QUOTATION' AND invoice_no = ?",
        (invoice_no,),
    )
    lines = cur.fetchall()
    conn.close()
    if not lines:
        return None

    sale_invoice_no = hardware_get_next_invoice_no("SALE")
    for _, party_id, item_id, qty, rate, description in lines:
        hardware_record_sale(sale_date, party_id, item_id, qty, rate, mode, description, sale_invoice_no)

    conn2 = get_connection()
    cur2 = conn2.cursor()
    cur2.execute("UPDATE hardware_transactions SET txn_type = 'QUOTATION_CONVERTED' WHERE txn_type = 'QUOTATION' AND invoice_no = ?",
                 (invoice_no,))
    conn2.commit()
    conn2.close()
    return sale_invoice_no


def hardware_record_purchase(date_, party_id, item_id, qty, rate, mode="Cash", description="", sale_rate=None,
                             invoice_no=None, expiry_date=None):
    """Records a Purchase, adds the qty to stock, and fixes the item's
    Purchase Rate to the rate just paid (same field shown on the
    Inventory page - a Purchase entry IS how you'd know the current
    buying price, so it should always reflect the latest one). When
    sale_rate is given, fixes the item's Sale Rate the same way -
    restocking and re-pricing happen in one step instead of needing a
    separate trip to Inventory. expiry_date (optional) marks this
    specific batch of stock for the Expiring Soon dashboard card - it's
    informational only, not consumed FIFO against later sales."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, expiry_date, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "PURCHASE", party_id, item_id, qty, rate, amount, mode, description, invoice_no,
             expiry_date or None, now_iso()),
        )
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty + ?, purchase_rate = ? WHERE id = ?",
                    (qty, rate, item_id))
        if sale_rate is not None:
            cur.execute("UPDATE hardware_items SET sale_rate = ? WHERE id = ?", (sale_rate, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_record_sale_return(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    """A customer returning something they bought - the mirror image of
    hardware_record_sale: stock comes back instead of leaving, and on
    Credit mode it reduces (rather than adds to) what the customer owes,
    via hardware_party_ledger treating SALE_RETURN as a credit-side entry."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "SALE_RETURN", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty + ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_record_purchase_return(date_, party_id, item_id, qty, rate, mode, description="", invoice_no=None):
    """Sending something back to a supplier - the mirror image of
    hardware_record_purchase: stock leaves instead of arriving, and on
    Credit mode it reduces what's owed to that supplier."""
    amount = qty * rate
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_transactions (date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (date_, "PURCHASE_RETURN", party_id, item_id, qty, rate, amount, mode, description, invoice_no, now_iso()),
        )
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty - ? WHERE id = ?", (qty, item_id))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def hardware_list_transactions(txn_type, limit=50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.id, t.date, t.party_id, p.name, t.item_id, i.name, t.qty, t.rate, t.amount, t.mode, t.description, t.invoice_no
           FROM hardware_transactions t
           LEFT JOIN hardware_parties p ON p.id = t.party_id
           LEFT JOIN hardware_items i ON i.id = t.item_id
           WHERE t.txn_type = ?
           ORDER BY t.id DESC LIMIT ?""",
        (txn_type, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "party_id": r[2], "party": r[3] or "Walk-in", "item_id": r[4],
             "item": r[5], "qty": r[6], "rate": r[7], "amount": r[8], "mode": r[9], "description": r[10],
             "invoice_no": r[11], "invoice": hardware_format_invoice_no(txn_type, r[11])}
            for r in rows]


def hardware_list_invoices(txn_type, limit=50):
    """Recent Sale/Purchase entries grouped by invoice - one row per Save
    click, even though a multi-item sale/purchase is still one
    hardware_transactions row per line underneath. Rows saved before
    invoice_no existed (or with no lines sharing a number for some other
    reason) each just become their own single-line 'invoice' here."""
    txns = hardware_list_transactions(txn_type, limit=max(limit * 6, 100))
    groups, order = {}, []
    for t in txns:
        key = t["invoice_no"] if t["invoice_no"] is not None else f"single-{t['id']}"
        if key not in groups:
            groups[key] = {"invoice_no": t["invoice_no"], "invoice": t["invoice"], "date": t["date"],
                           "party": t["party"], "party_id": t["party_id"], "mode": t["mode"],
                           "description": t["description"], "total_amount": 0.0, "lines": []}
            order.append(key)
        groups[key]["total_amount"] += t["amount"]
        groups[key]["lines"].append(t)
    return [groups[k] for k in order[:limit]]


def hardware_get_bill(txn_type, anchor_txn_id):
    """Every line item belonging to the same bill as anchor_txn_id - i.e.
    everything sharing its invoice_no, or just that one row if it predates
    invoice_no (or was never grouped). Used for the per-bill Print button
    on the Recent Sales/Purchases list, which only needs to know one line
    item's id to reprint the whole thing."""
    anchor = hardware_get_transaction(anchor_txn_id)
    if not anchor or anchor["txn_type"] != txn_type:
        return None
    conn = get_connection()
    cur = conn.cursor()
    if anchor["invoice_no"] is not None:
        cur.execute(
            """SELECT t.id, t.date, t.qty, t.rate, t.amount, i.name
               FROM hardware_transactions t LEFT JOIN hardware_items i ON i.id = t.item_id
               WHERE t.txn_type = ? AND t.invoice_no = ? ORDER BY t.id""",
            (txn_type, anchor["invoice_no"]),
        )
        rows = cur.fetchall()
    else:
        cur.execute(
            """SELECT t.id, t.date, t.qty, t.rate, t.amount, i.name
               FROM hardware_transactions t LEFT JOIN hardware_items i ON i.id = t.item_id
               WHERE t.id = ?""",
            (anchor_txn_id,),
        )
        rows = cur.fetchall()
    conn.close()
    lines = [{"id": r[0], "date": r[1], "qty": r[2], "rate": r[3], "amount": r[4], "item": r[5]} for r in rows]
    party = hardware_get_party(anchor["party_id"]) if anchor["party_id"] else None
    return {
        "invoice": hardware_format_invoice_no(txn_type, anchor["invoice_no"]),
        "date": anchor["date"], "mode": anchor["mode"], "description": anchor["description"],
        "party": party, "lines": lines, "total": sum(l["amount"] for l in lines),
    }


def hardware_party_ledger(party_id):
    """Chronological T-account statement for one party (Customer or
    Supplier): opening balance, every credit sale/purchase on their
    account (adds to what they owe / what's owed to them) as a debit,
    every payment AND every credit-mode return (reduces it) as a credit.
    Works for either party type - a Customer's debits come from credit
    Sales and credits from Payments Received + Sale Returns; a Supplier's
    debits come from credit Purchases and credits from Payments Made +
    Purchase Returns - but the shape returned is identical so one
    template can render both."""
    conn = get_connection()
    cur = conn.cursor()
    party = hardware_get_party(party_id, conn)
    if not party:
        conn.close()
        return None

    is_customer = party["party_type"] == "Customer"
    txn_type = "SALE" if is_customer else "PURCHASE"
    return_type = "SALE_RETURN" if is_customer else "PURCHASE_RETURN"
    txn_label = "Sale (Credit)" if is_customer else "Purchase (Credit)"
    return_label = "Sale Return" if is_customer else "Purchase Return"

    cur.execute(
        """SELECT t.id, t.date, i.name, t.qty, t.rate, t.amount, t.created_at
           FROM hardware_transactions t LEFT JOIN hardware_items i ON i.id = t.item_id
           WHERE t.party_id = ? AND t.txn_type = ? AND t.mode = 'Credit'""",
        (party_id, txn_type),
    )
    entries = [{"kind": "transaction", "id": r[0], "date": r[1], "type": txn_label, "detail": r[2],
                "qty": r[3], "rate": r[4], "debit": r[5], "credit": 0, "sort": r[6]}
               for r in cur.fetchall()]

    cur.execute(
        """SELECT t.id, t.date, i.name, t.qty, t.rate, t.amount, t.created_at
           FROM hardware_transactions t LEFT JOIN hardware_items i ON i.id = t.item_id
           WHERE t.party_id = ? AND t.txn_type = ? AND t.mode = 'Credit'""",
        (party_id, return_type),
    )
    entries += [{"kind": "return", "id": r[0], "date": r[1], "type": return_label, "detail": r[2],
                 "qty": r[3], "rate": r[4], "debit": 0, "credit": r[5], "sort": r[6]}
                for r in cur.fetchall()]

    cur.execute("SELECT id, date, description, amount, created_at FROM hardware_payments WHERE party_id = ?", (party_id,))
    label = "Payment Received" if is_customer else "Payment Made"
    entries += [{"kind": "payment", "id": r[0], "date": r[1], "type": label, "detail": r[2] or "",
                 "qty": None, "rate": None, "debit": 0, "credit": r[3], "sort": r[4]}
                for r in cur.fetchall()]
    conn.close()

    entries.sort(key=lambda e: (e["date"], e["sort"]))
    running = party["opening_balance"]
    for e in entries:
        running += e["debit"] - e["credit"]
        e["balance"] = running
    return {"party": party, "entries": entries, "closing_balance": running}


def hardware_party_balance(party_id):
    ledger = hardware_party_ledger(party_id)
    return ledger["closing_balance"] if ledger else 0


def hardware_record_payment(date_, party_id, amount, description=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO hardware_payments (date, party_id, amount, description, created_at) VALUES (?,?,?,?,?)",
            (date_, party_id, amount, description, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def hardware_get_payment(payment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, party_id, amount, description FROM hardware_payments WHERE id = ?", (payment_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "date": row[1], "party_id": row[2], "amount": row[3], "description": row[4]}


def hardware_update_payment(payment_id, date_, amount, description=""):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE hardware_payments SET date = ?, amount = ?, description = ? WHERE id = ?",
                    (date_, amount, description, payment_id))
        conn.commit()
    finally:
        conn.close()


def hardware_delete_payment(payment_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM hardware_payments WHERE id = ?", (payment_id,))
        conn.commit()
    finally:
        conn.close()


def hardware_get_transaction(txn_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, txn_type, party_id, item_id, qty, rate, amount, mode, description, invoice_no FROM hardware_transactions WHERE id = ?",
        (txn_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "date": row[1], "txn_type": row[2], "party_id": row[3], "item_id": row[4],
            "qty": row[5], "rate": row[6], "amount": row[7], "mode": row[8], "description": row[9],
            "invoice_no": row[10]}


# txn types that ADD to stock when recorded (a Purchase brings stock in;
# a Sale Return brings it back) - everything else (Sale, Purchase Return)
# removes stock. Used to get the sign right when editing/deleting any of
# the four transaction types generically.
_HW_STOCK_INCREASING_TXN_TYPES = ("PURCHASE", "SALE_RETURN")


def hardware_update_transaction(txn_id, date_, qty, rate, description=""):
    """Corrects date/qty/rate/description on an existing Sale, Purchase,
    or Return row (item and party stay the same - editing which
    item/party a past entry belongs to isn't supported, just fixing a
    mistyped number). Adjusts stock by the qty delta so it stays
    accurate either way."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT txn_type, item_id, qty FROM hardware_transactions WHERE id = ?", (txn_id,))
        row = cur.fetchone()
        if not row:
            return
        txn_type, item_id, old_qty = row
        amount = qty * rate
        cur.execute("UPDATE hardware_transactions SET date = ?, qty = ?, rate = ?, amount = ?, description = ? WHERE id = ?",
                    (date_, qty, rate, amount, description, txn_id))
        qty_delta = qty - old_qty
        stock_delta = qty_delta if txn_type in _HW_STOCK_INCREASING_TXN_TYPES else -qty_delta
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty + ? WHERE id = ?", (stock_delta, item_id))
        conn.commit()
    finally:
        conn.close()


def hardware_delete_transaction(txn_id):
    """Removes a Sale/Purchase/Return entry and reverses its effect on stock."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT txn_type, item_id, qty FROM hardware_transactions WHERE id = ?", (txn_id,))
        row = cur.fetchone()
        if not row:
            return
        txn_type, item_id, qty = row
        stock_delta = -qty if txn_type in _HW_STOCK_INCREASING_TXN_TYPES else qty
        cur.execute("UPDATE hardware_items SET stock_qty = stock_qty + ? WHERE id = ?", (stock_delta, item_id))
        cur.execute("DELETE FROM hardware_transactions WHERE id = ?", (txn_id,))
        conn.commit()
    finally:
        conn.close()


def hardware_cash_book():
    """Every cash-affecting event across sales/purchases/returns/payments,
    oldest first, with a running balance. Cash-mode sales, payments
    received from customers, and Cash-mode purchase returns (supplier
    refunding us) are inflows; Cash-mode purchases, supplier payments,
    Cash-mode sale returns (refunding a customer), and expenses are
    outflows. Credit-mode entries don't move cash until a payment is
    recorded against them."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT t.date, t.txn_type, t.amount, i.name, p.name, t.created_at
           FROM hardware_transactions t
           LEFT JOIN hardware_items i ON i.id = t.item_id
           LEFT JOIN hardware_parties p ON p.id = t.party_id
           WHERE t.mode = 'Cash'"""
    )
    events = []
    for date_, txn_type, amount, item_name, party_name, created_at in cur.fetchall():
        if txn_type == "SALE":
            events.append({"date": date_, "description": f"Sale — {item_name} to {party_name or 'Walk-in'}",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})
        elif txn_type == "PURCHASE":
            events.append({"date": date_, "description": f"Purchase — {item_name} from {party_name or 'supplier'}",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        elif txn_type == "SALE_RETURN":
            events.append({"date": date_, "description": f"Sale Return — {item_name} from {party_name or 'Walk-in'} (refunded)",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        elif txn_type == "PURCHASE_RETURN":
            events.append({"date": date_, "description": f"Purchase Return — {item_name} to {party_name or 'supplier'} (refunded)",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})

    cur.execute(
        """SELECT pay.date, pay.amount, pay.description, pty.name, pty.party_type, pay.created_at
           FROM hardware_payments pay LEFT JOIN hardware_parties pty ON pty.id = pay.party_id"""
    )
    for date_, amount, description, party_name, party_type, created_at in cur.fetchall():
        extra = f" — {description}" if description else ""
        if party_type == "Supplier":
            events.append({"date": date_, "description": f"Payment made to {party_name}{extra}",
                            "in_amount": 0, "out_amount": amount, "sort": created_at})
        else:
            events.append({"date": date_, "description": f"Payment received from {party_name}{extra}",
                            "in_amount": amount, "out_amount": 0, "sort": created_at})

    cur.execute("SELECT date, category, description, amount, created_at FROM hardware_expenses")
    for date_, category, description, amount, created_at in cur.fetchall():
        label = f"Expense — {category or 'General'}" + (f": {description}" if description else "")
        events.append({"date": date_, "description": label, "in_amount": 0, "out_amount": amount, "sort": created_at})
    conn.close()

    events.sort(key=lambda e: (e["date"], e["sort"]))
    running = 0
    for e in events:
        running += e["in_amount"] - e["out_amount"]
        e["balance"] = running
    return events


def hardware_stock_summary():
    """Total stock quantity and total stock value (qty * purchase rate)
    across every item, plus the per-item breakdown behind those totals."""
    items = hardware_list_items()
    breakdown = [{"name": i["name"], "unit": i["unit"], "stock_qty": i["stock_qty"],
                  "value": i["stock_qty"] * (i["purchase_rate"] or 0)} for i in items]
    return {"total_qty": sum(i["stock_qty"] for i in items),
            "total_value": sum(b["value"] for b in breakdown),
            "breakdown": breakdown}


def hardware_low_stock_summary():
    """Items at or below their own reorder level - only items with a
    reorder_level actually set (> 0) are considered, since 0 means "no
    alert configured" for that item. Each row also carries a suggested
    reorder quantity based on actual recent sales velocity (how much sold
    in the last 30 days), not just a static number - simplest useful
    heuristic: buy enough to cover what the last 30 days actually used,
    on top of getting back above the reorder level."""
    items = hardware_list_items()
    low_items = [i for i in items if i["reorder_level"] > 0 and i["stock_qty"] <= i["reorder_level"]]
    if not low_items:
        return {"count": 0, "breakdown": []}

    cutoff = (date.today() - timedelta(days=30)).isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT item_id, COALESCE(SUM(qty),0) FROM hardware_transactions "
        "WHERE txn_type = 'SALE' AND date >= ? GROUP BY item_id",
        (cutoff,),
    )
    recent_sales = dict(cur.fetchall())
    conn.close()

    breakdown = []
    for i in low_items:
        sold_30d = recent_sales.get(i["id"], 0)
        shortfall = max(0, i["reorder_level"] - i["stock_qty"])
        suggested_qty = round(shortfall + sold_30d, 2)
        breakdown.append({"id": i["id"], "name": i["name"], "unit": i["unit"], "stock_qty": i["stock_qty"],
                           "reorder_level": i["reorder_level"], "sold_30d": sold_30d, "suggested_qty": suggested_qty})
    breakdown.sort(key=lambda b: b["stock_qty"])
    return {"count": len(breakdown), "breakdown": breakdown}


def hardware_expiring_batches(days=30):
    """Purchase lines with an expiry_date within the next N days (or
    already expired), soonest first - each is one batch of stock bought
    on one Purchase entry. Informational: doesn't know how much of that
    specific batch has since been sold, since stock isn't tracked by
    batch - just a checklist of what to go physically inspect."""
    conn = get_connection()
    cur = conn.cursor()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    cur.execute(
        """SELECT t.id, t.date, t.qty, i.name, i.unit, t.expiry_date
           FROM hardware_transactions t LEFT JOIN hardware_items i ON i.id = t.item_id
           WHERE t.txn_type = 'PURCHASE' AND t.expiry_date IS NOT NULL AND t.expiry_date <= ?
           ORDER BY t.expiry_date ASC""",
        (cutoff,),
    )
    rows = cur.fetchall()
    conn.close()
    today_iso = date.today().isoformat()
    breakdown = []
    for txn_id, purchase_date, qty, item_name, unit, expiry_date in rows:
        breakdown.append({"id": txn_id, "purchase_date": purchase_date, "qty": qty, "item": item_name,
                           "unit": unit, "expiry_date": expiry_date, "expired": expiry_date < today_iso})
    return {"count": len(breakdown), "breakdown": breakdown}


def hardware_balance_summary(party_type):
    """Total outstanding balance across every party of one type (positive
    balances only - a party who's overpaid isn't 'owed' anything), plus
    the per-party breakdown behind that total. Customer balances are
    receivable (they owe the business); Supplier balances are payable
    (the business owes them)."""
    parties = hardware_list_parties(party_type)
    breakdown = []
    total = 0
    for p in parties:
        balance = hardware_party_balance(p["id"])
        if balance > 0:
            breakdown.append({"id": p["id"], "name": p["name"], "balance": balance})
            total += balance
    breakdown.sort(key=lambda b: -b["balance"])
    return {"total": total, "breakdown": breakdown}


def hardware_total_sales(date_from=None, date_to=None):
    """Net sales (Sale amount minus Sale Return amount) - returns reduce
    revenue for Net Profit purposes, standard accounting treatment."""
    conn = get_connection()
    cur = conn.cursor()
    net_expr = "SUM(CASE WHEN txn_type = 'SALE' THEN amount ELSE -amount END)"
    if date_from and date_to:
        cur.execute(f"SELECT COALESCE({net_expr},0) FROM hardware_transactions "
                    f"WHERE txn_type IN ('SALE','SALE_RETURN') AND date BETWEEN ? AND ?", (date_from, date_to))
    else:
        cur.execute(f"SELECT COALESCE({net_expr},0) FROM hardware_transactions WHERE txn_type IN ('SALE','SALE_RETURN')")
    total = cur.fetchone()[0]
    conn.close()
    return total


def hardware_add_expense(date_, category, description, amount):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO hardware_expenses (date, category, description, amount, created_at) VALUES (?,?,?,?,?)",
            (date_, category, description, amount, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def hardware_list_expenses(limit=200):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, category, description, amount FROM hardware_expenses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "date": r[1], "category": r[2], "description": r[3], "amount": r[4]} for r in rows]


def hardware_get_expense(expense_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, date, category, description, amount FROM hardware_expenses WHERE id = ?", (expense_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "date": row[1], "category": row[2], "description": row[3], "amount": row[4]}
    finally:
        conn.close()


def hardware_update_expense(expense_id, date_, category, description, amount):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE hardware_expenses SET date = ?, category = ?, description = ?, amount = ? WHERE id = ?",
                    (date_, category, description, amount, expense_id))
        conn.commit()
    finally:
        conn.close()


def hardware_delete_expense(expense_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM hardware_expenses WHERE id = ?", (expense_id,))
        conn.commit()
    finally:
        conn.close()


def hardware_total_expenses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM hardware_expenses")
    total = cur.fetchone()[0]
    conn.close()
    return total

if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DB_PATH}")
