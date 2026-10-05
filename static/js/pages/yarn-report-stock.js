/* Stock Report - wired to app.py's report_stock() route. A flat list of
   every item's current stock quantity (opening + purchases - sales),
   filterable by name/area, with a StatCard summary and a With/Without
   Value toggle that now actually changes what's shown on screen (it
   previously only affected the PDF/Excel export params, leaving the
   rate/value columns always visible either way). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, DataTable, EmptyState, StatCard, SearchField } = DS;
  const { money, ExportButtons, Segmented } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function columns(withValue) {
    const cols = [
      { key: "name", label: "Item / Quality", emphasis: true },
      { key: "area", label: "Area", render: (r) => r.area || "—" },
    ];
    if (withValue) {
      cols.push(
        { key: "purchase_rate", label: "Purch. Rate", numeric: true, align: "right", render: (r) => money(r.purchase_rate) },
        { key: "sale_rate", label: "Sale Rate", numeric: true, align: "right", render: (r) => money(r.sale_rate) }
      );
    }
    cols.push({
      key: "stock",
      label: "Stock Qty",
      numeric: true,
      align: "right",
      render: (r) => h("span", { className: "tabular", style: { color: r.stock < 0 ? "var(--red-600)" : undefined, fontWeight: "var(--fw-semibold)" } }, r.stock),
    });
    if (withValue) {
      cols.push({ key: "value", label: "Value", numeric: true, align: "right", emphasis: true, render: (r) => money(r.value) });
    }
    return cols;
  }

  function Root() {
    const allItems = P.items || [];
    const [withValue, setWithValue] = React.useState("1");
    const [q, setQ] = React.useState("");

    const filtered = React.useMemo(() => {
      const needle = q.trim().toLowerCase();
      if (!needle) return allItems;
      return allItems.filter((i) => (i.name || "").toLowerCase().includes(needle) || (i.area || "").toLowerCase().includes(needle));
    }, [allItems, q]);

    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginBottom: "16px" } },
        h(StatCard, { label: "Total Items", value: allItems.length }),
        h(StatCard, { label: "Total Stock Value", value: money(P.totalValue) }),
        h(StatCard, { label: "Negative Stock", value: P.negativeStockCount, tone: P.negativeStockCount > 0 ? "danger" : "neutral" })
      ),
      h(
        "div",
        { style: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", marginBottom: "16px", flexWrap: "wrap" } },
        h(SearchField, { value: q, onChange: (e) => setQ(e.target.value), placeholder: "Find by item or area…", width: 280 }),
        h(
          "div",
          { style: { display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" } },
          h(Segmented, {
            value: withValue,
            onChange: setWithValue,
            options: [{ value: "1", label: "With Value" }, { value: "0", label: "Without Value" }],
          }),
          h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { with_value: withValue } })
        )
      ),
      h(
        Card,
        { padding: "none" },
        filtered.length === 0
          ? h(EmptyState, { icon: "package", title: allItems.length === 0 ? "No items yet." : 'No items match "' + q + '"' })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(withValue === "1"), rows: filtered }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "report-stock",
    topbar: { breadcrumb: "Reports", title: "Stock Report" },
    content: h(Root),
  });
})();
