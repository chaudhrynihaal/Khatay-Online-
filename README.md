# ULTRA ERP — Web Edition

A multi-company (multi-tenant) web version of ULTRA ERP. Each company
gets its own completely isolated database. You run one platform admin
panel to create companies and manage their subscriptions; each
company's staff log in separately and only ever see their own data.

## Quick start (on your office PC)

1. Install Python 3.9+ if you don't have it.
2. In this folder:
   ```
   pip3 install -r requirements.txt
   python3 app.py
   ```
3. The very first time it runs, it prints a **super-admin username and
   password** to the terminal — write these down, they won't be shown
   again (though you can always reset via `admin_change_password`).
4. Open `http://localhost:5000` in a browser on the same PC, or
   `http://<this-PC's-LAN-IP>:5000` from any other device on the same
   office network (find your IP with `ipconfig` on Windows or
   `ifconfig`/`ip addr` on Mac/Linux).
5. Log in with the super-admin account → **Companies** → add your
   first company. That creates the company's own database and its
   first admin login, which you hand to that company's staff.

Leave the `python3 app.py` window running — closing it stops the
server for everyone. To keep it running after you close the terminal,
see "Running it continuously" below.

## How the two logins work

- **Super-admin** (you): manages the whole platform. Create
  companies, set each one's subscription status (Trial / Active /
  Expired / Suspended) and expiry date, add or remove that company's
  users. This is a manual, no-payment-gateway process for now — you
  decide who's active.
- **Company users**: log in and only ever see their own company's
  parties, transactions, and reports. A company whose subscription has
  lapsed sees a simple "subscription expired" screen instead of the
  app until you reactivate them.

## What's included vs. simplified from the desktop version

Fully working: Parties, Quality/Items, Purchase & Sale entry (with
D.O. auto-numbering and auto rate-fill), Receipt & Payment entry,
Capital & Expense entry, Receivable Ledger, Payable Ledger, Cash Book
(T-account), Profit & Capital, Stock report, PDF printing for every
voucher/report, per-company color theme, backup download.

Simplified in this first web version (works, but not yet as rich as
desktop): Receipt & Payment entry only records a single cash/cheque
line — the desktop app's multi-cheque table per voucher isn't ported
yet. No Trial Balance or "Invoices & Vouchers" browsing screen in the
web UI yet (the PDF exports for these still work via
`pdf_export.py` if you want to wire up a route).

## Backups

Each company user can go to **Download Backup** in the sidebar to
download a zip of their own database at any time. As the platform
admin, you can also just copy the whole `tenants/` folder — every
company's data lives in its own `tenants/<slug>/ultra_erp.db` file.
Consider setting up a scheduled copy of this folder to another drive
or cloud storage (Windows Task Scheduler / macOS `cron`) for real
disaster-recovery protection, since backups sitting on the same PC
as the live data don't protect against that PC failing.

## Running it continuously

The `python3 app.py` command above runs Flask's development server,
which is fine for trying this out, but two things matter for real use:

1. **Keep it running** even after you close the terminal:
   - **Windows**: use Task Scheduler to run `python app.py` at startup,
     or install [NSSM](https://nssm.cc/) to run it as a Windows service.
   - **Mac/Linux**: run it inside `screen` or `tmux`, or set it up as a
     `systemd` service (Linux) / `launchd` job (Mac).
2. **Switch to a production server** before relying on this for real
   business use or opening it to the internet — the built-in Flask
   server (`app.run(...)`) is explicitly not meant for production.
   The standard swap is [gunicorn](https://gunicorn.org/) (Linux/Mac)
   or [waitress](https://github.com/Pylons/waitress) (Windows-friendly):
   ```
   pip3 install waitress
   python3 -c "from waitress import serve; import app; serve(app.app, host='0.0.0.0', port=5000)"
   ```

## Making this reachable outside your office (to sell to other businesses)

Running it on your office PC only works for people on your office
network unless you either:

- **Port-forward** your router to expose port 5000 to the internet
  (simple but has real security tradeoffs — talk to whoever manages
  your network before doing this), or
- **Move it to real hosting** — a small VPS (DigitalOcean, Linode,
  Hetzner, a local Pakistani host) or a platform like Railway/Render.
  This is the safer, more standard path once you're ready to sell to
  outside customers: copy this whole folder to the server, run the
  same `pip3 install -r requirements.txt` + production-server steps
  above, point a domain name at it, and add HTTPS (most of those
  platforms provide free HTTPS automatically; on a bare VPS, use
  [Caddy](https://caddyserver.com/) or `certbot` for a free certificate).

I can help set up either path in more detail once you know which one
you want.

## Environment variables (optional)

- `ULTRAERP_SECRET_KEY` — set this to a long random string in
  production; without it, sessions use a fixed development key, which
  is fine for testing but not for a real deployment.
- `ULTRAERP_ADMIN_PASSWORD` — set this before the very first run to
  choose your own super-admin password instead of the random
  auto-generated one.

## What's next

Natural next additions, in roughly the order I'd suggest tackling
them: multi-cheque support in the web Receipt & Payment form (to match
the desktop app), a Trial Balance and Invoices & Vouchers page, an
"impersonate this company" button for you to help troubleshoot a
customer's account without needing their password, and — when you're
ready to charge automatically instead of marking subscriptions active
by hand — a payment gateway integration (Stripe internationally, or a
local Pakistani gateway).

## What's fixed/new in this update

1. **Fixed the "can't manage subscriptions" bug.** The real cause: the
   login page silently redirected you to whatever account you were
   already signed in as, so if you'd tested a company login earlier,
   there was no way back to sign in as super-admin without an explicit
   sign-out first. The login page now shows who you're currently
   signed in as and lets you continue or switch accounts.
2. **Party Ledger report** (`Reports → Party Ledger`) — pick any party
   and see their complete chronological history: every entry with its
   date, reference number, debit/credit, and running balance.
3. **Company admins can add their own users** (`Team` in the sidebar)
   — no need to go through the platform admin for routine staff
   accounts. Regular staff can't access this page, and one company
   can never see or modify another company's users, even by guessing
   an ID.
4. **Receivable/Payable ledgers now show Full Amount and Remaining
   separately**, not just the outstanding balance.
5. **Purchase & Sale Bookings** (`Bookings` in the sidebar) — record a
   forward deal now, deliver against it later (in full or in parts).
   Nothing touches stock or the party's balance until an actual
   delivery is recorded; each delivery becomes a normal Sale/Purchase
   entry with its own D.O. number, flowing into every report exactly
   like a walk-in transaction would.
6. Ledgers and the D.O. slip were already redesigned in a lighter,
   cleaner style (thin rules instead of solid color blocks).
7. Company logo and warehouse address (Settings page) were already
   wired into the printed D.O. slip.

## What's new in this update

1. **Trial Balance report** added (`Reports → Trial Balance`), with PDF export.
2. **Purchase rate is no longer a manually-maintained field.** The
   Quality/Item form only asks for the Sale Rate now — the Purchase
   Rate shown everywhere (Stock report, Profit calculation) is derived
   automatically as the quantity-weighted average of that item's actual
   Purchase entries (including deliveries against Purchase bookings),
   so it always reflects real buying activity instead of a number
   someone has to remember to update.
3. **Searchable party/item dropdowns.** Every place you pick a party or
   an item — Purchase & Sale entry, Receipt & Payment entry, Bookings,
   and the Party Ledger — now lets you type to filter instead of
   scrolling a long list.
4. **Saving an entry no longer jumps straight to printing.** After you
   save a Sale, Purchase, Receipt, Payment, Expense, Capital entry, or
   a booking delivery, you're returned to a fresh, blank entry form
   with a "Saved as INV-000001" confirmation and a separate "Print
   This Voucher" button — so you can keep entering back-to-back
   transactions without a PDF interrupting you each time, and print
   only when you actually want to.

## What's new in this update

1. **Multiple cheques on one Receipt/Payment voucher.** Switch Mode to
   "Cheque" in Receipt & Payment Entry to add several cheque lines
   (date, bank, cheque number, amount) under a single voucher — the
   total is always their sum, and the printed voucher lists every
   cheque in a table.
2. **Search Purchase & Sale entries** by invoice number, D.O. number,
   or serial number — searches your entire history, not just the
   recent list, so an old entry is always a search away.
3. **Sale D.O. quantity now matches the font of every other field**
   (previously it stood out in an oversized, colored style).
4. **E-signature capture on Sale entries.** Tick "Get the receiver's
   signature before saving" on a Sale entry to walk through: fill in
   the entry → capture a signature (finger, stylus, mouse, or most
   USB/Bluetooth signature pads work, since they act like a mouse or
   touchscreen) → the entry saves → optionally print, with the actual
   signature embedded on the printed D.O. in place of the blank
   signature line. Skip the checkbox and entries save exactly as
   before — this is entirely optional per entry.

## Fixed: "database is locked" error

If you saw `sqlite3.OperationalError: database is locked` (for example
when deleting an entry) after more than one person started using the
app at the same time, this is now fixed. SQLite only allows one writer
at a time by default, and the two settings that solve this cleanly are
now applied to every database connection:

- **WAL mode** — lets reads and writes happen at the same time instead
  of a write blocking every reader.
- **A busy timeout** — if two people do genuinely write at the exact
  same instant, SQLite now waits and quietly retries for a few seconds
  instead of immediately throwing an error.

This was stress-tested with 10 simultaneous connections hammering the
database with writes and deletes at once — zero errors.

## Moving to the cloud (off your laptop)

See `deploy/DEPLOYMENT.md` for the full step-by-step guide to moving
this off your laptop onto a small always-on server (DigitalOcean), with
automatic daily backups to Backblaze B2 and a real domain with HTTPS.

Quick summary of what's in `deploy/`:
- `DEPLOYMENT.md` — the full walkthrough, start here
- `setup.sh` — one-time server setup (installs everything, configures HTTPS)
- `setup_backups.sh` — one-time Backblaze B2 backup setup
- `backup.sh` — the actual backup script (runs automatically via cron once set up; backs up every company completely separately, never combined)
- `ultraerp.service` — keeps the app running always, restarts on crash/reboot
- `Caddyfile` — automatic HTTPS configuration

`serve.py` is the production server entry point (used automatically by
the systemd service) — it replaces the "development server" warning
you saw with `python3 app.py` with a proper production-grade server.

## Beta release — 17 final changes

This round covers everything requested before beta testing:

1. **Export to Excel** on every ledger/report (Receivable, Payable,
   Cash Book, Party Ledger, Trial Balance, Stock, Profit, Brokerage) —
   sits next to the existing "Print / Save PDF" button.
2. **Cash Book relabeled** — "Debit/Credit" → "Banaam/Jama".
3. **Edit option** for Sale, Purchase, Receipt, Payment, Expense, and
   Capital entries — gated by the new permission system (#9).
4. **Remarks column** added to the Cash Book, both on screen and in
   the PDF/Excel exports.
5. **Landscape, two-copy printing** for the Sale/Purchase D.O. and the
   Receipt/Payment voucher — Office Copy and Customer Copy side by
   side on one A4 sheet.
6. **Booking breakout** — click into any booking to see every
   individual delivery ever made against it, each with its own D.O.
   number and print link.
7. **Search everywhere** — every list page (Parties, Quality,
   Transactions, Recovery, Bookings, Brokerage, Team) now has a
   working search box.
8. **Receipt/Payment by sign** — in Cash mode, a positive amount is
   automatically a Receipt and a negative amount is automatically a
   Payment. Cheque mode keeps an explicit direction choice, since a
   physical cheque amount is always positive.
9. **Delete/Edit permissions** — deleting is admin-only, always. A
   company admin can grant individual staff members the right to edit
   entries (Team page); staff can never delete regardless.
10. **Daily automated email reports** — set a notification email per
    company (Settings page) and the Receivable, Payable, Cash Book,
    and Stock reports are emailed automatically every day, completely
    independently per company. Requires SMTP details on the server —
    see `deploy/setup_email_reports.sh`.
11. **Zakat** as a third expense category alongside Home and Office —
    flows through the Cash Book, Capital Account, and Profit report
    exactly like any other expense.
12. **"Expense" party type** — its own ledger, but never appears in
    the Receivable or Payable ledgers.
13. **Automatic brokerage** — set a broker's rate once (percentage or
    fixed-per-unit) and every Sale/Purchase they're assigned to
    calculates brokerage automatically, tracked in its own searchable
    Brokerage report, never mixed into the Payable Ledger.
14. **Contra entries** — reclassify a balance between two (or more)
    parties/accounts without it counting as real cash movement; must
    balance Dr = Cr before it saves.
15. **"Bank" party type** — its own ledger, excluded from Receivable/
    Payable, behaves normally in the Cash Book.
16. **Subscription due-date tracking** for you (the platform admin) —
    a dedicated page listing every company sorted by how soon their
    subscription is due, with overdue ones flagged first.
17. **Full QA pass** — ran end-to-end as super-admin, company admin,
    and staff, covering every feature above together on one shared
    dataset, plus cross-company data isolation and permission
    boundaries. All green.
