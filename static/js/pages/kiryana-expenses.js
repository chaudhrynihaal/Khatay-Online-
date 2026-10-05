/* Expenses - wired to app.py's kiryana_expenses()/kiryana_edit_expense()/
   kiryana_expense_delete() routes. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, IconButton, StatCard, DataTable, EmptyState } = DS;
  const { money, CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function ExpenseForm() {
    return h(
      Card,
      { title: "Record an expense" },
      h(
        "form",
        { method: "post", action: P.nav.expenses },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(Input, { label: "Category", name: "category", placeholder: "e.g. Rent, Electricity" }),
          h(Input, { label: "Amount", name: "amount", type: "number", step: "0.01", required: true }),
          h(Input, { label: "Description", name: "description" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save Expense"))
      )
    );
  }

  function columns() {
    return [
      { key: "date", label: "Date" },
      { key: "category", label: "Category", render: (r) => r.category || "—" },
      { key: "description", label: "Description", render: (r) => r.description || "—" },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, { icon: "pencil", label: "Edit", size: "sm", onClick: () => (window.location.href = urlFor(P.editExpenseUrlBase, r.id)) }),
            h(
              "form",
              { method: "post", action: urlFor(P.deleteExpenseUrlBase, r.id), style: { display: "inline" }, onSubmit: (e) => { if (!window.confirm("Delete this expense?")) e.preventDefault(); } },
              h(CsrfField, null),
              h(IconButton, { icon: "trash-2", label: "Delete", size: "sm", type: "submit" })
            )
          ),
      },
    ];
  }

  function Root() {
    const expenses = P.expenses || [];
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Total Sales", value: money(P.totalSales) }),
        h(StatCard, { label: "Total Expenses", value: money(P.totalExpenses), tone: P.totalExpenses > 0 ? "danger" : "neutral" }),
        h(StatCard, { label: "Net Profit", value: money(P.netProfit), tone: P.netProfit < 0 ? "danger" : "neutral" })
      ),
      h(ExpenseForm),
      h(
        Card,
        { title: "All expenses", padding: "none" },
        expenses.length === 0
          ? h(EmptyState, { icon: "receipt", title: "No expenses recorded yet." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: expenses }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "expenses",
    topbar: { breadcrumb: "Kiryana", title: "Expenses" },
    content: h(Root),
    navItems: window.KhatayDS.buildKiryanaNavItems(P, "expenses"),
  });
})();
