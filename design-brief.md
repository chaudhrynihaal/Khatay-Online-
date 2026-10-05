# ULTRA ERP ("Khatay") — Complete Functional Specification & UI Redesign Brief

## How to use this document

This is a complete inventory of every screen, field, button, and behavior in a working multi-tenant
business-management web app. The current UI is a plain, utilitarian data-table design (white cards,
a purple sidebar theme, HTML tables) — **that visual design is not precious and should be treated as
disposable.** What must survive a redesign is every piece of *functionality* listed below: every field,
every action, every business rule, every conditional behavior. Nothing here is a request to keep the
current look. Redesign the navigation, the layout system, the components, the visual language —
completely — around the capabilities below.

Where a rule affects what the UI must be able to show or do (e.g. "a warning appears but doesn't block
saving"), that's a functional requirement, not a styling note — keep the behavior, replace the look.

---

## 1. What this product is

A multi-tenant SaaS business-management platform for small-to-medium businesses (currently used by real
textile/yarn trading companies in Pakistan). One deployment serves many independent companies
("tenants"), each with completely isolated data. Each company picks one **business type** and gets a
purpose-built set of tools for that trade:

- **Yarn / Textile Trading** — the original, most complete vertical: full double-entry-style
  bookkeeping, forward-contract bookings, brokerage tracking, signature capture, multi-report suite.
- **Kiryana** (grocery / general store) — inventory-driven retail: barcode scanning, expiry tracking,
  low-stock alerts, simple sale/purchase/return flow.
- **Hardware store** — everything Kiryana has, plus B2B features: credit limits, customer-specific
  pricing, quotations, item variants, tax-inclusive invoicing, smart reorder suggestions.
- **Fabric** and **Broker** — shown as "Coming soon" placeholders, not yet built. A redesign can either
  leave these as disabled/teaser cards or design placeholder screens for future build-out.

A subscription model gates access per company: **Trial** (time-limited), **Active**, **Expired**,
**Suspended**. An expired/suspended company sees a blocking "subscription expired" screen instead of the
app.

The product is installable as a **PWA** (add-to-home-screen, works offline for already-visited pages;
new transactions/data entry require a live connection — offline write queueing is intentionally not
supported, to avoid double-booked sales or corrupted stock counts).

---

## 2. User roles

1. **Platform Super Admin** — one account, not tied to any company. Manages the whole platform: creates
   companies, sets/extends subscriptions, creates the first admin login for each company, can add
   additional users to any company, changes their own password. Never sees a company's actual business
   data (parties, transactions, inventory) — only account/subscription-level info.
2. **Company Admin** — full access within their one company: all data entry, all edit/delete rights,
   manages their team (add/remove staff, grant edit rights), company settings, backups.
3. **Company Staff** — can view and enter data (sales, purchases, etc.) but cannot delete entries by
   default, cannot manage the team, cannot access company settings/backups. An admin can grant an
   individual staff member "edit rights" (can correct past entries) without full admin rights.

---

## 3. Platform-level screens (shared by every business type)

### 3.1 Login
Single login form (username + password) for both super-admin and company users — the system detects
which and routes accordingly after login. If already signed in, shows a "Continue as X / Sign out and
switch account" banner instead of forcing a re-login. Has a "Forgot password?" link. Login attempts are
rate-limited (protection against password guessing) with a friendly "too many attempts, wait a minute"
message on lockout, not a raw error.

### 3.2 Forgot Password / Reset Password
- Forgot Password: single "Username or Email" field. Always shows the same generic confirmation message
  regardless of whether the account/email actually exists (security: prevents an attacker from probing
  which usernames are real). Emails a reset link if a match with a verified email is found.
- Reset Password: reached via the emailed link (token expires after 30 minutes, single-use). New
  Password + Confirm New Password fields, minimum 6 characters, must match.

### 3.3 Business Type Selector
Shown after login (or accessible any time) as a grid of cards: Yarn, Kiryana, Hardware, Fabric (disabled/
"coming soon"), Broker (disabled/"coming soon"). Picking one enters that vertical's app.

### 3.4 Team Management (company admin only)
- "Add a team member" form: Username, Password, Full Name, Email (used for their own password-reset),
  Role (Staff / Admin).
- Table of everyone with access: Username, Full Name, editable Email field (inline save button per row),
  Role, "Can Edit Entries" toggle (admins always can; staff can be individually granted this), Remove
  button. Search by username/name. Can't remove yourself.

### 3.5 Company Settings (company admin only)
- Company name (shown on every report/invoice).
- Warehouse address (printed on delivery-order slips).
- Logo upload (PNG/JPG/GIF, shown on invoices/vouchers and in the settings page itself once uploaded).
- Color theme picker — swatches for 8 preset themes (Purple, Blue, Green, Red, Grey, Orange, Navy,
  Black), click to select, applies platform-wide for that company.
- Opening Cash Balance: amount + "as of" date — the Cash Book report adds every transaction from that
  date forward on top of this starting figure.
- Daily Email Reports: one notification-email field. If set, that address automatically receives the
  Receivable, Payable, Cash Book, and Stock reports by email every day; blank turns it off.

### 3.6 Backup & Restore (company admin only)
- **Backup**: on-demand "back up now" action (also runs automatically daily via a scheduled job).
- **Backup History**: full list of every daily backup ever taken (date, file size), kept permanently.
  Each has a "Restore This" action — clicking opens a serious confirmation dialog: shows the exact
  backup date, warns that anything entered since will be lost from the live app (but is itself safely
  preserved in an automatic pre-restore safety copy), and requires typing the word **RESTORE** exactly
  before the action is enabled. Not configured yet on a server shows a plain "not set up" empty state
  instead of an error; a cloud-connectivity failure shows its own distinct error state.

### 3.7 Data Import (company admin only)
A 3-step wizard for bringing existing data in from another system, each step downloads an Excel
template first:
1. **Parties** (customers/suppliers/brokers) — name + current balance.
2. **Items/Quality** — with current stock quantity.
3. **Outstanding Invoices** (optional, recommended) — the real per-invoice breakdown of what's still
   unpaid per party, rather than one lump-sum balance, so Receivable/Payable reports show true detail
   from day one. Requires Step 1 done first (needs party names to already exist).
Each step: file upload (.xlsx or .csv) → import. Already-existing names are silently skipped, so
re-uploading a corrected file is always safe (idempotent).

### 3.8 Platform Super-Admin Panel
- **Companies list / dashboard**: "Add a new company" form (Company Name, Trial Length in days, Admin
  Username, Admin Password, Admin Full Name, Admin Email) + table of all companies (Name, subscription
  status badge, expiry date, created date, "Manage" link).
- **Company Detail** page: update subscription (Status dropdown: Trial/Active/Expired/Suspended, Expiry
  Date, Notes), "Add a user" form for that company, table of that company's users with Remove action.
  Explicitly cannot see that company's actual business data — banner says so.
- **Subscriptions** overview: stat cards (Overdue count, Due-within-7-days count, Total companies),
  table of every company with status badge, expiry date, days-until-due (or "Overdue by Nd" / "Due
  today"), sorted for urgency.
- **Change Password** (their own super-admin login).

### 3.9 Subscription Expired screen
Shown instead of the whole app to any company user when their subscription lapses — a blocking, full
screen message (not a normal page with a banner), telling them the subscription needs renewal.

---

## 4. YARN vertical (full detail)

### 4.1 Dashboard
4 stat cards: Total Receivable, Overdue Receivable (red if > 0), Total Payable, Net Profit (this month).
Quick action buttons: New Sale/Purchase, New Receipt/Payment, New Party, View Receivable Ledger. A
small "This company" line: party count · items in stock master.

### 4.2 Parties (customers, suppliers, brokers, and general ledger-style accounts)
- **Add a party** form: Name*, Type (Customer / Supplier / Broker / Expense / Bank), City, Phone, NTN,
  STN, Credit Limit, Opening Balance, Address. Choosing "Broker" reveals extra fields: Brokerage Rate
  Type (Percentage of sale amount / Fixed rate per unit), Brokerage Rate value — this auto-calculates
  brokerage owed on every transaction that broker is assigned to.
- **List/search**: search by name/city/phone. Table: Name, Type, City, Phone, Balance, Status badge
  (Receivable / Payable / Settled — color-coded), Edit, Delete (blocked with a clear message if the
  party has any transactions recorded, or has imported outstanding invoices — a separate "clear imported
  invoices" action unblocks that second case).
- **Edit party** page: same fields, shows current balance prominently. Also surfaces a "clear opening
  entries" action for imported outstanding-invoice detail (see Data Import) so the party can eventually
  be deleted if truly no longer needed.

### 4.3 Quality / Items (the "products" being traded — yarn qualities)
- **Add an item** form: Name*, City/Area, Sale Rate, Opening Stock Qty. Explicitly has **no manual
  Purchase Rate field** — that's automatically computed as the quantity-weighted average of every real
  purchase recorded for that item (shown as "avg, from purchases" in the list), and that derived value
  is what's used to value stock in the Profit report.
- **List/search**: search by item/area. Table: Item, Area, Purchase Rate (avg), Sale Rate, Stock (red
  if negative), Delete (blocked if the item has any transactions against it).

### 4.4 Purchase & Sale Entry (single unified transaction form)
A two-step wizard:
- **Step 1 — Entry**: Type (Sale/Purchase), Date, D.O. (delivery order) Number (auto-suggested next
  number, editable), Broker (optional, searchable), Party* (searchable), Item/Quality* (searchable,
  auto-fills Sale Rate for Sale type only — Purchase rate is always typed fresh), Qty*, Rate*, computed
  read-only Amount, Credit Days, Mode (Cash/Cheque), Cheque No., Description. A checkbox "Get the
  receiver's signature before saving" (Sale only).
- **Step 2 — Signature** (only if checkbox ticked): a full-width **canvas signature pad** (mouse/touch/
  stylus/signature-pad compatible), Clear button, Back button, Confirm & Save. The captured signature
  image gets embedded on the printed voucher.
- **Recent entries** list below: searchable by invoice #/D.O.#/serial #. Table: Voucher #, Date, Type,
  D.O.#, Party, Item, Qty, Rate, Amount, and per-row Print (PDF voucher), Edit, Delete actions
  (Edit needs "can edit" permission, Delete is admin-only). A "saved" success banner with a direct
  "Print This Voucher" shortcut appears right after saving.

### 4.5 Bookings (forward contracts / "sauda")
A deal struck now for delivery later — explicitly does **not** touch stock or the party's balance until
an actual delivery is recorded against it (fully or in parts, multiple partial deliveries allowed).
- **New booking** form: Type (Sale/Purchase), Date, Party*, Item*, Qty*, Rate*, Delivery Terms (free
  text, e.g. "within 30 days, ex-warehouse").
- **Status tabs**: Open / Delivered / Cancelled / All, each with its own list + a search box.
- **List** columns: Booking #, Type, Date, Party, Item, Qty, Rate, Delivered (running total), Remaining,
  Terms, Status badge. Per open booking: an inline expandable **"Deliver" mini-form** (Deliver Qty
  capped at remaining, Delivery Date, D.O. No., Credit Days, Mode, Cheque No., Confirm Delivery) that
  creates a real Sale/Purchase transaction using the booking's original locked-in rate. A booking auto-
  flips to "Delivered" once fully delivered. **Cancel** is only available before any delivery has been
  made against it (blocked with a message otherwise).
- **Booking detail** page (click a booking #): full booking info + a table of every individual delivery
  ever made against it (date, D.O., qty, rate, amount, mode).

### 4.6 Receipt & Payment Entry (money movement not tied to a Sale/Purchase)
- Type (Receipt = money in / Payment = money out), Date, Party*.
- **Mode = Cash**: a single Amount field where the *sign* decides direction — typing a positive number
  makes it a Receipt, negative makes it a Payment, and the Type dropdown becomes a live read-only
  indicator instead of an input (hidden, replaced by a note) in this mode.
- **Mode = Cheque**: the Type dropdown becomes a real input (cheques are always entered as positive, so
  direction must be chosen explicitly). A repeatable "Cheque Lines" mini-table — Date, Bank, Cheque #,
  Amount per row, "+ Add Cheque" — the voucher's total amount is always the sum of every cheque line
  added; running total shown live.
- Description field. Recent entries list: Voucher #, Date, Type, Party, Mode, Amount, Description, with
  Print/Edit/Delete per row (same permission rules as Purchase & Sale).

### 4.7 Capital & Expense Entry
Two tabs on one page:
- **Home & Office Expense**: Date, Category (Home / Office / Zakat), Amount*, Description. List of
  recent expenses with Print/Edit/Delete.
- **Capital In / Out**: Date, Direction (Capital Introduced / Capital Withdrawn), Amount*, Description.
  3 summary stat cards (Total Introduced, Total Withdrawn, Net Capital, all-time) + full history table
  with Print per entry.

### 4.8 Contra Entries
Reclassifies a balance between two or more parties/accounts (e.g. Cash → Bank) without it counting as a
real cash-in/cash-out event (deliberately excluded from the Cash Book).
- Date field, then a repeatable "legs" builder: pick a Party, choose Impact (Dr = increases their
  balance / Cr = decreases it), Amount, "+ Add Party" — builds a running table of legs with Remove per
  row. Live running Total Dr / Total Cr with a "✓ Balanced" / "✗ Not balanced yet" indicator. Requires
  at least 2 legs and Dr must exactly equal Cr before it can be saved (validated both live in the UI and
  again on the server). Description field. History table below shows every past contra entry with all
  its legs summarized inline.

### 4.9 Reports (all support a date-range or as-of-date filter where relevant, plus "Print / Save PDF"
and "Export to Excel" actions on every report)
- **Receivable Ledger**: as-of-date filter. Stat cards (Total Outstanding, Overdue). Grouped by party,
  each group showing every individual outstanding invoice — Invoice #, Date, D.O.#, Item, Qty, Rate,
  Full Amount, Remaining, Credit Days, Due Date, and a computed Status ("Overdue by Nd" / "Due today" /
  "Not due (Nd)"), with a subtotal per party.
- **Payable Ledger**: the identical structure, mirrored for what the company owes suppliers.
- **Party Ledger**: pick any single party (searchable dropdown, auto-submits on selection) → full
  running-balance statement: party info header (name/city/phone/NTN) + big "Closing Balance" figure
  labeled Receivable/Payable/Settled, then a complete chronological table (Date, Reference, Type, D.O.#,
  Item, Qty, Debit, Credit, running Balance) starting from an Opening Balance row, ending with column
  totals.
- **Stock Report**: every item with Area, Purchase Rate (avg), Sale Rate, Stock Qty (red if negative).
- **Trial Balance**: every party with nonzero activity — Debit (Sale+Payment), Credit (Purchase
  +Receipt), Balance — plus a grand total row.
- **Profit & Capital**: date-range filter. A full profit waterfall: Total Sales, Total Purchases,
  + Opening Stock Value, − Closing Stock Value, = Cost of Goods Sold, = Gross Profit, − Home Expense,
  − Office Expense, − Zakat, = **Net Profit**. Below it, the all-time Capital Account summary (Total
  Introduced / Withdrawn / Net Capital).
- **Brokerage Report**: filterable by broker and date range; every Sale/Purchase transaction that has a
  broker assigned, with the brokerage amount automatically computed per that broker's configured rate
  (percentage of amount, or fixed per unit).
- **Cash Book**: date-range filter, a running T-account style statement of every cash-affecting event
  (cash sales, cash purchases, payments received/made, cash-mode returns, expenses) with a running
  balance, seeded from the configured Opening Cash Balance.
- *(Known gap, not yet built: a "Quality Ledger" — a per-item transaction history report — has a route
  and a nav-adjacent concept but no backing implementation. Worth designing a placeholder or including
  as a real feature if you choose to build it out.)*

### 4.10 Voucher printing
Every Sale/Purchase/Receipt/Payment/Expense/Capital entry has a "Print" action producing a real PDF:
- **Sale/Purchase**: a delivery-order-style slip, printed **two copies side by side on one landscape
  page** (Office Copy + Customer Copy) — boxed serial number, company logo, plain underlined fields
  (Quantity/Quality/Rate/Broker/D.O. No./Credit Days), embedded signature image if one was captured. The
  customer's own copy of a Sale hides the rate (a driver/warehouse hand receiving goods doesn't need to
  see pricing); Purchase D.O.s show rate on both copies.
- **Receipt/Payment**: also two copies side-by-side landscape — company header, a colored voucher-number
  stamp, a cheque-lines table (or a single cash line) with a total, amount spelled out in words
  ("Rupees, lakh/crore" style), signature line.
- **Expense/Capital In/Capital Out**: single-page portrait "card" style voucher — big boxed amount,
  amount-in-words, signature strip.

---

## 5. KIRYANA vertical (grocery / general store)

Deliberately a **simpler, separate data model** from Yarn — not the same engine reused. Every module
below is independent per company.

### 5.1 Dashboard
Stat cards (several are click-to-expand into a detail breakdown table): Total Stock (qty), Total Stock
Value, Cash Balance, Sales Today, Total Sales (all-time), Net Profit (Sales − Expenses), Total
Receivable (expandable: per-customer breakdown with "View Ledger" links), Total Payable (same, per-
supplier), **Low Stock** count (expandable: item, current stock, reorder level, "Restock" shortcut —
only items with a reorder level actually configured are flagged), **Expiring Soon (30 days)** count
(expandable: item, qty, purchase date, expiry date, visually flags anything already expired). Quick
actions: New Sale, New Purchase, New Item, New Expense, Print.

### 5.2 Inventory
- **Add items** — a **repeatable multi-item form** (not one-at-a-time): each "card" has Name*, Unit
  (dropdown of standard grocery units — kg, g, L, ml, pcs, dozen, packet, box, bag, bundle — plus a
  free-text "Other" fallback), Category (free text with autocomplete from existing categories), Barcode
  (scan or type), Purchase Rate, Sale Rate, Opening Stock Qty, Reorder Level (0 = no low-stock alert),
  Bulk Purchase Unit + Units-per-Bulk-Unit (optional — lets you buy "1 carton = 24 units" and still stock
  individually; surfaces a quick bulk→base-unit converter on the Purchase form). "+ Add Another Item"
  adds more cards in the same save; blank cards are silently skipped; duplicate barcodes within the same
  batch are rejected before anything saves.
- **List**: category filter dropdown, search, table (Item, Category, Unit, Barcode, Purchase Rate, Sale
  Rate, Stock — red if ≤0, amber-flagged with a ⚠ if at/below reorder level), Edit, Delete (blocked if
  the item has any transaction history).

### 5.3 Sale Book
- Barcode scan input (works with a handheld USB/Bluetooth scanner, or a "📷 Scan with Camera" button
  using the device camera) — a recognized barcode auto-adds/selects that item on a line; an unrecognized
  one prompts to quick-add a brand-new item on the spot without leaving the page.
- **Multi-item line-based form**: Date, Customer (searchable, quick-add-a-new-customer inline), Mode
  (Cash/Credit), repeatable item lines (Item [searchable + quick-add], Qty, Rate [auto-fills from item's
  Sale Rate], computed Amount, remove-row), "+ Add Line", running grand Total. A live **stock warning**
  appears inline per line if the qty being sold exceeds what's on hand — it does **not block** the sale,
  just warns, and asks for an explicit confirm at submit time if still over. Description field. Credit
  mode requires a customer to be picked.
- **Recent sales**: one row per invoice (not per line — a 3-item sale is one collapsible row showing
  "Item A, Item B, Item C (3 items)"), expandable to see每 individual line, with per-line Edit/Delete and
  a per-bill Print button (generates a real PDF receipt).
- **Add a new customer** mini-form pinned on the page: Name*, Phone.

### 5.4 Purchase List
Same multi-line structure as Sale Book, but per line also asks for **Sale Rate** (so restocking and
re-pricing happen in one step — every purchase updates that item's going-forward selling price) and an
optional **Expiry Date** per line (shows up on the dashboard's Expiring Soon card as it approaches). Also
has the bulk-purchase-unit quick converter (buy 2 cartons @ Rs 4800 total → auto-computes base-unit qty
and per-unit rate). Recording a purchase always updates the item's on-file Purchase Rate to the latest
actual purchase rate. "Add a new supplier" mini-form (Name*, Phone).

### 5.5 Returns
Two tabs: Sale Return / Purchase Return.
- "Return against a bill" — a searchable dropdown listing recent bills **grouped one-per-invoice** (not
  one-per-line — this was a real bug fixed this session: a 3-item bill used to show as 3 confusing
  near-identical entries). Picking a single-item bill auto-fills the return form directly; picking a
  multi-item bill reveals a small sub-picker listing each line so the exact item/qty/rate being returned
  can be chosen.
- Manual entry is also fully supported (leave the bill picker blank): Date, Item*, Customer/Supplier,
  Mode (Cash refund / Credit note — a credit note doesn't touch the Cash Book, just adjusts the ledger
  balance), Qty*, Rate* (prefilled from the original sale/purchase rate when picked from a bill, not
  today's rate), computed Amount, Reason/Description.
- Recent returns list, grouped by invoice, same expandable pattern as Sales/Purchases.

### 5.6 Cash Book
Running balance of every cash-affecting event (cash sales, cash purchases, cash-mode returns, payments,
expenses), oldest first.

### 5.7 Ledger
Customer/Supplier tab toggle, searchable party picker, full running-balance statement per party
(mirrors the Yarn Party Ledger pattern, simpler schema). Payment entry (date, amount, description)
recordable directly from here; individual past transactions/payments editable/deletable inline.

### 5.8 Expenses
Simple expense log: Date, Category, Description, Amount — add/edit/delete.

### 5.9 Printed bills
A real generated PDF per invoice: plain single-copy receipt style — company name, doc-type label ("Sale
Receipt"/"Purchase Bill"/"Sale Return"/"Purchase Return"), invoice # + date, Customer/Supplier + phone,
itemized table (Item/Qty/Rate/Amount), bold total, optional note, generated-on timestamp footer.

---

## 6. HARDWARE vertical

**Everything Kiryana has (full parity: dashboard, inventory with multi-add, sales, purchases, returns,
cashbook, ledger, expenses, barcode scanning, PDF bills)** — plus these hardware-store-specific
additions:

### 6.1 Dashboard extras
Same stat-card layout as Kiryana, plus: an **"Open Quotations"** count card linking to the Quotations
page. The Low Stock breakdown here goes further than Kiryana's — it also shows **Sold (30 days)** and a
computed **Suggested Reorder** quantity per item (enough to get back above the reorder level, plus
whatever actually sold in the trailing 30 days) — explained inline. A **Tax Settings** mini-form directly
on the dashboard: Tax Rate % (0 = off), Our GST Number — when tax rate is set, every printed bill shows a
Subtotal/Tax/Total breakdown instead of one flat total.

### 6.2 Inventory extras
Same multi-item add form as Kiryana, plus two more fields per item: **Variant Of** (a dropdown of
existing "parent" items — makes this a variant, e.g. "Screws — 1 inch" grouped under a parent "Screws"
item for easier browsing, while still tracking fully independent stock/rate) and **Variant Name** (free
text, e.g. "1 inch", "Red", "Large"). The item list visually indents/labels variants under their parent.
Standard unit dropdown is hardware-appropriate: pcs, box, set, pair, roll, meter, kg, carton, packet,
bundle.

### 6.3 Customers & Suppliers (party management — Hardware-only page, Kiryana has no equivalent)
- List with type tabs, Edit link per party.
- **Edit party** page: Name, Phone, Opening Balance, and for Customers only: **Credit Limit** (0 = no
  limit — a note explains that exceeding it on a Credit sale shows a warning, doesn't block), and for
  everyone: **GST Number** (for tax invoicing).
- **Special Pricing** section (Customers only): a table of item-specific negotiated rates for that one
  customer (Item, Special Rate, Remove), plus an add-new-override mini-form. These rates auto-apply on
  the Sale Book the instant that customer + that item are both picked, silently overriding the item's
  normal Sale Rate.

### 6.4 Quotations
A quotation is a price quote that touches **neither stock nor the ledger** until explicitly converted.
- **New quotation** form: same multi-line structure as a Sale (Date, Customer, repeatable Item/Qty/Rate
  lines with quick-add, running total, Description).
- **Open quotations list**: grouped-by-invoice with expandable line detail (same pattern as
  Sales/Purchases/Returns), each with Print and a prominent **"Convert to Sale"** button (confirms first:
  "Stock and the Ledger will update") — conversion creates a brand-new real Sale with its own invoice
  number while the original quotation is preserved/marked as converted, not deleted, so its history stays
  visible.

### 6.5 Sale Book extras (beyond Kiryana's version)
- **Credit limit warning**: if the selected customer has a credit limit configured and Mode is Credit,
  a live-updating inline warning shows if the sale (current cart total + their existing balance, minus
  any partial payment entered now) would push them over that limit — soft-warn only, confirmable at
  submit, never a hard block.
- **Split payment**: a "Amount Paid Now (Cash)" field appears in Credit mode — lets a customer pay part
  cash immediately on a credit sale, recording a separate payment transaction alongside the sale rather
  than forcing all-or-nothing.
- **Customer-specific pricing auto-apply**: picking a customer with a negotiated rate on an already-
  selected item live-updates that line's rate; the reverse (picking the item after the customer) also
  auto-applies it.
- Same stock-oversell soft-warning as Kiryana's Sale Book.

### 6.6 Printed bills (visually distinct from Kiryana's on purpose)
A fuller invoice-style PDF: solid color header band (company name + doc label in white-on-brand-color),
invoice # + date top-right, a "Billed To" block (or Supplier block) + Payment Mode + both parties' GST
numbers where applicable, a numbered item table, a Subtotal/Tax/Total breakdown box when tax is
configured (else a plain Total), optional note, **Received By / Authorized Signature** blank signature
lines at the bottom, generated-on footer.

---

## 7. Cross-cutting UX systems (apply across all 3 verticals)

- **Searchable selects**: every party/item dropdown of meaningful size is a type-to-filter search box,
  not a giant native `<select>` — type to filter, click to pick.
- **Quick-add inline**: on Sale/Purchase-type forms, typing a name that doesn't exist in a searchable
  item/party dropdown offers a "+ Add '{text}' as a new item/customer/supplier" option that creates it
  and selects it without leaving the page or losing anything else already filled in.
- **Barcode scanning**: a dedicated input that accepts both a physical USB/Bluetooth handheld scanner
  (keyboard-wedge style: types the code, sends Enter) and a device camera (a "📷 Scan with Camera"
  button opens a live camera view). A recognized code jumps straight to selecting/adding that line item;
  an unrecognized one offers to create a brand-new item on the spot.
- **Soft-warn, never hard-block pattern**: stock-oversell, credit-limit-exceeded, and similar "this looks
  like a mistake but might be intentional" situations always show an inline warning and require an
  explicit confirm to proceed — they never silently block a legitimate business action (e.g. a real
  emergency sale of the last item in stock, or a valued customer's one-time credit exception).
  Server-side, the same situations are also non-blocking (a safety-net flash message, not a rejection).
- **Invoice/bill grouping**: anywhere multiple line items were saved together in one click (a multi-item
  sale/purchase/return/quotation), lists always show **one row per bill** (with a line-item count and an
  expandable detail view), never one row per underlying database line — this was a real bug fixed
  multiple times this session and should be treated as a hard requirement everywhere bills are listed.
- **Print-friendly pages**: every list page has a browser-print button; printed views hide navigation/
  buttons (a `no-print` convention) and adapt table layout for paper.
- **Real PDF generation**: every printable document (Yarn vouchers, Kiryana/Hardware bills, every report)
  is a genuinely generated PDF (not just "print this webpage"), downloadable/openable in a new tab.
- **Excel export**: every report also has a one-click "Export to Excel" alongside its PDF option.
- **Mobile / PWA**: installable to a home screen with its own icon, works standalone (no browser chrome),
  shows a distinct "you're offline" banner state when connectivity drops (previously-visited pages still
  render from cache; anything that would write data is clearly communicated as unavailable until back
  online, never allowed to silently fail or duplicate).

---

## 8. Core data entities (for context on data density / table design)

- **Company** (tenant): name, slug, subscription status/expiry, notes, theme, logo, business type.
- **User**: username, full name, email, role (staff/admin/super_admin), can_edit flag.
- **Party** (Yarn): name, city, phone, NTN, STN, address, credit limit, opening balance, type (Customer/
  Supplier/Broker/Expense/Bank), brokerage type/rate if Broker.
- **Quality/Item** (Yarn): name, area, sale rate, computed avg purchase rate, computed stock.
- **Transaction** (Yarn): the single table backing Sale/Purchase/Receipt/Payment/Expense/Capital In/
  Capital Out/Contra Dr/Contra Cr — voucher type + number, date, party, broker, item, qty, rate, amount,
  mode, cheque #, description, credit days, signature image, linked booking (if any).
- **Booking** (Yarn): a pre-transaction forward contract — qty/rate locked in, tracks delivered-so-far
  and remaining, status.
- **Kiryana/Hardware Item**: name, unit, purchase/sale rate, stock qty, barcode, reorder level, category,
  bulk-purchase unit + conversion factor; Hardware items additionally: parent item (for variants),
  variant name, credit-limit-relevant fields live on the party instead.
- **Kiryana/Hardware Party**: name, phone, type, opening balance; Hardware additionally: credit limit,
  GST number, and a separate customer-specific-price table (party × item × rate).
- **Kiryana/Hardware Transaction**: a single flat table per vertical with a `txn_type` (SALE, PURCHASE,
  SALE_RETURN, PURCHASE_RETURN, and Hardware also QUOTATION/QUOTATION_CONVERTED) — line items sharing an
  `invoice_no` are one "bill."

---

## 9. Explicitly out of scope for this brief

- Fabric and Broker verticals — not built, currently just disabled teaser cards.
- Payment gateway integration, SMS notifications, customer-facing portal, multi-currency, audit log,
  session timeout controls — none of these exist; don't design screens for them unless asked.
- Platform-wide analytics/impersonation for the super-admin — the super-admin's view is deliberately
  limited to account/subscription management only, never business data.

---

## 10. What "complete UI redesign" should still guarantee

Whatever the new visual system looks like, it must still let a user do everything in sections 3–7 above.
If you're feeding this to a design tool as a prompt, a good framing is: *"Design a modern, clean business
app for [X] roles across up to 3 industry-specific modes, covering every screen and field listed in this
spec — reimagine the navigation, layout, components, and visual identity completely, but preserve every
listed capability, field, and business rule."*
