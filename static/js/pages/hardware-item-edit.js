/* Edit Item - wired to app.py's hardware_edit_item() route. Same field
   set as one bulk-add card (plus Stock Qty override, plus Variant Of/
   Variant Name). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Select, Button } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const item = P.item;

  function Root() {
    const isStandard = P.standardUnits.includes(item.unit);
    const [unit, setUnit] = React.useState(isStandard ? item.unit : "__other__");
    const unitOptions = P.standardUnits.map((u) => ({ value: u, label: u })).concat([{ value: "__other__", label: "Other…" }]);
    const parentOptions = [{ value: "", label: "Not a variant" }].concat(P.parentItems.map((p) => ({ value: String(p.id), label: p.name })));

    return h(
      Card,
      { title: "Edit " + item.name },
      h("datalist", { id: "categoryList" }, P.categories.map((c) => h("option", { key: c, value: c }))),
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1.4fr", gap: "16px" } },
          h(Input, { label: "Name", name: "name", defaultValue: item.name, required: true }),
          h(Select, { label: "Unit", name: "unit", value: unit, onChange: (e) => setUnit(e.target.value), options: unitOptions }),
          unit === "__other__" ? h(Input, { label: "Unit (custom)", name: "unit_other", defaultValue: isStandard ? "" : item.unit }) : h("input", { type: "hidden", name: "unit_other", value: "" }),
          h(Input, { label: "Category", name: "category", list: "categoryList", defaultValue: item.category || "" })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Barcode", name: "barcode", defaultValue: item.barcode || "", onKeyDown: (e) => { if (e.key === "Enter") e.preventDefault(); } }),
          h(Input, { label: "Purchase Rate", name: "purchase_rate", type: "number", step: "0.01", defaultValue: item.purchase_rate }),
          h(Input, { label: "Sale Rate", name: "sale_rate", type: "number", step: "0.01", defaultValue: item.sale_rate }),
          h(Input, { label: "Stock Qty", name: "stock_qty", type: "number", step: "0.01", defaultValue: item.stock_qty, hint: "Direct override - not run through a sale/purchase" })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Reorder Level", name: "reorder_level", type: "number", step: "0.01", defaultValue: item.reorder_level }),
          h(Input, { label: "Bulk Purchase Unit", name: "purchase_unit", defaultValue: item.purchase_unit || "" }),
          h(Input, { label: "Conversion Factor", name: "conversion_factor", type: "number", step: "0.01", defaultValue: item.conversion_factor })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" } },
          h(Select, { label: "Variant Of", name: "parent_item_id", options: parentOptions, defaultValue: item.parent_item_id ? String(item.parent_item_id) : "" }),
          h(Input, { label: "Variant Name", name: "variant_name", defaultValue: item.variant_name || "", placeholder: "e.g. 1 inch, Red" })
        ),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.nav.inventory) }, "Cancel")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "inventory",
    topbar: { breadcrumb: "Hardware", title: "Edit Item" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "inventory"),
  });
})();
