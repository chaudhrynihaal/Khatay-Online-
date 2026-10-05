/* Payable Ledger - wired to app.py's report_payable() route.
   Structurally identical to the Receivable Ledger (same
   db._fifo_aging engine, invoked for PURCHASE/PAYMENT instead of
   SALE/RECEIPT) - every unpaid purchase invoice, grouped by supplier
   with a subtotal, as of a chosen date. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, StatCard, EmptyState } = DS;
  const { money, ExportButtons, GroupedTable } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function DateFilter() {
    return h(
      "form",
      { method: "get", action: P.nav.reportPayable, style: { display: "flex", gap: "10px", alignItems: "end" } },
      h(Input, { label: "Status as of", type: "date", name: "as_of", defaultValue: P.asOf }),
      h(Button, { type: "submit", variant: "secondary" }, "Refresh"),
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { as_of: P.asOf } })
    );
  }

  function statusText(r) {
    if (r.is_overdue) return "Overdue by " + r.days + "d";
    if (r.status === "Due today") return "Due today";
    return "Not due (" + r.days + "d)";
  }

  function columns() {
    return [
      { key: "voucher_display", label: "Inv # / Party", emphasis: true },
      { key: "date", label: "Date" },
      { key: "do_no", label: "D.O.#", render: (r) => r.do_no || "—" },
      { key: "item_name", label: "Item", render: (r) => r.item_name || "—" },
      { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => (r.qty ? r.qty : "—") },
      { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => (r.rate ? money(r.rate) : "—") },
      { key: "full_amount", label: "Full Amount", numeric: true, align: "right", render: (r) => money(r.full_amount) },
      { key: "outstanding", label: "Remaining", numeric: true, align: "right", render: (r) => money(r.outstanding) },
      { key: "credit_days", label: "Credit Days" },
      { key: "due_date", label: "Due Date", render: (r) => r.due_date || "—" },
      { key: "status", label: "Status", render: (r) => h("span", { style: { color: r.is_overdue ? "var(--red-600)" : undefined, fontWeight: r.is_overdue ? "var(--fw-semibold)" : undefined } }, statusText(r)) },
    ];
  }

  function Root() {
    const groups = P.groups || [];
    return h(
      React.Fragment,
      null,
      h(DateFilter),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Total Outstanding", value: money(P.total) }),
        h(StatCard, { label: "Overdue", value: money(P.overdue), tone: P.overdue > 0 ? "danger" : "neutral" })
      ),
      h(
        Card,
        { padding: "none" },
        groups.length === 0
          ? h(EmptyState, { icon: "circle-check", title: "Nothing outstanding — every purchase invoice is fully paid." })
          : h(
              "div",
              { style: { overflowX: "auto" } },
              h(GroupedTable, {
                columns: columns(),
                subtotalKey: "outstanding",
                groups: groups.map((g) => ({ label: g.party_name, subtotal: g.subtotal, rows: g.rows })),
              })
            )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-payable",
    topbar: { breadcrumb: "Reports", title: "Payable Ledger" },
    content: h(Root),
  });
})();
