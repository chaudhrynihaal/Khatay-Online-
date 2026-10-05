/* Sale Book - wired to app.py's kiryana_sales() route. One shared
   invoice_no per Save click, one kiryana_transactions row per line -
   see db.kiryana_record_sale. Barcode scanning (keyboard-wedge or
   camera) fills the currently-open row or adds a new one; a
   non-blocking oversell warning is computed client-side per row from
   each item's known stock_qty and re-confirmed with one dialog on
   submit (the server re-checks and flashes a warning too either way). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, IconButton, Banner } = DS;
  const { money, CsrfField, ComboboxField, Segmented, BarcodeScanInput, InvoiceList, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  let nextRowKey = 1;
  function blankRow() {
    return { key: nextRowKey++, itemId: "", qty: "", rate: "" };
  }

  function baseItemOptions(extra) {
    return P.items.concat(extra).map((i) => ({ value: String(i.id), label: i.name, sale_rate: i.sale_rate, stock_qty: i.stock_qty }));
  }

  function LineRow({ row, itemOptions, onChange, onRemove }) {
    const selected = itemOptions.find((o) => o.value === row.itemId);
    const stock = selected ? selected.stock_qty : null;
    const qtyNum = parseFloat(row.qty) || 0;
    const overselling = selected && qtyNum > 0 && qtyNum > stock;
    const amount = qtyNum * (parseFloat(row.rate) || 0);

    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "4px" } },
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "2.2fr 1fr 1fr 1fr auto", gap: "10px", alignItems: "start" } },
        h(ComboboxField, {
          key: row.itemId,
          name: "item_id[]",
          label: "Item",
          options: itemOptions,
          defaultValue: row.itemId,
          placeholder: "Search…",
          quickAddUrl: P.itemQuickAddUrl,
          entityLabel: "item",
          onPick: (value, opt) => onChange(row.key, { itemId: value, rate: opt ? String(opt.sale_rate || 0) : row.rate }),
        }),
        h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty[]", value: row.qty, onChange: (e) => onChange(row.key, { qty: e.target.value }), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate[]", value: row.rate, onChange: (e) => onChange(row.key, { rate: e.target.value }), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Amount", value: money(amount), disabled: true }),
        h("div", { style: { paddingTop: 26 } }, h(IconButton, { icon: "x", label: "Remove line", size: "sm", onClick: onRemove }))
      ),
      overselling ? h("div", { style: { fontSize: "12.5px", color: "var(--red-600)" } }, "Only " + stock + " in stock.") : null
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
          const patch = { itemId: String(data.id), rate: String(data.sale_rate || 0), qty: (openRow && openRow.qty) || "1" };
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

    function onSubmit(e) {
      const warnings = rows.filter((r) => {
        const opt = itemOptions.find((o) => o.value === r.itemId);
        return opt && parseFloat(r.qty) > opt.stock_qty;
      });
      if (warnings.length && !window.confirm("This sale takes some items' stock below zero. Save anyway?")) {
        e.preventDefault();
      }
    }

    return h(
      React.Fragment,
      null,
      h(Card, { title: "Scan to add" }, h(BarcodeScanInput, { onScan: handleScan })),
      h(
        Card,
        { title: "New sale" },
        h(
          "form",
          { method: "post", action: P.nav.sales, onSubmit: onSubmit },
          h(CsrfField, null),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
            h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
            h(ComboboxField, { name: "party_id", label: "Customer", options: P.customers.map((c) => ({ value: String(c.id), label: c.name })), placeholder: "Walk-in (optional)…", quickAddUrl: P.customerQuickAddUrl, entityLabel: "customer" }),
            h(
              "div",
              { style: { display: "flex", flexDirection: "column", gap: "6px" } },
              h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
              h("input", { type: "hidden", name: "mode", value: mode }),
              h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash" }, { value: "Credit", label: "Credit" }] })
            )
          ),
          mode === "Credit" ? h(Banner, { tone: "info", style: { marginTop: "16px" } }, "This sale will be added to the customer's balance - pick a customer above.") : null,
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
            h(Button, { type: "submit", icon: "check" }, "Save Sale")
          )
        )
      ),
      h(
        Card,
        { title: "Add a new customer" },
        h(
          "form",
          { method: "post", action: P.addCustomerUrl, style: { display: "grid", gridTemplateColumns: "2fr 1fr 1fr auto", gap: "10px", alignItems: "end" } },
          h(CsrfField, null),
          h(Input, { label: "Name", name: "name", required: true }),
          h(Input, { label: "Phone", name: "phone" }),
          h(Input, { label: "Opening Balance", name: "opening_balance", type: "number", step: "0.01", defaultValue: "0" }),
          h(Button, { type: "submit", variant: "secondary" }, "Add Customer")
        )
      ),
      h(InvoiceList, {
        title: "Recent sales",
        invoices: P.invoices,
        emptyIcon: "receipt",
        emptyMessage: "No sales recorded yet.",
        printUrlBase: P.printUrlBase,
        editUrlBase: P.editTxnUrlBase,
        deleteUrlBase: P.deleteTxnUrlBase,
        canEdit: P.canEdit,
        isAdmin: P.isAdmin,
      })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "sales",
    topbar: { breadcrumb: "Kiryana", title: "Sale Book" },
    content: h(Root),
    navItems: window.KhatayDS.buildKiryanaNavItems(P, "sales"),
  });
})();
