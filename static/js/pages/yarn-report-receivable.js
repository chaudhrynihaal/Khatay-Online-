/* Receivable Ledger - wired to app.py's report_receivable() route.
   Every unpaid sale invoice, grouped by party with a subtotal, as of a
   chosen date (aging/overdue status is computed relative to as_of
   server-side via db.get_receivable_aging - FIFO against each party's
   credit-days terms). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, StatCard, EmptyState } = DS;
  const { money, ExportButtons, GroupedTable } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function DateFilter() {
    return h(
      "form",
      { method: "get", action: P.nav.reportReceivable, style: { display: "flex", gap: "10px", alignItems: "end" } },
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
      {
        key: "days", label: "Days Outstanding", numeric: true, align: "right",
        render: (r) => h("span", { style: { color: r.is_overdue ? "var(--red-600)" : undefined, fontWeight: r.is_overdue ? "var(--fw-semibold)" : undefined } }, r.days),
      },
      { key: "status", label: "Status", render: (r) => h("span", { style: { color: r.is_overdue ? "var(--red-600)" : undefined, fontWeight: r.is_overdue ? "var(--fw-semibold)" : undefined } }, statusText(r)) },
    ];
  }

  function groupLabel(g) {
    return h(
      "span",
      null,
      g.party_name,
      g.party_phone ? h("span", { style: { fontWeight: "var(--fw-regular)", color: "var(--text-subtle)" } }, "  ·  " + g.party_phone) : null
    );
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
          ? h(EmptyState, { icon: "circle-check", title: "Nothing outstanding — every sale invoice is fully paid." })
          : h(
              "div",
              { style: { overflowX: "auto" } },
              h(GroupedTable, {
                columns: columns(),
                subtotalKey: "outstanding",
                groups: groups.map((g) => ({ label: groupLabel(g), subtotal: g.subtotal, rows: g.rows })),
              })
            )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-receivable",
    topbar: { breadcrumb: "Reports", title: "Receivable Ledger" },
    content: h(Root),
  });
})();
