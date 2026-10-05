/* Inventory - wired to app.py's hardware_inventory()/hardware_edit_item()/
   hardware_delete_item() routes. Same bulk multi-row <form> pattern as
   Kiryana's Inventory, plus two Hardware-only fields per card: "Variant
   Of" (parent_item_id[]) and "Variant Name" (variant_name[]), letting
   one item be a size/color variant of another (e.g. "Screws — 1 inch"
   under a "Screws" parent) - db.hardware_list_items() folds these into
   a ready-made display_name, used everywhere an item name is shown. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Select, Button, IconButton, DataTable, EmptyState, Banner } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  let nextRowId = 1;
  const parentOptions = [{ value: "", label: "Not a variant" }].concat(P.parentItems.map((p) => ({ value: String(p.id), label: p.name })));

  function ItemCard({ onRemove }) {
    const [unit, setUnit] = React.useState(P.standardUnits[0] || "pcs");
    const unitOptions = P.standardUnits.map((u) => ({ value: u, label: u })).concat([{ value: "__other__", label: "Other…" }]);
    return h(
      "div",
      { style: { border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "16px", position: "relative", display: "flex", flexDirection: "column", gap: "14px" } },
      h(
        "div",
        { style: { position: "absolute", top: 10, right: 10 } },
        h(IconButton, { icon: "x", label: "Remove item", size: "sm", onClick: onRemove })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1.4fr", gap: "14px" } },
        h(Input, { label: "Name", name: "name[]", placeholder: "e.g. Screws" }),
        h(Select, { label: "Unit", name: "unit[]", value: unit, onChange: (e) => setUnit(e.target.value), options: unitOptions }),
        unit === "__other__" ? h(Input, { label: "Unit (custom)", name: "unit_other[]" }) : h("input", { type: "hidden", name: "unit_other[]", value: "" }),
        h(Input, { label: "Category", name: "category[]", list: "categoryList", placeholder: "e.g. Fasteners" })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "14px" } },
        h(Input, { label: "Barcode", name: "barcode[]", onKeyDown: (e) => { if (e.key === "Enter") e.preventDefault(); } }),
        h(Input, { label: "Purchase Rate", name: "purchase_rate[]", type: "number", step: "0.01", defaultValue: "0" }),
        h(Input, { label: "Sale Rate", name: "sale_rate[]", type: "number", step: "0.01", defaultValue: "0" }),
        h(Input, { label: "Opening Qty", name: "opening_qty[]", type: "number", step: "0.01", defaultValue: "0" })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" } },
        h(Input, { label: "Reorder Level", name: "reorder_level[]", type: "number", step: "0.01", defaultValue: "0", hint: "0 = don't warn on low stock" }),
        h(Input, { label: "Bulk Purchase Unit", name: "purchase_unit[]", placeholder: "e.g. carton" }),
        h(Input, { label: "Conversion Factor", name: "conversion_factor[]", type: "number", step: "0.01", defaultValue: "1", hint: "units per bulk purchase unit" })
      ),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" } },
        h(Select, { label: "Variant Of", name: "parent_item_id[]", options: parentOptions, defaultValue: "", hint: "Is this a size/color variant of an existing item?" }),
        h(Input, { label: "Variant Name", name: "variant_name[]", placeholder: "e.g. 1 inch, Red" })
      )
    );
  }

  function AddItemsForm() {
    const [rows, setRows] = React.useState([nextRowId++]);

    function addRow() {
      setRows((r) => r.concat([nextRowId++]));
    }
    function removeRow(id) {
      setRows((r) => (r.length > 1 ? r.filter((x) => x !== id) : [nextRowId++]));
    }

    return h(
      Card,
      { title: "Add items" },
      h(
        Banner,
        { tone: "info", style: { marginBottom: "16px" } },
        "Reorder Level triggers the dashboard's Low Stock warning once stock falls to or below it (0 = never warn). Bulk Purchase Unit + Conversion Factor let the Purchase List page convert a bulk buy into base units automatically. Variant Of + Variant Name let this item be a size/color variant of another (e.g. \"Screws — 1 inch\")."
      ),
      h("datalist", { id: "categoryList" }, P.categories.map((c) => h("option", { key: c, value: c }))),
      h(
        "form",
        { method: "post", action: P.nav.inventory },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "14px" } },
          rows.map((id) => h(ItemCard, { key: id, onRemove: () => removeRow(id) }))
        ),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "16px" } },
          h(Button, { type: "button", variant: "secondary", icon: "plus", onClick: addRow }, "Add Another Item"),
          h(Button, { type: "submit", icon: "check" }, "Save Items")
        )
      )
    );
  }

  function ItemsTable() {
    const [category, setCategory] = React.useState("");
    const items = (P.items || []).filter((i) => !category || i.category === category);
    const categoryOptions = [{ value: "", label: "All categories" }].concat(P.categories.map((c) => ({ value: c, label: c })));

    function columns() {
      return [
        {
          key: "name",
          label: "Item",
          emphasis: true,
          render: (r) => (r.parent_item_id ? h("span", null, h("span", { style: { color: "var(--text-subtle)" } }, "↳ "), r.variant_name) : r.name),
        },
        { key: "category", label: "Category", render: (r) => r.category || "—" },
        { key: "unit", label: "Unit", render: (r) => r.unit || "—" },
        { key: "barcode", label: "Barcode", render: (r) => r.barcode || "—" },
        { key: "purchase_rate", label: "Purchase Rate", numeric: true, align: "right", render: (r) => window.KhatayDS.money(r.purchase_rate) },
        { key: "sale_rate", label: "Sale Rate", numeric: true, align: "right", render: (r) => window.KhatayDS.money(r.sale_rate) },
        {
          key: "stock_qty",
          label: "Stock",
          numeric: true,
          align: "right",
          render: (r) => {
            const low = r.reorder_level > 0 && r.stock_qty > 0 && r.stock_qty <= r.reorder_level;
            const negative = r.stock_qty <= 0;
            return h("span", { style: { color: negative ? "var(--red-600)" : low ? "var(--amber-700)" : undefined, fontWeight: negative || low ? "var(--fw-semibold)" : undefined } }, r.stock_qty + " " + (r.unit || "") + (low ? " ⚠" : ""));
          },
        },
        {
          key: "actions",
          label: "",
          align: "right",
          render: (r) =>
            h(
              "div",
              { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
              h(IconButton, { icon: "pencil", label: "Edit " + r.display_name, size: "sm", onClick: () => (window.location.href = urlFor(P.editItemUrlBase, r.id)) }),
              h(
                "form",
                {
                  method: "post",
                  action: urlFor(P.deleteItemUrlBase, r.id),
                  onSubmit: (e) => {
                    if (!window.confirm("Remove this item?")) e.preventDefault();
                  },
                },
                h(CsrfField, null),
                h(IconButton, { icon: "trash-2", label: "Delete " + r.display_name, size: "sm", type: "submit" })
              )
            ),
        },
      ];
    }

    return h(
      Card,
      { title: "All items", actions: h(Select, { name: "categoryFilter", options: categoryOptions, value: category, onChange: (e) => setCategory(e.target.value), containerStyle: { width: 200 } }), padding: "none" },
      items.length === 0
        ? h(EmptyState, { icon: "sprout", title: "No items yet", message: "Add your first one above." })
        : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: items }))
    );
  }

  window.KhatayDS.mountShell({
    activeId: "inventory",
    topbar: { breadcrumb: "Hardware", title: "Inventory", actions: h(Button, { variant: "secondary", icon: "printer", onClick: () => window.print() }, "Print") },
    content: h(React.Fragment, null, h(AddItemsForm), h(ItemsTable)),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "inventory"),
  });
})();
