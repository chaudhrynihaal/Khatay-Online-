/* Hardware Dashboard - wired to app.py's hardware_dashboard()/
   hardware_tax_settings() routes. Same click-to-expand stat-breakdown
   pattern as Kiryana's dashboard, plus: an Open Quotations card, a
   Low Stock breakdown with sales-velocity-based reorder suggestions,
   and a (non-print) Tax Settings card - no Kiryana equivalent. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, StatCard, DataTable, EmptyState, Reveal, Button, Input } = DS;
  const { money, CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function BreakdownPanel({ open, title, children, empty }) {
    return h(
      Reveal,
      { show: open },
      h(
        Card,
        { title: title, padding: "none", style: { marginTop: "-6px" } },
        children && children.length !== 0 ? children : h(EmptyState, { title: empty })
      )
    );
  }

  function TaxSettings() {
    return h(
      Card,
      { title: "Tax Settings" },
      h(
        "form",
        { method: "post", action: P.taxSettingsUrl, style: { display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "16px", alignItems: "end" } },
        h(CsrfField, null),
        h(Input, { label: "Tax Rate (%)", name: "tax_rate", type: "number", step: "0.01", defaultValue: P.taxRate }),
        h(Input, { label: "GST Number", name: "gst_number", defaultValue: P.gstNumber || "" }),
        h(Button, { type: "submit" }, "Save Tax Settings")
      )
    );
  }

  function Root() {
    const [open, setOpen] = React.useState({});
    const toggle = (id) => setOpen((o) => Object.assign({}, o, { [id]: !o[id] }));

    const stockRows = P.stock.breakdown || [];
    const receivableRows = P.receivable.breakdown || [];
    const payableRows = P.payable.breakdown || [];
    const lowStockRows = P.lowStock.breakdown || [];
    const expiringRows = P.expiring.breakdown || [];

    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Total Stock", value: P.stock.total_qty, icon: "boxes", onClick: () => toggle("stock"), style: { cursor: "pointer" } }),
        h(StatCard, { label: "Total Stock Value", value: money(P.stock.total_value), icon: "wallet" }),
        h(StatCard, { label: "Cash Balance", value: money(P.cashBalance), icon: "banknote", tone: P.cashBalance < 0 ? "danger" : "neutral" }),
        h(StatCard, { label: "Sales Today", value: money(P.salesTodayTotal), icon: "trending-up" }),
        h(StatCard, { label: "Total Sales", value: money(P.totalSales), icon: "receipt" }),
        h(StatCard, { label: "Net Profit", value: money(P.netProfit), icon: "line-chart", tone: P.netProfit < 0 ? "danger" : "neutral" }),
        h(StatCard, { label: "Total Receivable", value: money(P.receivable.total), icon: "hand-coins", onClick: () => toggle("receivable"), style: { cursor: "pointer" } }),
        h(StatCard, { label: "Total Payable", value: money(P.payable.total), icon: "wallet-cards", onClick: () => toggle("payable"), style: { cursor: "pointer" } }),
        h(StatCard, { label: "Low Stock", value: P.lowStock.count, icon: "triangle-alert", tone: P.lowStock.count > 0 ? "highlight" : "neutral", onClick: () => toggle("lowStock"), style: { cursor: "pointer" } }),
        h(StatCard, { label: "Expiring Soon", value: P.expiring.count, icon: "clock-alert", tone: P.expiring.count > 0 ? "highlight" : "neutral", onClick: () => toggle("expiring"), style: { cursor: "pointer" } }),
        h(StatCard, { label: "Open Quotations", value: P.openQuotationsCount, icon: "file-text", onClick: () => (window.location.href = P.nav.quotations), style: { cursor: "pointer" } })
      ),

      h(
        BreakdownPanel,
        { open: open.stock, title: "Stock breakdown", empty: "No stock yet." },
        stockRows.length
          ? h(DataTable, {
              columns: [
                { key: "name", label: "Item", emphasis: true },
                { key: "unit", label: "Unit" },
                { key: "stock_qty", label: "Stock Qty", numeric: true, align: "right" },
                { key: "value", label: "Value", numeric: true, align: "right", render: (r) => money(r.value) },
              ],
              rows: stockRows,
            })
          : null
      ),
      h(
        BreakdownPanel,
        { open: open.receivable, title: "Receivable breakdown", empty: "Nothing outstanding." },
        receivableRows.length
          ? h(DataTable, {
              columns: [
                { key: "name", label: "Customer", emphasis: true },
                { key: "balance", label: "Balance", numeric: true, align: "right", render: (r) => money(r.balance) },
                { key: "actions", label: "", align: "right", render: (r) => h("a", { href: P.nav.ledger + "?type=Customer&party_id=" + r.id }, "View Ledger") },
              ],
              rows: receivableRows,
            })
          : null
      ),
      h(
        BreakdownPanel,
        { open: open.payable, title: "Payable breakdown", empty: "Nothing outstanding." },
        payableRows.length
          ? h(DataTable, {
              columns: [
                { key: "name", label: "Supplier", emphasis: true },
                { key: "balance", label: "Balance", numeric: true, align: "right", render: (r) => money(r.balance) },
                { key: "actions", label: "", align: "right", render: (r) => h("a", { href: P.nav.ledger + "?type=Supplier&party_id=" + r.id }, "View Ledger") },
              ],
              rows: payableRows,
            })
          : null
      ),
      h(
        BreakdownPanel,
        { open: open.lowStock, title: "Low stock", empty: "Nothing low on stock." },
        lowStockRows.length
          ? h(
              React.Fragment,
              null,
              h(DataTable, {
                columns: [
                  { key: "name", label: "Item", emphasis: true },
                  { key: "stock_qty", label: "Stock", numeric: true, align: "right", render: (r) => r.stock_qty + " " + (r.unit || "") },
                  { key: "reorder_level", label: "Reorder Level", numeric: true, align: "right" },
                  { key: "sold_30d", label: "Sold 30d", numeric: true, align: "right" },
                  { key: "suggested_qty", label: "Suggested Reorder", numeric: true, align: "right", emphasis: true },
                  { key: "actions", label: "", align: "right", render: () => h("a", { href: P.nav.purchases }, "Restock") },
                ],
                rows: lowStockRows,
              }),
              h("p", { style: { fontSize: "12.5px", color: "var(--text-subtle)", padding: "10px var(--gutter-card)" } }, "Suggested Reorder = enough to cover the last 30 days of sales, on top of getting back above the reorder level.")
            )
          : null
      ),
      h(
        BreakdownPanel,
        { open: open.expiring, title: "Expiring soon", empty: "Nothing expiring soon." },
        expiringRows.length
          ? h(DataTable, {
              columns: [
                { key: "item", label: "Item", emphasis: true },
                { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => r.qty + " " + (r.unit || "") },
                { key: "purchase_date", label: "Purchased" },
                {
                  key: "expiry_date",
                  label: "Expiry",
                  render: (r) => h("span", { style: { color: r.expired ? "var(--red-600)" : undefined, fontWeight: r.expired ? "var(--fw-semibold)" : undefined } }, r.expiry_date),
                },
              ],
              rows: expiringRows,
            })
          : null
      ),

      h(TaxSettings),

      h(
        Card,
        { title: "Quick actions" },
        h(
          "div",
          { style: { display: "flex", gap: "10px", flexWrap: "wrap" } },
          h(Button, { icon: "plus", onClick: () => (window.location.href = P.nav.sales) }, "New Sale"),
          h(Button, { icon: "plus", variant: "secondary", onClick: () => (window.location.href = P.nav.purchases) }, "New Purchase"),
          h(Button, { icon: "plus", variant: "secondary", onClick: () => (window.location.href = P.nav.quotations) }, "New Quotation"),
          h(Button, { icon: "plus", variant: "secondary", onClick: () => (window.location.href = P.nav.inventory) }, "New Item"),
          h(Button, { icon: "plus", variant: "secondary", onClick: () => (window.location.href = P.nav.expenses) }, "New Expense"),
          h(Button, { icon: "printer", variant: "ghost", onClick: () => window.print() }, "Print")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "dashboard",
    topbar: { breadcrumb: "Hardware", title: "Dashboard" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "dashboard"),
  });
})();
