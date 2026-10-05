/* Edit Entry - wired to app.py's kiryana_ledger_transaction_edit()
   route. Item, party, and mode aren't editable here (shown read-only)
   - only date/qty/rate/description can change; stock is auto-adjusted
   server-side by the qty delta (db.kiryana_update_transaction). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Banner } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const txn = P.txn;

  const TYPE_LABEL = { SALE: "Sale", PURCHASE: "Purchase", SALE_RETURN: "Sale Return", PURCHASE_RETURN: "Purchase Return" };

  function Root() {
    return h(
      Card,
      { title: "Edit " + (TYPE_LABEL[txn.txn_type] || txn.txn_type) },
      h(Banner, { tone: "info", style: { marginBottom: "16px" } }, "Item, party, and mode aren't editable here - delete and re-enter if any of those need to change. Stock is adjusted automatically to match any quantity change."),
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "return_to", value: P.returnTo || "" }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Input, { label: "Party", value: (P.party && P.party.name) || "Walk-in", disabled: true }),
          h(Input, { label: "Mode", value: txn.mode, disabled: true })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: txn.date, required: true }),
          h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty", defaultValue: txn.qty, required: true }),
          h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate", defaultValue: txn.rate, required: true })
        ),
        h(Input, { label: "Description", name: "description", defaultValue: txn.description || "", containerStyle: { marginTop: "16px" } }),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.returnTo || P.nav.ledger) }, "Cancel")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "ledger",
    topbar: { breadcrumb: "Kiryana", title: "Edit Entry" },
    content: h(Root),
    navItems: window.KhatayDS.buildKiryanaNavItems(P, "ledger"),
  });
})();
