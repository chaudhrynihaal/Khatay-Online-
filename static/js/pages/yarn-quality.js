/* Quality / Items - wired to app.py's quality()/delete_quality() routes.
   The Purchase Rate field only prices Opening Stock Qty - the rate shown
   in the table (Purch. Rate (avg)) is the quantity-weighted average
   across that opening stock and every real Purchase entry, computed
   server-side by db.get_weighted_avg_purchase_rate(). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, IconButton, Card, Dialog, DataTable, EmptyState, Banner, Input } = DS;
  const { SearchField, Pagination } = DS;
  const { money, CsrfField, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.quality, style: { display: "flex", gap: "8px" } },
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Search item, area…", width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = P.nav.quality) }, "Clear") : null
    );
  }

  function AddItemDialog({ open, onClose }) {
    return h(
      Dialog,
      { open: open, onClose: onClose, width: 560, title: "Add an item", description: "Add a new yarn quality" },
      h(
        Banner,
        { tone: "info", style: { marginBottom: "16px" } },
        "Purchase Rate here only prices your opening stock (what it cost before you started using Khatay Online). Once you record real Purchase entries for this item, its rate becomes the quantity-weighted average across the opening stock and every purchase."
      ),
      h(
        "form",
        { method: "post", action: P.nav.quality },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "16px" } },
          h(Input, { name: "name", label: "Name", required: true, placeholder: "e.g. 40s Combed Cotton", onKeyDown: focusNextOnEnter }),
          h(Input, { name: "city_area", label: "City / Area", onKeyDown: focusNextOnEnter }),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
            h(Input, { name: "sale_rate", label: "Sale Rate", prefix: "Rs", type: "number", step: "0.01", defaultValue: 0, onKeyDown: focusNextOnEnter }),
            h(Input, { name: "opening_balance", label: "Opening Stock Qty", type: "number", step: "0.01", defaultValue: 0, onKeyDown: focusNextOnEnter }),
            h(Input, { name: "purchase_rate", label: "Purchase Rate (opening stock)", prefix: "Rs", type: "number", step: "0.01", defaultValue: 0, onKeyDown: focusNextOnEnter })
          )
        ),
        h(
          "div",
          { style: { display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "20px" } },
          h(Button, { type: "button", variant: "secondary", onClick: onClose }, "Cancel"),
          h(Button, { type: "submit", icon: "check" }, "Save Item")
        )
      )
    );
  }

  function itemColumns() {
    return [
      { key: "name", label: "Item / Quality", emphasis: true },
      { key: "area", label: "Area", render: (r) => r.area || "—" },
      { key: "purchase_rate", label: "Purch. Rate (avg)", numeric: true, align: "right", render: (r) => (r.purchase_rate ? money(r.purchase_rate) : "—") },
      { key: "sale_rate", label: "Sale Rate", numeric: true, align: "right", render: (r) => money(r.sale_rate) },
      {
        key: "stock",
        label: "Stock",
        numeric: true,
        align: "right",
        render: (r) => h("span", { style: { color: r.stock < 0 ? "var(--status-danger-fg)" : undefined, fontWeight: "var(--fw-semibold)" } }, r.stock),
      },
      {
        key: "actions",
        label: "",
        align: "right",
        width: 90,
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, {
              icon: "pencil",
              label: "Edit " + r.name,
              size: "sm",
              onClick: () => (window.location.href = urlFor(P.editQualityUrlBase, r.id)),
            }),
            r.has_history
              ? h(IconButton, { icon: "trash-2", label: "Delete " + r.name, size: "sm", disabledReason: "Can't delete — this item has transactions recorded against it" })
              : h(
                  "form",
                  {
                    method: "post",
                    action: P.nav.quality + "/" + r.id + "/delete",
                    onSubmit: (e) => {
                      if (!window.confirm("Delete this item?")) e.preventDefault();
                    },
                  },
                  h(CsrfField, null),
                  h(IconButton, { icon: "trash-2", label: "Delete " + r.name, size: "sm", type: "submit" })
                )
          ),
      },
    ];
  }

  function Root() {
    const [dialogOpen, setDialogOpen] = React.useState(false);
    const items = P.items || [];
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "flex", justifyContent: "center", marginBottom: "20px" } },
        h(Button, { size: "lg", icon: "plus", onClick: () => setDialogOpen(true) }, "Add Item")
      ),
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, h(SearchBar)),
      h(
        Card,
        { padding: "none", footer: h(Pagination, { page: 1, pageCount: 1, rangeLabel: items.length + (items.length === 1 ? " item" : " items") }) },
        items.length === 0
          ? h(EmptyState, {
              icon: "boxes",
              title: P.searchQ ? 'No items match "' + P.searchQ + '"' : "No items yet",
              message: P.searchQ ? "Try a different search." : "Add your first yarn quality to get started.",
            })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: itemColumns(), rows: items }))
      ),
      h(AddItemDialog, { open: dialogOpen, onClose: () => setDialogOpen(false) })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "quality",
    topbar: {
      breadcrumb: "Master Data",
      title: "Quality / Items",
      subtitle: P.items.length + " item" + (P.items.length === 1 ? "" : "s"),
    },
    content: h(Root),
  });
})();
