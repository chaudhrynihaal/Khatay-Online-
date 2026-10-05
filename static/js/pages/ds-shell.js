/* Shared shell pieces reused by every migrated Yarn screen: the full
   real nav item list (built once here instead of copy-pasted per page),
   the sidebar footer (user chip + switch business / sign out), and a
   couple of small formatters. Each page's own script builds its own
   content area and calls window.KhatayDS.mountShell(...). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Icon, Wordmark } = DS;
  const { SidebarNav } = DS;
  const h = React.createElement;

  function money(n) {
    return "Rs " + Math.round(n || 0).toLocaleString("en-PK");
  }

  function plural(n, singular, pluralWord) {
    return n === 1 ? singular : (pluralWord || singular + "s");
  }

  /* Data-entry forms (Purchase & Sale, Receipt & Payment, the Kiryana/
     Hardware sale/purchase line tables, etc.) get typed fast, row after
     row - e.g. Qty then Rate then the next row's Qty - and users expect
     Enter to move to the next field the way it does in Excel/older
     desktop entry software, not just Tab. Attach as onKeyDown on a
     plain text/number <input> (not on a Combobox's search input, a
     search bar, or the barcode scanner - those already have their own
     meaning for Enter). Finds the next focusable field in the same
     <form>, in DOM order, and focuses (and selects the text of) it
     instead of letting Enter submit the form. */
  function focusNextOnEnter(e) {
    if (e.key !== "Enter") return;
    const form = e.currentTarget.form;
    if (!form) return;
    e.preventDefault();
    const focusable = Array.from(
      form.querySelectorAll('input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])')
    ).filter((el) => el.offsetParent !== null);
    const idx = focusable.indexOf(e.currentTarget);
    if (idx > -1 && idx < focusable.length - 1) {
      const next = focusable[idx + 1];
      next.focus();
      if (next.select) next.select();
    }
  }

  /* Builds an Edit-transaction URL that carries the current page (path +
     query string) as return_to, so /transaction/<id>/edit's Save button
     sends the user back to whichever list/filter they were on instead
     of always falling back to the dashboard - matching the old
     `url_for('edit_transaction', ..., return_to=request.full_path)`
     behavior from every pre-migration entry screen. */
  function editUrlWithReturn(base, id) {
    return base.replace("/0/", "/" + id + "/") + "?return_to=" + encodeURIComponent(window.location.pathname + window.location.search);
  }

  // csrf_token() rendered once per page - every form built by page
  // scripts should spread {csrfToken} into a hidden input rather than
  // relying on the old base.html's DOM-scanning auto-injector, which
  // these standalone React pages don't include.
  function CsrfField() {
    return h("input", { type: "hidden", name: "csrf_token", defaultValue: window.__PAGE__.csrfToken });
  }

  function buildYarnNavItems(P, activeId) {
    const items = [
      { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", href: P.nav.dashboard },
      { section: "Master Data" },
      { id: "parties", label: "Parties", icon: "users", href: P.nav.parties },
      { id: "quality", label: "Quality / Items", icon: "boxes", href: P.nav.quality },
    ];
    if (P.isAdmin) {
      items.push({ id: "import", label: "Import Data", icon: "upload", href: P.nav.dataImport });
    }
    items.push(
      { section: "Entry" },
      { id: "transactions", label: "Purchase & Sale", icon: "file-plus-2", href: P.nav.transactions },
      { id: "bookings", label: "Bookings", icon: "calendar-check", href: P.nav.bookings },
      { id: "recovery", label: "Receipt & Payment", icon: "banknote", href: P.nav.recovery },
      { id: "capital-expense", label: "Capital & Expense", icon: "landmark", href: P.nav.capitalExpense },
      { section: "Reports" },
      { id: "report-ledger", label: "Party Ledger", icon: "book-user", href: P.nav.reportLedger },
      { id: "report-quality-ledger", label: "Purchase/Sale Ledger", icon: "notebook-text", href: P.nav.reportQualityLedger },
      { id: "report-receivable", label: "Receivable Ledger", icon: "wallet", href: P.nav.reportReceivable },
      { id: "report-payable", label: "Payable Ledger", icon: "hand-coins", href: P.nav.reportPayable },
      { id: "report-brokerage", label: "Brokerage", icon: "percent", href: P.nav.reportBrokerage },
      { id: "report-cashbook", label: "Cash Book", icon: "book-open-text", href: P.nav.reportCashbook },
      { id: "report-profit", label: "Profit & Capital", icon: "trending-up", href: P.nav.reportProfit },
      { id: "report-stock", label: "Stock", icon: "package", href: P.nav.reportStock },
      { id: "report-trial-balance", label: "Trial Balance", icon: "scale", href: P.nav.reportTrialBalance },
      { id: "report-balance-sheet", label: "Balance Sheet", icon: "landmark", href: P.nav.reportBalanceSheet },
      { section: "Account" }
    );
    if (P.isAdmin) {
      items.push({ id: "team", label: "Team", icon: "user-cog", href: P.nav.team });
    }
    items.push(
      { id: "settings", label: "Settings", icon: "settings-2", href: P.nav.settings },
      { id: "backup", label: "Download Backup", icon: "download", href: P.nav.backup },
      { id: "backup-history", label: "Backup History", icon: "history", href: P.nav.backupHistory }
    );
    return items.map((it) => (it.section ? it : Object.assign({}, it, { active: it.id === activeId })));
  }

  function SidebarFooter({ hideSwitchBusiness } = {}) {
    const P = window.__PAGE__;
    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "8px" } },
      h(
        "div",
        { style: { display: "flex", alignItems: "center", gap: "8px" } },
        h(
          "span",
          {
            style: {
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "var(--indigo-50)",
              color: "var(--indigo-700)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "12px",
              fontWeight: "var(--fw-bold)",
              flex: "0 0 auto",
            },
          },
          P.userInitial
        ),
        h(
          "span",
          {
            style: {
              fontSize: "13px",
              color: "var(--text-body)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            },
          },
          P.userName
        )
      ),
      h(
        "div",
        { style: { display: "flex", gap: "10px", fontSize: "12.5px" } },
        hideSwitchBusiness
          ? null
          : [h("a", { key: "switch", href: P.businessSelectUrl }, "Switch business"), h("span", { key: "sep", style: { color: "var(--border-strong)" } }, "·")],
        h("a", { href: P.logoutUrl }, "Sign out")
      )
    );
  }

  const FLASH_TONE = { success: "ok", error: "danger" };

  /* Surfaces Flask's flash() messages (the app's only feedback mechanism
     for every mutation - "Party added.", "Can't delete...", etc.) as
     Toasts. Without this, every migrated page would silently swallow
     that feedback, since these standalone React pages don't render the
     old base.html's flash-message markup. Reads window.__PAGE__.flashes,
     injected once by _v2_page_data.html - [[category, message], ...]
     exactly as Flask's get_flashed_messages(with_categories=true)
     returns it. */
  function FlashToasts() {
    const { Toast } = DS;
    const flashes = (window.__PAGE__ && window.__PAGE__.flashes) || [];
    const [visible, setVisible] = React.useState(flashes.map((_, i) => i));
    React.useEffect(() => {
      const timers = visible.map((i) => setTimeout(() => dismiss(i), 5000));
      return () => timers.forEach(clearTimeout);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    function dismiss(i) {
      setVisible((v) => v.filter((x) => x !== i));
    }
    if (!flashes.length) return null;
    return h(
      "div",
      { style: { position: "absolute", bottom: 24, right: 28, zIndex: 80, display: "flex", flexDirection: "column", gap: "10px" } },
      visible.map((i) =>
        h(Toast, {
          key: i,
          tone: FLASH_TONE[flashes[i][0]] || "info",
          title: flashes[i][1],
          onDismiss: () => dismiss(i),
        })
      )
    );
  }

  function buildKiryanaNavItems(P, activeId) {
    const items = [
      { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", href: P.nav.dashboard },
      { section: "Kiryana" },
      { id: "inventory", label: "Inventory", icon: "boxes", href: P.nav.inventory },
      { id: "sales", label: "Sale Book", icon: "receipt", href: P.nav.sales },
      { id: "purchases", label: "Purchase List", icon: "shopping-cart", href: P.nav.purchases },
      { id: "returns", label: "Returns", icon: "undo-2", href: P.nav.returns },
      { id: "cashbook", label: "Cash Book", icon: "book-open-text", href: P.nav.cashbook },
      { id: "ledger", label: "Ledger", icon: "book-user", href: P.nav.ledger },
      { id: "expenses", label: "Expenses", icon: "receipt-text", href: P.nav.expenses },
    ];
    return items.map((it) => (it.section ? it : Object.assign({}, it, { active: it.id === activeId })));
  }

  function buildHardwareNavItems(P, activeId) {
    const items = [
      { id: "dashboard", label: "Dashboard", icon: "layout-dashboard", href: P.nav.dashboard },
      { section: "Hardware" },
      { id: "inventory", label: "Inventory", icon: "boxes", href: P.nav.inventory },
      { id: "parties", label: "Customers & Suppliers", icon: "users", href: P.nav.parties },
      { id: "quotations", label: "Quotations", icon: "file-text", href: P.nav.quotations },
      { id: "sales", label: "Sale Book", icon: "receipt", href: P.nav.sales },
      { id: "purchases", label: "Purchase List", icon: "shopping-cart", href: P.nav.purchases },
      { id: "returns", label: "Returns", icon: "undo-2", href: P.nav.returns },
      { id: "cashbook", label: "Cash Book", icon: "book-open-text", href: P.nav.cashbook },
      { id: "ledger", label: "Ledger", icon: "book-user", href: P.nav.ledger },
      { id: "expenses", label: "Expenses", icon: "receipt-text", href: P.nav.expenses },
    ];
    return items.map((it) => (it.section ? it : Object.assign({}, it, { active: it.id === activeId })));
  }

  /* The platform super-admin panel's nav - a flat 3-link list (no
     section labels, no company-scoped items) since this area only
     manages tenant companies/subscriptions/users at the platform
     level, never a single company's own business data (see
     design-brief.md's explicit "no impersonation" scoping). */
  function buildAdminNavItems(P, activeId) {
    const items = [
      { id: "companies", label: "Companies", icon: "building-2", href: P.nav.companies },
      { id: "subscriptions", label: "Subscriptions", icon: "credit-card", href: P.nav.subscriptions },
      { id: "changePassword", label: "Change Password", icon: "key-round", href: P.nav.changePassword },
    ];
    return items.map((it) => Object.assign({}, it, { active: it.id === activeId }));
  }

  /* Renders the standard [SidebarNav | Topbar + content] frame and
     mounts it into #root. `activeId` highlights the matching sidebar
     item; `topbar` is the props object passed straight to <Topbar>;
     `content` is the page body (already built by the caller).
     `navItems` lets a non-Yarn vertical (Kiryana, Hardware, the
     super-admin panel) supply its own sidebar list - defaults to the
     Yarn nav when omitted. `hideSwitchBusiness` drops the footer's
     "Switch business" link - the super-admin panel has no tenant
     company to switch away from (their session is never attached to
     one), so only "Sign out" applies there. */
  function mountShell({ activeId, topbar, content, navItems, hideSwitchBusiness }) {
    const P = window.__PAGE__;
    const { Topbar } = DS;
    const tree = h(
      "div",
      { style: { display: "flex", height: "100%", background: "var(--surface-app)", fontFamily: "var(--font-sans)", position: "relative" } },
      h(SidebarNav, {
        value: activeId,
        header: h(Wordmark, { size: "sm" }),
        items: navItems || buildYarnNavItems(P, activeId),
        footer: h(SidebarFooter, { hideSwitchBusiness: hideSwitchBusiness }),
      }),
      h(
        "div",
        { style: { flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflowY: "auto" } },
        h(Topbar, topbar),
        h(
          "div",
          {
            style: {
              padding: "24px 28px 40px",
              display: "flex",
              flexDirection: "column",
              gap: "22px",
              maxWidth: 1180,
              width: "100%",
              margin: "0 auto",
            },
          },
          content
        )
      ),
      h(FlashToasts)
    );
    ReactDOM.createRoot(document.getElementById("root")).render(tree);
  }

  /* The centered, sidebar-less shell for pre-auth screens (Login,
     Forgot Password, Reset Password) - these run before g.user/g.company
     exist, so they use _v2_auth_page_data.html (csrfToken + flashes
     only) instead of the full _v2_page_data.html, and never call
     buildYarnNavItems/mountShell. */
  function mountAuthShell({ title, subtitle, content, maxWidth = 400 }) {
    const { Wordmark } = DS;
    const tree = h(
      "div",
      { style: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", background: "var(--surface-app)", fontFamily: "var(--font-sans)", padding: "24px", position: "relative" } },
      h(
        "div",
        { style: { width: "100%", maxWidth: maxWidth, display: "flex", flexDirection: "column", gap: "22px" } },
        h(
          "div",
          { style: { textAlign: "center", display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" } },
          h(Wordmark, { size: "md" }),
          title ? h("h1", { style: { fontSize: "var(--text-h2-size)", fontWeight: "var(--text-h2-weight)", color: "var(--text-heading)", margin: 0 } }, title) : null,
          subtitle ? h("p", { style: { fontSize: "13.5px", color: "var(--text-subtle)", margin: 0, textAlign: "center" } }, subtitle) : null
        ),
        content
      ),
      h(FlashToasts)
    );
    ReactDOM.createRoot(document.getElementById("root")).render(tree);
  }

  const PARTY_TYPES = ["Customer", "Supplier", "Broker", "Expense", "Bank"];

  /* Shared Name/Type/City/Phone/NTN/STN/Credit Limit/Opening Balance/
     Address/Brokerage fields, used by both the Add Party dialog (Parties
     list screen) and the Edit Party page - same field set, same names,
     so both post to their respective existing routes unchanged. Pass an
     existing `party` object to prefill (Edit); omit/null for a blank
     Add form. */
  function PartyFormFields({ party }) {
    const { Input, Select, Reveal } = DS;
    const [partyType, setPartyType] = React.useState((party && party.party_type) || "Customer");
    const isBroker = partyType === "Broker";
    const grid2 = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" };
    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "16px" } },
      h(
        "div",
        { style: grid2 },
        h(Input, { name: "name", label: "Name", required: true, defaultValue: party && party.name, placeholder: "e.g. Al-Falah Traders" }),
        h(Select, {
          name: "party_type",
          label: "Type",
          options: PARTY_TYPES,
          value: partyType,
          onChange: (e) => setPartyType(e.target.value),
        })
      ),
      h(
        Reveal,
        { show: isBroker },
        h(
          "div",
          {
            style: {
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
              padding: "14px 16px",
              background: "var(--surface-brand-soft)",
              border: "1px solid var(--indigo-100)",
              borderRadius: "var(--radius-md)",
            },
          },
          h(Select, {
            name: "brokerage_type",
            label: "Brokerage Rate Type",
            options: [
              { value: "percentage", label: "Percentage of sale amount" },
              { value: "per_unit", label: "Fixed rate per unit/bag" },
            ],
            defaultValue: (party && party.brokerage_type) || "percentage",
          }),
          h(Input, {
            name: "brokerage_rate",
            label: "Brokerage Rate",
            type: "number",
            step: "0.01",
            placeholder: "e.g. 1.5 or 50",
            defaultValue: party && party.brokerage_rate,
          })
        )
      ),
      h(
        "div",
        { style: grid2 },
        h(Input, { name: "city", label: "City", defaultValue: party && party.city, placeholder: "e.g. Lahore" }),
        h(Input, { name: "phone", label: "Phone", icon: "phone", defaultValue: party && party.phone, placeholder: "03XX-XXXXXXX" })
      ),
      h(
        "div",
        { style: grid2 },
        h(Input, { name: "ntn", label: "NTN", defaultValue: party && party.ntn, placeholder: "National Tax No." }),
        h(Input, { name: "stn", label: "STN", defaultValue: party && party.stn, placeholder: "Sales Tax No." })
      ),
      h(
        "div",
        { style: grid2 },
        h(Input, { name: "credit_limit", label: "Credit Limit", prefix: "Rs", type: "number", step: "0.01", defaultValue: (party && party.credit_limit) || 0 }),
        h(Input, { name: "opening_balance", label: "Opening Balance", prefix: "Rs", type: "number", step: "0.01", defaultValue: (party && party.opening_balance) || 0 })
      ),
      h(
        "div",
        { style: { display: "flex", flexDirection: "column", gap: "6px" } },
        h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Address"),
        h("textarea", {
          name: "address",
          defaultValue: party && party.address,
          rows: 2,
          placeholder: "Street, area, landmark",
          style: {
            resize: "vertical",
            minHeight: 56,
            padding: "10px 12px",
            fontFamily: "var(--font-sans)",
            fontSize: "14px",
            color: "var(--text-heading)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-control)",
            boxShadow: "var(--shadow-xs)",
            outline: "none",
            boxSizing: "border-box",
          },
        })
      )
    );
  }

  /* DS.Combobox is a controlled UI-only component - it has no
     form-serializable <input name=...> of its own (its visible <input>
     only exists while the dropdown is open, and holds the search text,
     not the selected value). Every screen that needs a searchable
     party/item/broker picker inside a real <form> that must actually
     post the selected id needs this wrapper: it keeps a hidden input in
     sync with the Combobox's selection so plain form submission (no JS
     fetch) carries the right value, exactly like a native <select
     name=...> would. `onPick(value, option)` is called with the full
     matching option object (not just the id) so callers can read extra
     fields they stashed on it, e.g. an item's sale_rate for
     rate-autofill. */
  /* `quickAddUrl` (optional) turns on Combobox's built-in allowCreate:
     typing something with no match offers "+ Add ... as a new
     <entityLabel>", which POSTs {name: <typed text>, ...extraCreateFields}
     to that URL (same JSON contract as the old searchable-select.js's
     data-quick-add-url - {ok, id, name, ...}) and, on success, adds the
     result to this field's own option list and selects it - without the
     caller's original `options` array (server-rendered once at page
     load) ever needing to change. */
  function ComboboxField({ name, label, options, defaultValue, required, placeholder, hint, onPick, quickAddUrl, entityLabel, extraCreateFields }) {
    const { Combobox } = DS;
    const [localOptions, setLocalOptions] = React.useState(options);
    const [value, setValue] = React.useState(defaultValue != null ? String(defaultValue) : "");

    function handleCreate(text) {
      const body = new URLSearchParams(Object.assign({ name: text }, extraCreateFields || {}));
      fetch(quickAddUrl, { method: "POST", body: body, credentials: "same-origin", headers: { "X-CSRFToken": window.__PAGE__.csrfToken } })
        .then((r) => r.json())
        .then((data) => {
          if (!data.ok) {
            window.alert(data.error || "Could not add that.");
            return;
          }
          const opt = Object.assign({}, data, { value: String(data.id), label: data.name });
          setLocalOptions((opts) => opts.concat([opt]));
          setValue(opt.value);
          if (onPick) onPick(opt.value, opt);
        })
        .catch(() => window.alert("Could not reach the server - try again."));
    }

    return h(
      "div",
      { style: { position: "relative" } },
      h("input", { type: "hidden", name: name, value: value }),
      h(Combobox, {
        label: label,
        options: localOptions,
        required: required,
        placeholder: placeholder,
        hint: hint,
        value: value,
        allowCreate: !!quickAddUrl,
        entityLabel: entityLabel || "entry",
        onCreate: quickAddUrl ? handleCreate : undefined,
        onChange: (v) => {
          setValue(v);
          if (onPick) onPick(v, localOptions.find((o) => String(o.value) === String(v)));
        },
      })
    );
  }

  /* A grouped, subtotaled table for the reports that bucket rows under
     a party/broker (Receivable, Payable, Brokerage ledgers) - DS.DataTable
     is flat-rows-only, so this hand-rolls the same visual language
     (sunken header, var(--row-height) rows, border-subtle dividers) with
     a bold group-header row (the group's label + its subtotal, placed
     under whichever column `subtotalKey` names) followed by that
     group's rows, each indented one notch under the first column -
     matching the old pages' "party-row" header + indented-rows pattern.
     `columns` takes the same shape as DataTable's (key/label/align/
     numeric/render). `groups` is [{label, subtotal, rows}, ...]. */
  function GroupedTable({ columns, groups, subtotalKey }) {
    const subIdx = columns.findIndex((c) => c.key === subtotalKey);
    const afterSpan = columns.length - subIdx - 1;
    const cellStyle = (align) => ({ padding: "0 14px", textAlign: align || "left", verticalAlign: "middle" });
    return h(
      "table",
      { style: { width: "100%", borderCollapse: "collapse", fontSize: "var(--text-body-size)" } },
      h(
        "thead",
        null,
        h(
          "tr",
          { style: { height: "38px", background: "var(--surface-sunken)" } },
          columns.map((c) =>
            h(
              "th",
              { key: c.key, style: { ...cellStyle(c.align), height: "38px", fontSize: "var(--text-label-size)", fontWeight: "var(--fw-semibold)", color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)", whiteSpace: "nowrap" } },
              c.label
            )
          )
        )
      ),
      h(
        "tbody",
        null,
        groups.map((g, gi) =>
          h(
            React.Fragment,
            { key: gi },
            h(
              "tr",
              { style: { height: "var(--row-height)", background: "var(--surface-sunken)", borderBottom: "1px solid var(--border-subtle)" } },
              h("td", { colSpan: subIdx, style: { ...cellStyle(), fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, g.label),
              h("td", { style: { ...cellStyle(columns[subIdx].align), fontWeight: "var(--fw-bold)", color: "var(--text-heading)" }, className: "tabular" }, money(g.subtotal)),
              afterSpan > 0 ? h("td", { colSpan: afterSpan }) : null
            ),
            g.rows.map((r, ri) =>
              h(
                "tr",
                { key: ri, style: { height: "var(--row-height)", borderBottom: "1px solid var(--border-subtle)" } },
                columns.map((c, ci) =>
                  h(
                    "td",
                    { key: c.key, className: c.numeric ? "tabular" : undefined, style: { ...cellStyle(c.align), paddingLeft: ci === 0 ? "26px" : undefined, color: c.emphasis ? "var(--text-heading)" : "var(--text-body)", fontWeight: c.emphasis ? "var(--fw-medium)" : "var(--fw-regular)" } },
                    c.render ? c.render(r) : r[c.key]
                  )
                )
              )
            )
          )
        )
      )
    );
  }

  /* Barcode scanning for Kiryana Sale/Purchase entry - ported from the
     old static/js/barcode-scanner.js. Two independent scan sources feed
     the same onScan(code) callback: a plain text input for USB/Bluetooth
     handheld scanners (they "type" the code then send Enter - just keep
     this focused before scanning), and a native BarcodeDetector-based
     camera scanner (Chrome/Edge/Android only - the button hides itself
     when the API isn't available, same as before, rather than show a
     control that would silently fail e.g. on Safari/iOS). */
  function BarcodeScanInput({ onScan }) {
    const { Input, Button } = DS;
    const [code, setCode] = React.useState("");
    const [scanning, setScanning] = React.useState(false);
    const [cameraError, setCameraError] = React.useState("");
    const videoRef = React.useRef(null);
    const streamRef = React.useRef(null);
    const detectingRef = React.useRef(false);
    const hasCameraApi = typeof window !== "undefined" && "BarcodeDetector" in window;

    function stopCamera() {
      detectingRef.current = false;
      if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setScanning(false);
    }

    async function scanLoop(detector) {
      if (!detectingRef.current || !videoRef.current) return;
      try {
        const codes = await detector.detect(videoRef.current);
        if (codes.length) {
          const value = codes[0].rawValue;
          stopCamera();
          onScan(value);
          return;
        }
      } catch (err) {
        // transient decode errors happen constantly while aiming - keep trying
      }
      requestAnimationFrame(() => scanLoop(detector));
    }

    async function startCamera() {
      setCameraError("");
      const detector = new window.BarcodeDetector();
      try {
        streamRef.current = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      } catch (err) {
        setCameraError("Could not access the camera - check permissions.");
        return;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = streamRef.current;
        await videoRef.current.play();
      }
      detectingRef.current = true;
      setScanning(true);
      scanLoop(detector);
    }

    React.useEffect(() => () => stopCamera(), []);

    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "10px" } },
      h(
        "div",
        { style: { display: "flex", gap: "10px", alignItems: "end" } },
        h(Input, {
          label: "Scan barcode",
          value: code,
          onChange: (e) => setCode(e.target.value),
          onKeyDown: (e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              const c = code.trim();
              setCode("");
              if (c) onScan(c);
            }
          },
          placeholder: "Scan or type a barcode, then Enter…",
          containerStyle: { flex: 1 },
        }),
        hasCameraApi ? h(Button, { type: "button", variant: "secondary", icon: "camera", onClick: () => (scanning ? stopCamera() : startCamera()) }, scanning ? "Stop Camera" : "Scan with Camera") : null
      ),
      scanning
        ? h(
            "div",
            { style: { maxWidth: 360 } },
            h("video", { ref: videoRef, playsInline: true, muted: true, style: { width: "100%", display: "block", borderRadius: "var(--radius-md)" } })
          )
        : null,
      cameraError ? h("p", { style: { color: "var(--red-600)", fontSize: "12.5px", margin: 0 } }, cameraError) : null
    );
  }

  /* The collapsible "Recent Sales/Purchases/Returns" list shared by
     Kiryana's Sale Book, Purchase List, and Returns screens - one row
     per invoice (db.kiryana_list_invoices already groups same-invoice
     lines together, fixing the old per-line-row confusion for a
     multi-item bill), click a row to expand its line items, each with
     its own Print/Edit/Delete. `urlFor(base, id)` replacement is the
     caller's job via the *UrlBase props (same "/0/" placeholder pattern
     used everywhere else) so this stays agnostic of exact route names. */
  function InvoiceList({ title, invoices, emptyIcon, emptyMessage, printUrlBase, editUrlBase, deleteUrlBase, canEdit, isAdmin, renderRowExtra }) {
    const { Card, EmptyState, IconButton, Badge } = DS;
    const [open, setOpen] = React.useState({});
    function urlFor(base, id) {
      return base.replace("/0/", "/" + id + "/").replace("/0", "/" + id);
    }
    if (!invoices || invoices.length === 0) {
      return h(Card, { title: title, padding: "none" }, h(EmptyState, { icon: emptyIcon, title: emptyMessage }));
    }
    return h(
      Card,
      { title: title, padding: "none" },
      h(
        "div",
        null,
        invoices.map((inv, i) => {
          const key = inv.invoice_no != null ? "inv-" + inv.invoice_no : "single-" + inv.lines[0].id;
          const isOpen = !!open[key];
          const itemSummary = inv.lines.map((l) => l.item).join(", ") + (inv.lines.length > 1 ? " (" + inv.lines.length + " items)" : "");
          return h(
            "div",
            { key: key, style: { borderBottom: i < invoices.length - 1 ? "1px solid var(--border-subtle)" : "none" } },
            h(
              "div",
              {
                onClick: () => setOpen((o) => Object.assign({}, o, { [key]: !o[key] })),
                style: { display: "flex", alignItems: "center", gap: "12px", padding: "12px var(--gutter-card)", cursor: "pointer", background: isOpen ? "var(--surface-sunken)" : "transparent" },
              },
              h(DS.Icon, { name: isOpen ? "chevron-down" : "chevron-right", size: 15, color: "var(--text-subtle)" }),
              h("div", { style: { flex: "0 0 110px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, inv.invoice),
              h("div", { style: { flex: "0 0 90px", fontSize: "13px", color: "var(--text-subtle)" } }, inv.date),
              h("div", { style: { flex: "0 0 140px", fontSize: "13.5px" } }, inv.party || "Walk-in"),
              h("div", { style: { flex: 1, minWidth: 0, fontSize: "13.5px", color: "var(--text-subtle)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, itemSummary),
              h("div", { style: { flex: "0 0 90px", textAlign: "right", fontWeight: "var(--fw-semibold)" }, className: "tabular" }, money(inv.total_amount)),
              inv.mode && inv.mode !== "N/A" ? h("div", { style: { flex: "0 0 70px" } }, h(Badge, { tone: inv.mode === "Credit" ? "warn" : "ok" }, inv.mode)) : h("div", { style: { flex: "0 0 70px" } }),
              renderRowExtra ? renderRowExtra(inv) : null,
              h(IconButton, {
                icon: "printer",
                label: "Print " + inv.invoice,
                size: "sm",
                onClick: (e) => {
                  e.stopPropagation();
                  window.open(urlFor(printUrlBase, inv.lines[0].id), "_blank");
                },
              })
            ),
            isOpen
              ? h(
                  "div",
                  { style: { padding: "0 var(--gutter-card) 12px 40px" } },
                  h(
                    "table",
                    { style: { width: "100%", borderCollapse: "collapse", fontSize: "13px" } },
                    h(
                      "thead",
                      null,
                      h(
                        "tr",
                        null,
                        ["Item", "Qty", "Rate", "Amount", ""].map((l) => h("th", { key: l, style: { textAlign: l === "Amount" || l === "Qty" || l === "Rate" ? "right" : "left", padding: "4px 8px", color: "var(--text-subtle)", fontWeight: "var(--fw-medium)" } }, l))
                      )
                    ),
                    h(
                      "tbody",
                      null,
                      inv.lines.map((line) =>
                        h(
                          "tr",
                          { key: line.id, style: { borderTop: "1px solid var(--border-subtle)" } },
                          h("td", { style: { padding: "4px 8px" } }, line.item || "—"),
                          h("td", { style: { padding: "4px 8px", textAlign: "right" } }, line.qty),
                          h("td", { style: { padding: "4px 8px", textAlign: "right" } }, money(line.rate)),
                          h("td", { style: { padding: "4px 8px", textAlign: "right" } }, money(line.amount)),
                          h(
                            "td",
                            { style: { padding: "4px 8px", textAlign: "right", whiteSpace: "nowrap" } },
                            canEdit
                              ? h(IconButton, {
                                  icon: "pencil",
                                  label: "Edit",
                                  size: "sm",
                                  onClick: () => (window.location.href = editUrlWithReturn(editUrlBase, line.id)),
                                })
                              : null,
                            isAdmin
                              ? h(
                                  "form",
                                  {
                                    method: "post",
                                    action: urlFor(deleteUrlBase, line.id),
                                    style: { display: "inline" },
                                    onSubmit: (e) => {
                                      if (!window.confirm("Delete this entry?")) e.preventDefault();
                                    },
                                  },
                                  h(CsrfField, null),
                                  h(IconButton, { icon: "trash-2", label: "Delete", size: "sm", type: "submit" })
                                )
                              : null
                          )
                        )
                      )
                    )
                  )
                )
              : null
          );
        })
      )
    );
  }

  /* The "Print / Save PDF" + "Export to Excel" pair every report screen
     ends with. Pass the base url_for(...) URL for each (or null to omit
     that button, e.g. Brokerage has no PDF export) plus the current
     filter values as `params` - they're appended as a query string so
     the export carries the same date/party/search filter the on-screen
     report is showing, matching the old pages' url_for(..., **filters)
     links. */
  function ExportButtons({ pdfUrl, excelUrl, params }) {
    const { Button } = DS;
    function withParams(base) {
      const url = new URL(base, window.location.origin);
      Object.entries(params || {}).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
      });
      return url.pathname + url.search;
    }
    return h(
      "div",
      { style: { display: "flex", gap: "8px" } },
      pdfUrl ? h(Button, { icon: "printer", onClick: () => window.open(withParams(pdfUrl), "_blank") }, "Print / Save PDF") : null,
      excelUrl ? h(Button, { variant: "secondary", icon: "download", onClick: () => window.open(withParams(excelUrl), "_blank") }, "Export to Excel") : null
    );
  }

  /* A 2-3 option pill toggle (Sale/Purchase, Cash/Cheque, Dr/Cr, ...) -
     reused across every entry form. Not a form-serializable control on
     its own; pair it with a hidden <input> the way EntryForm etc. do. */
  function Segmented({ options, value, onChange }) {
    return h(
      "div",
      { style: { display: "inline-flex", padding: "3px", gap: "2px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-control)" } },
      options.map((o) => {
        const on = o.value === value;
        return h(
          "button",
          {
            key: o.value,
            type: "button",
            onClick: () => onChange(o.value),
            style: {
              display: "flex", alignItems: "center", justifyContent: "center", gap: "7px", flex: 1, height: "32px", padding: "0 16px",
              border: "none", borderRadius: "var(--radius-sm)", cursor: "pointer",
              background: on ? "var(--surface-card)" : "transparent", boxShadow: on ? "var(--shadow-xs)" : "none",
              color: on ? "var(--text-heading)" : "var(--text-muted)", fontFamily: "var(--font-sans)", fontSize: "14px",
              fontWeight: on ? "var(--fw-semibold)" : "var(--fw-medium)", transition: "var(--transition-control)",
            },
          },
          o.label
        );
      })
    );
  }

  window.KhatayDS = { money, plural, buildYarnNavItems, buildKiryanaNavItems, buildHardwareNavItems, buildAdminNavItems, SidebarFooter, mountShell, mountAuthShell, CsrfField, PartyFormFields, PARTY_TYPES, ComboboxField, Segmented, editUrlWithReturn, ExportButtons, GroupedTable, InvoiceList, BarcodeScanInput, focusNextOnEnter };
})();
