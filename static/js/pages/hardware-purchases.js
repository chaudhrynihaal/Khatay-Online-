/* Purchase List - wired to app.py's hardware_purchases() route. Same
   skeleton as Sale Book plus a Sale Rate + Expiry Date per line
   (db.hardware_record_purchase re-prices the item from these on save)
   and a bulk-unit-converter helper for items with a configured
   purchase_unit/conversion_factor (e.g. "1 carton = 24 pcs"). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, IconButton, Banner } = DS;
  const { money, CsrfField, ComboboxField, Segmented, BarcodeScanInput, InvoiceList, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  let nextRowKey = 1;
  function blankRow() {
    return { key: nextRowKey++, itemId: "", qty: "", rate: "", saleRate: "", expiryDate: "" };
  }

  function baseItemOptions(extra) {
    return P.items.concat(extra).map((i) => ({
      value: String(i.id),
      label: i.display_name || i.name,
      sale_rate: i.sale_rate,
      purchase_rate: i.purchase_rate,
      purchase_unit: i.purchase_unit,
      conversion_factor: i.conversion_factor,
    }));
  }

  function BulkConverter({ onApply, unit, factor }) {
    const [bulkQty, setBulkQty] = React.useState("");
    const [bulkTotal, setBulkTotal] = React.useState("");
    function apply() {
      const bq = parseFloat(bulkQty);
      const bt = parseFloat(bulkTotal);
      if (!bq || !bt) return;
      const baseQty = bq * factor;
      onApply(baseQty, bt / baseQty);
      setBulkQty("");
      setBulkTotal("");
    }
    return h(
      "div",
      { style: { display: "flex", alignItems: "end", gap: "10px", padding: "10px 12px", background: "var(--surface-brand-soft)", border: "1px dashed var(--indigo-100)", borderRadius: "var(--radius-md)" } },
      h("div", { style: { fontSize: "12.5px", color: "var(--text-subtle)", flex: "0 0 auto", maxWidth: 160 } }, "Buying by the " + unit + " (" + factor + "/unit)?"),
      h(Input, { label: "Bulk Qty", type: "number", step: "0.01", value: bulkQty, onChange: (e) => setBulkQty(e.target.value), size: "sm", containerStyle: { width: 100 } }),
      h(Input, { label: "Bulk Total Cost", type: "number", step: "0.01", value: bulkTotal, onChange: (e) => setBulkTotal(e.target.value), size: "sm", containerStyle: { width: 130 } }),
      h(Button, { type: "button", size: "sm", variant: "secondary", onClick: apply }, "Apply")
    );
  }

  function LineRow({ row, itemOptions, onChange, onRemove }) {
    const selected = itemOptions.find((o) => o.value === row.itemId);
    const qtyNum = parseFloat(row.qty) || 0;
    const amount = qtyNum * (parseFloat(row.rate) || 0);
    const showConverter = selected && selected.purchase_unit && selected.conversion_factor > 1;

    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "8px" } },
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "2fr 0.8fr 0.8fr 0.8fr 0.9fr 1fr auto", gap: "10px", alignItems: "start" } },
        h(ComboboxField, {
          key: row.itemId,
          name: "item_id[]",
          label: "Item",
          options: itemOptions,
          defaultValue: row.itemId,
          placeholder: "Search…",
          quickAddUrl: P.itemQuickAddUrl,
          entityLabel: "item",
          onPick: (value, opt) => onChange(row.key, { itemId: value, saleRate: opt ? String(opt.sale_rate || 0) : row.saleRate }),
        }),
        h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty[]", value: row.qty, onChange: (e) => onChange(row.key, { qty: e.target.value }), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate[]", value: row.rate, onChange: (e) => onChange(row.key, { rate: e.target.value }), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Sale Rate", type: "number", step: "0.01", name: "sale_rate[]", value: row.saleRate, onChange: (e) => onChange(row.key, { saleRate: e.target.value }) }),
        h(Input, { label: "Expiry Date", type: "date", name: "expiry_date[]", value: row.expiryDate, onChange: (e) => onChange(row.key, { expiryDate: e.target.value }) }),
        h(Input, { label: "Amount", value: money(amount), disabled: true }),
        h("div", { style: { paddingTop: 26 } }, h(IconButton, { icon: "x", label: "Remove line", size: "sm", onClick: onRemove }))
      ),
      showConverter
        ? h(BulkConverter, {
            unit: selected.purchase_unit,
            factor: selected.conversion_factor,
            onApply: (baseQty, rate) => onChange(row.key, { qty: String(baseQty), rate: rate.toFixed(2) }),
          })
        : null
    );
  }

  function Root() {
    const [rows, setRows] = React.useState([blankRow()]);
    const [extraItems, setExtraItems] = React.useState([]);
    const [mode, setMode] = React.useState("Cash");
    const rowsRef = React.useRef(rows);
    rowsRef.current = rows;

    const itemOptions = baseItemOptions(extraItems);

    function updateRow(key, patch) {
      setRows((rs) => rs.map((r) => (r.key === key ? Object.assign({}, r, patch) : r)));
    }
    function addRow() {
      setRows((rs) => rs.concat([blankRow()]));
    }
    function removeRow(key) {
      setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : [blankRow()]));
    }

    function handleScan(code) {
      fetch(P.itemByBarcodeUrl + "?code=" + encodeURIComponent(code), { credentials: "same-origin" })
        .then((r) => r.json())
        .then((data) => {
          if (!data.ok) {
            window.alert("No item found for barcode " + code + ". Add it from Inventory, or type its name in an Item field below to quick-add it.");
            return;
          }
          if (!P.items.some((i) => i.id === data.id) && !extraItems.some((i) => i.id === data.id)) {
            setExtraItems((ex) => ex.concat([data]));
          }
          const current = rowsRef.current;
          const openRow = current[current.length - 1];
          const targetKey = openRow && !openRow.itemId ? openRow.key : null;
          const patch = { itemId: String(data.id), saleRate: String(data.sale_rate || 0), rate: String(data.purchase_rate || 0), qty: (openRow && openRow.qty) || "1" };
          if (targetKey) {
            updateRow(targetKey, patch);
          } else {
            const row = Object.assign(blankRow(), patch);
            setRows((rs) => rs.concat([row]));
          }
        })
        .catch(() => window.alert("Could not reach the server - try again."));
    }

    const grandTotal = rows.reduce((s, r) => s + (parseFloat(r.qty) || 0) * (parseFloat(r.rate) || 0), 0);

    return h(
      React.Fragment,
      null,
      h(Card, { title: "Scan to add" }, h(BarcodeScanInput, { onScan: handleScan })),
      h(
        Card,
        { title: "New purchase" },
        h(
          "form",
          { method: "post", action: P.nav.purchases },
          h(CsrfField, null),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
            h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
            h(ComboboxField, { name: "party_id", label: "Supplier", options: P.suppliers.map((s) => ({ value: String(s.id), label: s.name })), placeholder: "Search…", quickAddUrl: P.supplierQuickAddUrl, entityLabel: "supplier" }),
            h(
              "div",
              { style: { display: "flex", flexDirection: "column", gap: "6px" } },
              h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
              h("input", { type: "hidden", name: "mode", value: mode }),
              h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash" }, { value: "Credit", label: "Credit" }] })
            )
          ),
          mode === "Credit" ? h(Banner, { tone: "info", style: { marginTop: "16px" } }, "This purchase will be added to the supplier's balance - pick a supplier above.") : null,
          h(
            "div",
            { style: { display: "flex", flexDirection: "column", gap: "12px", marginTop: "20px" } },
            rows.map((row) => h(LineRow, { key: row.key, row: row, itemOptions: itemOptions, onChange: updateRow, onRemove: () => removeRow(row.key) }))
          ),
          h("div", { style: { marginTop: "10px" } }, h(Button, { type: "button", variant: "secondary", size: "sm", icon: "plus", onClick: addRow }, "Add Line")),
          h(Input, { label: "Description", name: "description", containerStyle: { marginTop: "16px", maxWidth: 480 } }),
          h(
            "div",
            { style: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "20px" } },
            h("div", { style: { fontSize: "16px", fontWeight: "var(--fw-bold)" } }, "Total: " + money(grandTotal)),
            h(Button, { type: "submit", icon: "check" }, "Save Purchase")
          )
        )
      ),
      h(
        Card,
        { title: "Add a new supplier" },
        h(
          "form",
          { method: "post", action: P.addSupplierUrl, style: { display: "grid", gridTemplateColumns: "2fr 1fr auto", gap: "10px", alignItems: "end" } },
          h(CsrfField, null),
          h(Input, { label: "Name", name: "name", required: true }),
          h(Input, { label: "Phone", name: "phone" }),
          h(Button, { type: "submit", variant: "secondary" }, "Add Supplier")
        )
      ),
      h(InvoiceList, {
        title: "Recent purchases",
        invoices: P.invoices,
        emptyIcon: "package",
        emptyMessage: "No purchases recorded yet.",
        printUrlBase: P.printUrlBase,
        editUrlBase: P.editTxnUrlBase,
        deleteUrlBase: P.deleteTxnUrlBase,
        canEdit: P.canEdit,
        isAdmin: P.isAdmin,
      })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "purchases",
    topbar: { breadcrumb: "Hardware", title: "Purchase List" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "purchases"),
  });
})();
