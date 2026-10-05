/* Edit Entry - wired to app.py's edit_transaction() route. Reachable
   from every entry screen's Edit action (Purchase & Sale, Receipt &
   Payment, Capital & Expense); which fields show depends on the
   transaction's voucher_type, exactly like the old page's three
   template branches. Submits through a genuine <form method="post">
   back to the same URL; return_to (carried in as a query param by the
   linking screen) sends Save/Cancel back to wherever the user came
   from instead of always landing on the dashboard. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, Input, Select, Banner } = DS;
  const { CsrfField, ComboboxField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const txn = P.txn;
  const vType = P.vType;

  const partyOptions = P.parties.map((p) => ({ value: String(p.id), label: p.name, meta: p.type }));
  const itemOptions = P.items.map((i) => ({ value: String(i.id), label: i.name }));

  const ACTIVE_ID = { SALE: "transactions", PURCHASE: "transactions", RECEIPT: "recovery", PAYMENT: "recovery",
    EXPENSE: "capital-expense", CAPITAL_IN: "capital-expense", CAPITAL_OUT: "capital-expense" };

  function SaleOrPurchaseFields() {
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
        h(Input, { label: "Date", type: "date", name: "date", defaultValue: txn.date, required: true }),
        h(Input, { label: "D.O. No.", name: "do_no", defaultValue: txn.do_no || "" }),
        h(Input, { label: "Broker", name: "broker", defaultValue: txn.broker || "" }),
        h(Input, { label: "Credit Days", name: "credit_days", type: "number", defaultValue: txn.credit_days || 0 })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(180px, 1fr))", gap: "16px", marginTop: "16px" } },
        h(ComboboxField, { name: "party_id", label: "Party", options: partyOptions, required: true, defaultValue: txn.party_id, placeholder: "Search…" }),
        h(ComboboxField, { name: "quality_id", label: "Item / Quality", options: itemOptions, required: true, defaultValue: txn.quality_id, placeholder: "Search…" })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px", marginTop: "16px" } },
        h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty", defaultValue: txn.qty, required: true }),
        h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate", defaultValue: txn.rate, required: true }),
        h(Select, { label: "Mode", name: "mode", options: ["Cash", "Cheque"], defaultValue: txn.cash_or_cheque || "Cash" }),
        h(Input, { label: "Cheque No.", name: "cheque_no", defaultValue: txn.cheque_no || "" })
      ),
      h(Input, { label: "Description", name: "description", defaultValue: txn.description || "", containerStyle: { marginTop: "16px" } })
    );
  }

  function ReceiptOrPaymentFields() {
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
        h(Input, { label: "Date", type: "date", name: "date", defaultValue: txn.date, required: true }),
        h(ComboboxField, { name: "party_id", label: "Party", options: partyOptions, required: true, defaultValue: txn.party_id, placeholder: "Search…" }),
        h(Input, { label: "Amount", type: "number", step: "0.01", name: "amount", defaultValue: txn.amount, required: true })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
        h(Select, { label: "Mode", name: "mode", options: ["Cash", "Cheque"], defaultValue: txn.cash_or_cheque || "Cash" }),
        h(Input, { label: "Cheque No.", name: "cheque_no", defaultValue: txn.cheque_no || "" }),
        h(Input, { label: "Description", name: "description", defaultValue: txn.description || "" })
      ),
      h(
        Banner,
        { tone: "info", style: { marginTop: "16px" } },
        "This entry may have multiple cheque lines attached - editing here only changes the total amount/date/description, not individual cheque lines. Delete and re-enter if you need to change the cheque breakdown."
      )
    );
  }

  function OtherFields() {
    return h(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
      h(Input, { label: "Date", type: "date", name: "date", defaultValue: txn.date, required: true }),
      h(Input, { label: "Amount", type: "number", step: "0.01", name: "amount", defaultValue: txn.amount, required: true }),
      h(Input, { label: "Description", name: "description", defaultValue: txn.description || "" })
    );
  }

  function Root() {
    return h(
      Card,
      { title: "Edit " + vType.replace(/_/g, " ").replace(/\w\S*/g, (t) => t[0].toUpperCase() + t.slice(1).toLowerCase()) },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "return_to", value: P.returnTo || "" }),
        ["SALE", "PURCHASE"].includes(vType)
          ? h(SaleOrPurchaseFields)
          : ["RECEIPT", "PAYMENT"].includes(vType)
          ? h(ReceiptOrPaymentFields)
          : h(OtherFields),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.returnTo || P.nav.dashboard) }, "Cancel")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: ACTIVE_ID[vType] || "dashboard",
    topbar: { breadcrumb: "Entry", title: "Edit " + vType.replace(/_/g, " ") },
    content: h(Root),
  });
})();
