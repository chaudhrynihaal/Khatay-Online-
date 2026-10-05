/* Cash Book - wired to app.py's report_cashbook() route. A classic
   two-sided T-account for the date range: Banaam (money out, debit)
   on the left, Jama (money in, credit) on the right, each already
   balanced server-side with a synthetic "b/f" opening line and a "c/d"
   carried-down line so both sides foot to the same total. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, StatCard, DataTable } = DS;
  const { money, ExportButtons } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function DateFilter() {
    return h(
      "form",
      { method: "get", action: P.nav.reportCashbook, style: { display: "flex", gap: "10px", alignItems: "end" } },
      h(Input, { label: "From", type: "date", name: "from", defaultValue: P.dateFrom }),
      h(Input, { label: "To", type: "date", name: "to", defaultValue: P.dateTo }),
      h(Button, { type: "submit", variant: "secondary" }, "Refresh"),
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { from: P.dateFrom, to: P.dateTo } })
    );
  }

  function Side({ title, tone, entries, total }) {
    const withTotal = entries.concat([{ ref: "", date: "", party: "TOTAL", remarks: "", amount: total, _isTotal: true }]);
    return h(
      Card,
      { title: title, style: { borderTop: "3px solid " + (tone === "red" ? "var(--red-500)" : "var(--green-500)") }, padding: "none" },
      h(
        "div",
        { style: { overflowX: "auto" } },
        h(DataTable, {
          columns: [
            { key: "ref", label: "Ref #", render: (r) => (r._isTotal ? h("strong", null, "TOTAL") : r.ref) },
            { key: "date", label: "Date" },
            { key: "party", label: "Account", render: (r) => (r._isTotal ? "" : r.party) },
            { key: "remarks", label: "Remarks", render: (r) => (r._isTotal ? "" : r.remarks || "—") },
            { key: "amount", label: "Amount", numeric: true, align: "right", render: (r) => h("span", { style: { fontWeight: r._isTotal ? "var(--fw-bold)" : "var(--fw-medium)" } }, money(r.amount)) },
          ],
          rows: withTotal,
        })
      )
    );
  }

  function Root() {
    const t = P.t;
    return h(
      React.Fragment,
      null,
      h(DateFilter),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Opening Balance", value: money(t.opening_balance) }),
        h(StatCard, { label: "Closing Balance", value: money(t.closing_balance) })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" } },
        h(Side, { title: "Banaam — money out", tone: "red", entries: t.debit_entries, total: t.total_debit }),
        h(Side, { title: "Jama — money in", tone: "green", entries: t.credit_entries, total: t.total_credit })
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-cashbook",
    topbar: { breadcrumb: "Reports", title: "Cash Book" },
    content: h(Root),
  });
})();
