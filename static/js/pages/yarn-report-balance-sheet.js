/* Balance Sheet - wired to app.py's report_balance_sheet() route.
   Assets = Liabilities + Equity, as of today (a real accounting balance
   sheet, not just a party-balance summary) - see db.get_balance_sheet's
   docstring for how each figure is derived and why it always balances. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, DataTable, StatCard, Banner } = DS;
  const { money, ExportButtons } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function lineColumns() {
    return [
      { key: "name", label: "Account", emphasis: true, render: (r) => (r._isTotal ? h("strong", null, r.name) : r.name) },
      { key: "amount", label: "Amount", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._isTotal ? "var(--fw-bold)" : undefined } }, money(r.amount)) },
    ];
  }

  function Section({ title, rows, totalLabel, totalAmount }) {
    const withTotal = rows.concat([{ _isTotal: true, name: totalLabel, amount: totalAmount }]);
    return h(
      Card,
      { title: title, padding: "none" },
      h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: lineColumns(), rows: withTotal }))
    );
  }

  function Root() {
    const bs = P.bs;
    const assetRows = [{ name: "Cash", amount: bs.cash_balance }]
      .concat(bs.receivables.map((r) => ({ name: "Receivable — " + r.name, amount: r.amount })))
      .concat([{ name: "Stock / Inventory", amount: bs.stock_value }]);
    const liabilityRows = bs.payables.length
      ? bs.payables.map((p) => ({ name: "Payable — " + p.name, amount: p.amount }))
      : [{ name: "(none)", amount: 0 }];
    const equityRows = [
      { name: "Capital Account", amount: bs.capital },
      { name: "Opening Balance Equity", amount: bs.opening_balance_equity },
      { name: "Retained Earnings", amount: bs.retained_earnings },
    ];

    const balanced = Math.abs(bs.total_assets - bs.total_liabilities_and_equity) < 0.01;

    return h(
      React.Fragment,
      null,
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl }),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px", marginBottom: "16px" } },
        h(StatCard, { label: "Total Assets", value: money(bs.total_assets) }),
        h(StatCard, { label: "Total Liabilities + Equity", value: money(bs.total_liabilities_and_equity) })
      ),
      balanced
        ? null
        : h(Banner, { tone: "danger", style: { marginBottom: "16px" } }, "Assets don't equal Liabilities + Equity - this shouldn't happen. Please contact support."),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr", gap: "16px" } },
        h(Section, { title: "Assets", rows: assetRows, totalLabel: "TOTAL ASSETS", totalAmount: bs.total_assets }),
        h(Section, { title: "Liabilities", rows: liabilityRows, totalLabel: "TOTAL LIABILITIES", totalAmount: bs.total_liabilities }),
        h(Section, { title: "Equity", rows: equityRows, totalLabel: "TOTAL EQUITY", totalAmount: bs.total_equity })
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-balance-sheet",
    topbar: { breadcrumb: "Reports", title: "Balance Sheet", subtitle: "As of " + P.bs.as_of_date },
    content: h(Root),
  });
})();
