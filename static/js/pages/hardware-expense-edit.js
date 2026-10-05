/* Edit Expense - wired to app.py's hardware_edit_expense() route. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const expense = P.expense;

  function Root() {
    return h(
      Card,
      { title: "Edit Expense" },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: expense.date, required: true }),
          h(Input, { label: "Category", name: "category", defaultValue: expense.category || "" }),
          h(Input, { label: "Amount", name: "amount", type: "number", step: "0.01", defaultValue: expense.amount, required: true }),
          h(Input, { label: "Description", name: "description", defaultValue: expense.description || "" })
        ),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.nav.expenses) }, "Cancel")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "expenses",
    topbar: { breadcrumb: "Hardware", title: "Edit Expense" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "expenses"),
  });
})();
