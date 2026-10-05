/* Ledger - wired to app.py's kiryana_ledger()/kiryana_ledger_payment()
   routes. A two-column T-account: Sales/Purchases (Dr, credit-mode
   only - cash ones never touch the balance) on the left, Payments &
   Returns (Cr) on the right, each with an Opening Balance/TOTAL row -
   matching db.kiryana_party_ledger's already-computed running balance. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Select, Input, Button, Tabs, DataTable, EmptyState, IconButton } = DS;
  const { money, CsrfField, editUrlWithReturn } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/").replace("/0", "/" + id);
  }

  function switchType(type) {
    const u = new URL(P.nav.ledger, window.location.origin);
    u.searchParams.set("type", type);
    window.location.href = u.pathname + u.search;
  }

  function PartyPicker() {
    return h(
      "form",
      { method: "get", action: P.nav.ledger, style: { display: "flex", gap: "10px" } },
      h("input", { type: "hidden", name: "type", value: P.partyType }),
      h(Select, {
        name: "party_id",
        options: [{ value: "", label: "Select a " + P.partyType.toLowerCase() + "…" }].concat(P.parties.map((p) => ({ value: String(p.id), label: p.name }))),
        defaultValue: P.partyId ? String(P.partyId) : "",
        onChange: (e) => {
          const u = new URL(P.nav.ledger, window.location.origin);
          u.searchParams.set("type", P.partyType);
          if (e.target.value) u.searchParams.set("party_id", e.target.value);
          window.location.href = u.pathname + u.search;
        },
        containerStyle: { minWidth: 280 },
      })
    );
  }

  function explainBalance(party, balance) {
    const isCustomer = party.party_type === "Customer";
    if (Math.abs(balance) < 0.01) return "Settled — nothing owed either way.";
    if (isCustomer) return balance > 0 ? "This customer owes you " + money(balance) + "." : "You owe this customer " + money(Math.abs(balance)) + " (overpaid).";
    return balance > 0 ? "You owe this supplier " + money(balance) + "." : "This supplier owes you " + money(Math.abs(balance)) + " (overpaid).";
  }

  function PaymentForm() {
    return h(
      Card,
      { title: "Record a payment" },
      h(
        "form",
        { method: "post", action: P.paymentUrl, style: { display: "grid", gridTemplateColumns: "1fr 1fr 2fr auto", gap: "10px", alignItems: "end" } },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "party_id", value: P.partyId }),
        h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
        h(Input, { label: "Amount", type: "number", step: "0.01", name: "amount", required: true }),
        h(Input, { label: "Description", name: "description" }),
        h(Button, { type: "submit" }, "Record Payment")
      )
    );
  }

  function drColumns() {
    return [
      { key: "date", label: "Date", render: (r) => (r._total ? "" : r.date) },
      { key: "type", label: "Detail", render: (r) => (r._total ? h("strong", null, "TOTAL") : r.detail || "—") },
      { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => (r._total || r.qty == null ? "" : r.qty) },
      { key: "debit", label: "Amount", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._total ? "var(--fw-bold)" : undefined } }, money(r.debit)) },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          r._total || r._opening
            ? null
            : h(
                "div",
                { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
                P.canEdit ? h(IconButton, { icon: "pencil", label: "Edit", size: "sm", onClick: () => (window.location.href = editUrlWithReturn(P.editTxnUrlBase, r.id)) }) : null,
                P.isAdmin
                  ? h(
                      "form",
                      { method: "post", action: urlFor(P.deleteTxnUrlBase, r.id), style: { display: "inline" }, onSubmit: (e) => { if (!window.confirm("Delete this entry?")) e.preventDefault(); } },
                      h(CsrfField, null),
                      h(IconButton, { icon: "trash-2", label: "Delete", size: "sm", type: "submit" })
                    )
                  : null
              ),
      },
    ];
  }

  function crColumns() {
    return [
      { key: "date", label: "Date", render: (r) => (r._total ? "" : r.date) },
      { key: "type", label: "Type", render: (r) => (r._total ? h("strong", null, "TOTAL") : r.type) },
      { key: "detail", label: "Detail", render: (r) => (r._total ? "" : r.detail || "—") },
      { key: "credit", label: "Amount", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._total ? "var(--fw-bold)" : undefined } }, money(r.credit)) },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) => {
          if (r._total) return null;
          const editUrl = r.kind === "payment" ? editUrlWithReturn(P.editPaymentUrlBase, r.id) : editUrlWithReturn(P.editTxnUrlBase, r.id);
          const deleteUrl = r.kind === "payment" ? urlFor(P.deletePaymentUrlBase, r.id) : urlFor(P.deleteTxnUrlBase, r.id);
          return h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            P.canEdit ? h(IconButton, { icon: "pencil", label: "Edit", size: "sm", onClick: () => (window.location.href = editUrl) }) : null,
            P.isAdmin
              ? h(
                  "form",
                  { method: "post", action: deleteUrl, style: { display: "inline" }, onSubmit: (e) => { if (!window.confirm("Delete this entry?")) e.preventDefault(); } },
                  h(CsrfField, null),
                  h(IconButton, { icon: "trash-2", label: "Delete", size: "sm", type: "submit" })
                )
              : null
          );
        },
      },
    ];
  }

  function LedgerView() {
    const l = P.ledger;
    const party = l.party;
    const drEntries = l.entries.filter((e) => e.kind === "transaction");
    const crEntries = l.entries.filter((e) => e.kind !== "transaction");
    const drRows = [{ _opening: true, date: "", detail: "Opening Balance", debit: party.opening_balance > 0 ? party.opening_balance : 0 }]
      .concat(drEntries)
      .concat([{ _total: true, debit: drEntries.reduce((s, e) => s + e.debit, 0) + (party.opening_balance > 0 ? party.opening_balance : 0) }]);
    const crRows = [{ _opening: true, date: "", type: "Opening Balance", credit: party.opening_balance < 0 ? -party.opening_balance : 0 }]
      .concat(crEntries)
      .concat([{ _total: true, credit: crEntries.reduce((s, e) => s + e.credit, 0) + (party.opening_balance < 0 ? -party.opening_balance : 0) }]);

    return h(
      React.Fragment,
      null,
      h(
        Card,
        null,
        h(
          "div",
          { style: { display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" } },
          h(
            "div",
            null,
            h("div", { style: { fontSize: "16px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, party.name),
            h("div", { style: { fontSize: "13px", color: "var(--text-subtle)" } }, party.phone || "")
          ),
          h(
            "div",
            { style: { textAlign: "right" } },
            h("div", { style: { fontSize: "12px", color: "var(--text-subtle)" } }, "Closing Balance"),
            h("div", { className: "tabular", style: { fontSize: "20px", fontWeight: "var(--fw-bold)", color: l.closing_balance > 0 ? "var(--red-600)" : "var(--text-heading)" } }, money(Math.abs(l.closing_balance)))
          )
        ),
        h("p", { style: { fontSize: "13.5px", color: "var(--text-subtle)", marginTop: "10px" } }, explainBalance(party, l.closing_balance))
      ),
      h(PaymentForm),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" } },
        h(Card, { title: (party.party_type === "Customer" ? "Sales" : "Purchases") + " (Dr)", padding: "none" }, h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: drColumns(), rows: drRows }))),
        h(Card, { title: "Payments & Returns (Cr)", padding: "none" }, h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: crColumns(), rows: crRows })))
      )
    );
  }

  function Root() {
    return h(
      React.Fragment,
      null,
      h(Tabs, { value: P.partyType, onChange: switchType, items: [{ id: "Customer", label: "Customers" }, { id: "Supplier", label: "Suppliers" }] }),
      h(PartyPicker),
      P.ledger
        ? h(LedgerView)
        : P.partyId
        ? h(Card, null, h(EmptyState, { title: "Party not found." }))
        : h(Card, null, h(EmptyState, { icon: "book-open", title: "Select a " + P.partyType.toLowerCase() + " above", message: "See their complete statement with a running balance." }))
    );
  }

  window.KhatayDS.mountShell({
    activeId: "ledger",
    topbar: { breadcrumb: "Kiryana", title: "Ledger" },
    content: h(Root),
    navItems: window.KhatayDS.buildKiryanaNavItems(P, "ledger"),
  });
})();
