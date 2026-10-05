/* Capital & Expense - wired to app.py's capital_expense() route. Two
   tabs sharing one screen: Home/Office/Zakat expense vouchers, and
   Capital In/Out against the owner's capital account. Each tab posts
   its own real <form> (kind=expense or kind=capital) to the same
   unchanged route. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, IconButton, DataTable, EmptyState, Banner, Input, Select, Tabs, StatCard } = DS;
  const { money, CsrfField, editUrlWithReturn } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function SavedBanner() {
    if (!P.savedVoucher) return null;
    return h(Banner, {
      tone: "ok",
      title: "Saved as " + P.savedVoucher.voucher + " - ready for your next entry.",
      action: h(Button, { size: "sm", variant: "secondary", onClick: () => window.open(urlFor(P.printVoucherUrlBase, P.savedVoucher.id), "_blank") }, "Print This Voucher"),
    });
  }

  function ExpenseForm() {
    return h(
      Card,
      { title: "New expense voucher" },
      h(
        "form",
        { method: "post", action: P.nav.capitalExpense },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "kind", value: "expense" }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(Select, { label: "Category", name: "category", options: ["Home", "Office", "Zakat"], defaultValue: "Home" }),
          h(Input, { label: "Amount", name: "amount", type: "number", step: "0.01", required: true }),
          h(Input, { label: "Description", name: "description" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save Expense"))
      )
    );
  }

  function expenseColumns() {
    return [
      { key: "voucher", label: "Voucher #", emphasis: true },
      { key: "date", label: "Date" },
      { key: "category", label: "Category" },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      { key: "description", label: "Description", render: (r) => r.description || "—" },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, { icon: "printer", label: "Print " + r.voucher, size: "sm", onClick: () => window.open(urlFor(P.printVoucherUrlBase, r.id), "_blank") }),
            P.canEdit
              ? h(IconButton, { icon: "pencil", label: "Edit " + r.voucher, size: "sm", onClick: () => (window.location.href = editUrlWithReturn(P.editTransactionUrlBase, r.id)) })
              : null,
            P.isAdmin
              ? h(
                  "form",
                  {
                    method: "post",
                    action: urlFor(P.deleteTransactionUrlBase, r.id),
                    onSubmit: (e) => {
                      if (!window.confirm("Delete this entry?")) e.preventDefault();
                    },
                  },
                  h(CsrfField, null),
                  h(IconButton, { icon: "trash-2", label: "Delete " + r.voucher, size: "sm", type: "submit" })
                )
              : null
          ),
      },
    ];
  }

  function ExpensePanel() {
    const expenses = P.expenses || [];
    return h(
      React.Fragment,
      null,
      h(ExpenseForm),
      h(
        Card,
        { title: "Recent expenses", padding: "none" },
        expenses.length === 0
          ? h(EmptyState, { icon: "receipt", title: "No expenses yet" })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: expenseColumns(), rows: expenses }))
      )
    );
  }

  function CapitalForm() {
    return h(
      Card,
      { title: "New capital entry" },
      h(
        "form",
        { method: "post", action: P.nav.capitalExpense },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "kind", value: "capital" }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(Select, {
            label: "Direction",
            name: "direction",
            options: [{ value: "CAPITAL_IN", label: "Capital Introduced (in)" }, { value: "CAPITAL_OUT", label: "Capital Withdrawn (out)" }],
            defaultValue: "CAPITAL_IN",
          }),
          h(Input, { label: "Amount", name: "amount", type: "number", step: "0.01", required: true }),
          h(Input, { label: "Description", name: "description" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save Entry"))
      )
    );
  }

  function capitalColumns() {
    return [
      { key: "voucher", label: "Voucher #", emphasis: true },
      { key: "date", label: "Date" },
      { key: "direction", label: "Direction" },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      { key: "description", label: "Description", render: (r) => r.description || "—" },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) => h(IconButton, { icon: "printer", label: "Print " + r.voucher, size: "sm", onClick: () => window.open(urlFor(P.printVoucherUrlBase, r.id), "_blank") }),
      },
    ];
  }

  function CapitalPanel() {
    const entries = P.capitalEntries || [];
    return h(
      React.Fragment,
      null,
      h(CapitalForm),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Total In", value: money(P.capital.total_in) }),
        h(StatCard, { label: "Total Out", value: money(P.capital.total_out) }),
        h(StatCard, { label: "Net Capital", value: money(P.capital.net_capital) })
      ),
      h(
        Card,
        { title: "Capital history", padding: "none" },
        entries.length === 0
          ? h(EmptyState, { icon: "landmark", title: "No capital entries yet" })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: capitalColumns(), rows: entries }))
      )
    );
  }

  function Root() {
    const [tab, setTab] = React.useState("expense");
    return h(
      React.Fragment,
      null,
      h(SavedBanner),
      h(Tabs, {
        value: tab,
        onChange: setTab,
        items: [
          { id: "expense", label: "Home & Office Expense" },
          { id: "capital", label: "Capital In / Out" },
        ],
      }),
      tab === "expense" ? h(ExpensePanel) : h(CapitalPanel)
    );
  }

  window.KhatayDS.mountShell({
    activeId: "capital-expense",
    topbar: { breadcrumb: "Entry", title: "Capital & Expense" },
    content: h(Root),
  });
})();
