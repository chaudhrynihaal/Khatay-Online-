/* Edit Payment - wired to app.py's hardware_ledger_payment_edit() route.
   Party is fixed (shown read-only) - only date/amount/description can
   change. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const payment = P.payment;

  function Root() {
    return h(
      Card,
      { title: "Edit Payment" },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "return_to", value: P.returnTo || "" }),
        h(Input, { label: "Party", value: (P.party && P.party.name) || "—", disabled: true, containerStyle: { maxWidth: 320, marginBottom: "16px" } }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: payment.date, required: true }),
          h(Input, { label: "Amount", type: "number", step: "0.01", name: "amount", defaultValue: payment.amount, required: true })
        ),
        h(Input, { label: "Description", name: "description", defaultValue: payment.description || "", containerStyle: { marginTop: "16px" } }),
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
    topbar: { breadcrumb: "Hardware", title: "Edit Payment" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "ledger"),
  });
})();
