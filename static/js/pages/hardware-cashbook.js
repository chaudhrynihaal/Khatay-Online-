/* Cash Book - wired to app.py's hardware_cashbook() route. Identical
   to Kiryana's Cash Book - same db.hardware_cash_book() shape/logic. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, StatCard, DataTable, EmptyState, Button } = DS;
  const { money } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function columns() {
    return [
      { key: "date", label: "Date" },
      { key: "description", label: "Description" },
      { key: "in_amount", label: "In", numeric: true, align: "right", render: (r) => (r.in_amount ? money(r.in_amount) : "") },
      { key: "out_amount", label: "Out", numeric: true, align: "right", render: (r) => (r.out_amount ? money(r.out_amount) : "") },
      { key: "balance", label: "Balance", numeric: true, align: "right", emphasis: true, render: (r) => money(r.balance) },
    ];
  }

  function Root() {
    const events = P.events || [];
    return h(
      React.Fragment,
      null,
      h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "flex-start" } },
        h("div", { style: { maxWidth: 280, width: "100%" } }, h(StatCard, { label: "Closing Balance", value: money(P.closingBalance), tone: P.closingBalance < 0 ? "danger" : "neutral" })),
        h(Button, { variant: "secondary", icon: "printer", onClick: () => window.print() }, "Print")
      ),
      h(
        Card,
        { padding: "none" },
        events.length === 0
          ? h(EmptyState, { icon: "banknote", title: "No cash movements yet", message: "Record a Cash sale or purchase to see them here." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: events }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "cashbook",
    topbar: { breadcrumb: "Hardware", title: "Cash Book" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "cashbook"),
  });
})();
