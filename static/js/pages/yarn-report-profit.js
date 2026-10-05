/* Profit & Capital - wired to app.py's report_profit() route. A
   date-ranged Sales/COGS/Expense breakdown plus an always-all-time
   Capital Account summary (the date filter never touches the capital
   figures, matching db.get_capital_summary being called with no date
   args server-side). The From/To filter is a real GET form so the
   date range lives in the URL, same as the old page. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, StatCard } = DS;
  const { money, ExportButtons } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function DateFilter() {
    return h(
      "form",
      { method: "get", action: P.nav.reportProfit, style: { display: "flex", gap: "10px", alignItems: "end" } },
      h(Input, { label: "From", type: "date", name: "from", defaultValue: P.dateFrom }),
      h(Input, { label: "To", type: "date", name: "to", defaultValue: P.dateTo }),
      h(Button, { type: "submit", variant: "secondary" }, "Refresh"),
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { from: P.dateFrom, to: P.dateTo } })
    );
  }

  function Row({ label, value, emphasis }) {
    return h(
      "div",
      {
        style: {
          display: "flex",
          justifyContent: "space-between",
          padding: emphasis ? "10px 0" : "8px 0",
          borderBottom: "1px solid var(--border-subtle)",
          fontSize: emphasis ? "15px" : "14px",
          fontWeight: emphasis ? "var(--fw-semibold)" : "var(--fw-regular)",
          color: emphasis ? "var(--text-heading)" : "var(--text-body)",
        },
      },
      h("span", null, label),
      h("span", { className: "tabular" }, money(value))
    );
  }

  function Root() {
    const p = P.profit;
    return h(
      React.Fragment,
      null,
      h(DateFilter),
      h(
        Card,
        { title: "Profit for the period" },
        h(
          "div",
          null,
          h(Row, { label: "Total Sales", value: p.total_sales }),
          h(Row, { label: "Total Purchases", value: p.total_purchases }),
          h(Row, { label: "+ Opening Stock Value (at purchase rate)", value: p.opening_stock_value }),
          h(Row, { label: "− Closing Stock Value (at purchase rate)", value: p.closing_stock_value }),
          h(Row, { label: "Cost of Goods Sold", value: p.cogs }),
          h(Row, { label: "Gross Profit (Sales − COGS)", value: p.gross_profit, emphasis: true }),
          h(Row, { label: "Home Expense", value: p.home_expense }),
          h(Row, { label: "Office Expense", value: p.office_expense }),
          h(Row, { label: "Net Profit", value: p.net_profit, emphasis: true })
        )
      ),
      h(
        Card,
        { title: "Capital Account (all-time)", subtitle: "Zakat is a personal draw against capital, not a business expense - it reduces Capital here, not Net Profit above." },
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" } },
          h(StatCard, { label: "Total Introduced", value: money(P.capital.total_in) }),
          h(StatCard, { label: "Total Withdrawn", value: money(P.capital.total_out - P.capital.zakat_total) }),
          h(StatCard, { label: "Zakat Paid", value: money(P.capital.zakat_total) }),
          h(StatCard, { label: "Net Capital", value: money(P.capital.net_capital) })
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-profit",
    topbar: { breadcrumb: "Reports", title: "Profit & Capital" },
    content: h(Root),
  });
})();
