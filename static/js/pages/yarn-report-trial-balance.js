/* Trial Balance - wired to app.py's report_trial_balance() route.
   Read-only, no filters. Parties with zero all-time activity and a
   zero opening balance are already excluded server-side. A synthetic
   TOTAL row is appended client-side (its balance = totalDebit -
   totalCredit, computed the same way the old Jinja template did it
   inline rather than as a passed variable). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, DataTable, EmptyState } = DS;
  const { money, ExportButtons } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function columns() {
    return [
      { key: "name", label: "Account", emphasis: true, render: (r) => (r._isTotal ? h("strong", null, "TOTAL") : r.name) },
      { key: "debit", label: "Debit", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._isTotal ? "var(--fw-bold)" : undefined } }, money(r.debit)) },
      { key: "credit", label: "Credit", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._isTotal ? "var(--fw-bold)" : undefined } }, money(r.credit)) },
      { key: "balance", label: "Balance", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._isTotal ? "var(--fw-bold)" : undefined } }, money(r.balance)) },
    ];
  }

  function Root() {
    const rows = P.rows || [];
    const withTotal = rows.length ? rows.concat([{ _isTotal: true, name: "TOTAL", debit: P.totalDebit, credit: P.totalCredit, balance: P.totalDebit - P.totalCredit }]) : rows;
    return h(
      React.Fragment,
      null,
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl }),
      h(
        Card,
        { padding: "none" },
        rows.length === 0
          ? h(EmptyState, { icon: "scale", title: "No activity yet." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: withTotal }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-trial-balance",
    topbar: { breadcrumb: "Reports", title: "Trial Balance" },
    content: h(Root),
  });
})();
