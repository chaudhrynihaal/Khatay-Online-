/* Purchase / Sale Ledger - wired to app.py's report_quality_ledger()
   route. Three views of the same Purchase/Sale history, grouped by
   item instead of by party (see db.get_quality_ledger /
   get_quality_ledger_summary):
     Overall  - pick one item, see its full chronological history with
                a running quantity balance (same idea as the Party
                Ledger, but tracking qty on hand instead of amount owed)
     By count - one row per item, total quantity purchased/sold - for
                spotting your biggest-volume items at a glance
     By rate  - one row per item, purchase/sale rate min/avg/max - for
                spotting your most price-variable items
   Each view is a real page load (?view=...), not client-side
   filtering, matching every other report in this app. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Tabs, Combobox, DataTable, EmptyState, Badge } = DS;
  const { money } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const itemOptions = P.items.map((i) => ({ value: String(i.id), label: i.name }));

  function viewUrl(view, qualityId) {
    const u = new URL(P.nav.reportQualityLedger, window.location.origin);
    u.searchParams.set("view", view);
    if (view === "overall" && qualityId) u.searchParams.set("quality_id", qualityId);
    return u.pathname + u.search;
  }

  function ViewTabs() {
    return h(Tabs, {
      value: P.view,
      onChange: (v) => (window.location.href = viewUrl(v, P.qualityId)),
      items: [{ id: "overall", label: "Overall" }, { id: "count", label: "By Count" }, { id: "rate", label: "By Rate" }],
      style: { marginBottom: "20px" },
    });
  }

  function OverallView() {
    const ledger = P.ledger;
    return h(
      React.Fragment,
      null,
      h(
        Card,
        { title: "Pick an item" },
        h(Combobox, {
          label: "Item / Quality",
          options: itemOptions,
          value: P.qualityId ? String(P.qualityId) : "",
          onChange: (v) => (window.location.href = viewUrl("overall", v)),
          placeholder: "Search…",
        })
      ),
      !ledger
        ? h(Card, { padding: "none", style: { marginTop: "16px" } }, h(EmptyState, { icon: "notebook-text", title: "Pick an item to see its ledger" }))
        : h(
            Card,
            {
              title: ledger.item.name,
              subtitle: (ledger.item.area || "—") + " · Closing balance: " + ledger.closing_balance,
              padding: "none",
              style: { marginTop: "16px" },
            },
            h(
              "div",
              { style: { overflowX: "auto" } },
              h(DataTable, {
                columns: [
                  { key: "voucher_display", label: "Voucher #", emphasis: true },
                  { key: "date", label: "Date" },
                  { key: "voucher_type", label: "Type", render: (r) => h(Badge, { tone: r.voucher_type === "PURCHASE" ? "info" : "ok" }, r.voucher_type === "PURCHASE" ? "Purchase" : "Sale") },
                  { key: "party_name", label: "Party", render: (r) => r.party_name || "—" },
                  { key: "do_no", label: "D.O.#", render: (r) => r.do_no || "—" },
                  { key: "qty", label: "Qty", numeric: true, align: "right" },
                  { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => money(r.rate) },
                  { key: "amount", label: "Amount", numeric: true, align: "right", render: (r) => money(r.amount) },
                  { key: "balance", label: "Balance", numeric: true, align: "right", emphasis: true },
                ],
                rows: ledger.rows,
              })
            )
          )
    );
  }

  function CountView() {
    const rows = P.summary || [];
    return h(
      Card,
      { title: "By Count - total quantity purchased/sold per item", padding: "none" },
      rows.length === 0
        ? h(EmptyState, { icon: "notebook-text", title: "No purchase/sale activity yet" })
        : h(
            "div",
            { style: { overflowX: "auto" } },
            h(DataTable, {
              columns: [
                { key: "name", label: "Item / Quality", emphasis: true },
                { key: "area", label: "Area", render: (r) => r.area || "—" },
                { key: "purchased_qty", label: "Purchased", numeric: true, align: "right" },
                { key: "sold_qty", label: "Sold", numeric: true, align: "right" },
                { key: "net_qty", label: "Net (Stock)", numeric: true, align: "right", emphasis: true },
              ],
              rows: rows,
            })
          )
    );
  }

  function RateView() {
    const rows = P.summary || [];
    return h(
      Card,
      { title: "By Rate - purchase/sale rate range per item", padding: "none" },
      rows.length === 0
        ? h(EmptyState, { icon: "notebook-text", title: "No purchase/sale activity yet" })
        : h(
            "div",
            { style: { overflowX: "auto" } },
            h(DataTable, {
              columns: [
                { key: "name", label: "Item / Quality", emphasis: true },
                { key: "area", label: "Area", render: (r) => r.area || "—" },
                { key: "purchase_rate_min", label: "Purch. Min", numeric: true, align: "right", render: (r) => money(r.purchase_rate_min) },
                { key: "purchase_rate_avg", label: "Purch. Avg", numeric: true, align: "right", render: (r) => money(r.purchase_rate_avg) },
                { key: "purchase_rate_max", label: "Purch. Max", numeric: true, align: "right", render: (r) => money(r.purchase_rate_max) },
                { key: "sale_rate_min", label: "Sale Min", numeric: true, align: "right", render: (r) => money(r.sale_rate_min) },
                { key: "sale_rate_avg", label: "Sale Avg", numeric: true, align: "right", render: (r) => money(r.sale_rate_avg) },
                { key: "sale_rate_max", label: "Sale Max", numeric: true, align: "right", render: (r) => money(r.sale_rate_max) },
              ],
              rows: rows,
            })
          )
    );
  }

  function Root() {
    return h(
      React.Fragment,
      null,
      h(ViewTabs),
      P.view === "count" ? h(CountView) : P.view === "rate" ? h(RateView) : h(OverallView)
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-quality-ledger",
    topbar: { breadcrumb: "Reports", title: "Purchase / Sale Ledger" },
    content: h(Root),
  });
})();
