/* Brokerage - wired to app.py's report_brokerage() route. Every Sale/
   Purchase entry that had a broker assigned, grouped by broker with a
   subtotal; filterable by a specific broker and a free-text search
   (matched server-side against broker/party/D.O.#/voucher# - the
   whole page re-fetches on either filter, there's no client-side
   filtering). Owed/Paid/Balance per broker (see db.get_brokerage_summary)
   and a "Clear" dialog that records a payment via the unchanged
   /reports/brokerage/pay route - brokerage stays its own isolated
   system, same as before, just with an actual paid/owed balance now
   instead of only ever showing what's owed. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Select, Button, StatCard, EmptyState, Dialog, Input, DataTable, Badge, IconButton } = DS;
  const { SearchField } = DS;
  const { money, CsrfField, ExportButtons, GroupedTable } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function filterUrl(overrides) {
    const u = new URL(P.nav.reportBrokerage, window.location.origin);
    const broker = "broker_id" in overrides ? overrides.broker_id : P.brokerFilter;
    const q = "q" in overrides ? overrides.q : P.searchQ;
    if (broker) u.searchParams.set("broker_id", broker);
    if (q) u.searchParams.set("q", q);
    return u.pathname + u.search;
  }

  function Filters() {
    const [q, setQ] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.reportBrokerage, style: { display: "flex", gap: "10px", alignItems: "end", flexWrap: "wrap" } },
      h(Select, {
        label: "Broker",
        name: "broker_id",
        options: [{ value: "", label: "All brokers" }].concat(P.brokers.map((b) => ({ value: String(b.id), label: b.name }))),
        defaultValue: P.brokerFilter ? String(P.brokerFilter) : "",
        onChange: (e) => (window.location.href = filterUrl({ broker_id: e.target.value })),
        containerStyle: { width: 220 },
      }),
      h(SearchField, { placeholder: "Search by broker, party, D.O.#, or voucher#…", name: "q", value: q, onChange: (e) => setQ(e.target.value), width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ || P.brokerFilter ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = P.nav.reportBrokerage) }, "Clear") : null,
      h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { broker_id: P.brokerFilter } })
    );
  }

  function ClearBrokerageDialog({ open, onClose, broker }) {
    if (!broker) return null;
    return h(
      Dialog,
      { open: open, onClose: onClose, width: 480, title: "Clear brokerage bill", description: broker.broker_name },
      h(
        "div",
        { style: { display: "flex", flexDirection: "column", gap: "10px", marginBottom: "16px", fontSize: "13.5px" } },
        h("div", null, "Owed: ", h("strong", null, money(broker.owed))),
        h("div", null, "Paid so far: ", h("strong", null, money(broker.paid))),
        h("div", null, "Balance: ", h("strong", null, money(broker.balance)))
      ),
      h(
        "form",
        { method: "post", action: P.payBrokerageUrl },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "broker_id", value: broker.broker_id }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(Input, { label: "Amount", type: "number", step: "0.01", name: "amount", prefix: "Rs", defaultValue: broker.balance > 0 ? broker.balance : "", required: true })
        ),
        h(Input, { label: "Description", name: "description", containerStyle: { marginTop: "16px" } }),
        h(
          "div",
          { style: { display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "20px" } },
          h(Button, { type: "button", variant: "secondary", onClick: onClose }, "Cancel"),
          h(Button, { type: "submit", icon: "check" }, "Record Payment")
        )
      )
    );
  }

  function summaryColumns(onClear) {
    return [
      { key: "broker_name", label: "Broker", emphasis: true },
      { key: "owed", label: "Owed", numeric: true, align: "right", render: (r) => money(r.owed) },
      { key: "paid", label: "Paid", numeric: true, align: "right", render: (r) => money(r.paid) },
      {
        key: "balance", label: "Balance", numeric: true, align: "right",
        render: (r) => h(Badge, { tone: r.balance > 0 ? "warn" : "ok" }, money(r.balance)),
      },
      {
        key: "actions", label: "", align: "right",
        render: (r) => h(Button, { size: "sm", variant: "secondary", onClick: () => onClear(r) }, "Clear"),
      },
    ];
  }

  function SummaryCard() {
    const [clearing, setClearing] = React.useState(null);
    const summary = P.summary || [];
    if (summary.length === 0) return null;
    return h(
      React.Fragment,
      null,
      h(
        Card,
        { title: "Owed / Paid / Balance", padding: "none" },
        h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: summaryColumns(setClearing), rows: summary }))
      ),
      h(ClearBrokerageDialog, { open: !!clearing, onClose: () => setClearing(null), broker: clearing })
    );
  }

  function columns() {
    return [
      { key: "voucher_display", label: "Voucher # / Broker", emphasis: true },
      { key: "date", label: "Date" },
      { key: "do_no", label: "D.O.#", render: (r) => r.do_no || "—" },
      { key: "party_name", label: "Party", render: (r) => r.party_name || "—" },
      { key: "item_name", label: "Item", render: (r) => r.item_name || "—" },
      { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => (r.qty ? r.qty : "—") },
      { key: "amount", label: "Amount", numeric: true, align: "right", render: (r) => money(r.amount) },
      { key: "brokerage", label: "Brokerage", numeric: true, align: "right", render: (r) => money(r.brokerage) },
    ];
  }

  function Root() {
    const groups = P.groups || [];
    return h(
      React.Fragment,
      null,
      h(Filters),
      h("div", { style: { maxWidth: 280 } }, h(StatCard, { label: "Total Brokerage", value: money(P.total) })),
      h(SummaryCard),
      h(
        Card,
        { padding: "none" },
        groups.length === 0
          ? h(EmptyState, { icon: "handshake", title: "No brokerage earned yet", message: "Assign a broker (with a configured rate) to a Sale or Purchase entry." })
          : h(
              "div",
              { style: { overflowX: "auto" } },
              h(GroupedTable, {
                columns: columns(),
                subtotalKey: "amount",
                groups: groups.map((g) => ({ label: g.broker_name, subtotal: g.subtotal, rows: g.rows })),
              })
            )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-brokerage",
    topbar: { breadcrumb: "Reports", title: "Brokerage" },
    content: h(Root),
  });
})();
