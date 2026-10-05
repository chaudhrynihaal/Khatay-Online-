/* Quotations - wired to app.py's hardware_quotations()/
   hardware_convert_quotation() routes. A quotation is a real
   multi-line entry like a Sale, but with no Mode - it never touches
   stock or the Ledger (db.hardware_record_quotation_line stores
   mode="N/A") until explicitly converted into a real Sale, which
   creates a brand-new Cash-mode Sale from the same lines and flips
   these lines' txn_type to QUOTATION_CONVERTED (kept for history/
   reprint, dropped from this "open" list). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, IconButton, Banner } = DS;
  const { money, CsrfField, ComboboxField, InvoiceList } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/").replace("/0", "/" + id);
  }

  let nextRowKey = 1;
  function blankRow() {
    return { key: nextRowKey++, itemId: "", qty: "", rate: "" };
  }

  function baseItemOptions(extra) {
    return P.items.concat(extra).map((i) => ({ value: String(i.id), label: i.display_name || i.name, sale_rate: i.sale_rate }));
  }

  function LineRow({ row, itemOptions, onChange, onRemove }) {
    const qtyNum = parseFloat(row.qty) || 0;
    const amount = qtyNum * (parseFloat(row.rate) || 0);
    return h(
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
      h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty[]", value: row.qty, onChange: (e) => onChange(row.key, { qty: e.target.value }) }),
      h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate[]", value: row.rate, onChange: (e) => onChange(row.key, { rate: e.target.value }) }),
      h(Input, { label: "Amount", value: money(amount), disabled: true }),
      h("div", { style: { paddingTop: 26 } }, h(IconButton, { icon: "x", label: "Remove line", size: "sm", onClick: onRemove }))
    );
  }

  function QuotationForm() {
    const [rows, setRows] = React.useState([blankRow()]);
    const itemOptions = baseItemOptions([]);

    function updateRow(key, patch) {
      setRows((rs) => rs.map((r) => (r.key === key ? Object.assign({}, r, patch) : r)));
    }
    function addRow() {
      setRows((rs) => rs.concat([blankRow()]));
    }
    function removeRow(key) {
      setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.key !== key) : [blankRow()]));
    }

    const grandTotal = rows.reduce((s, r) => s + (parseFloat(r.qty) || 0) * (parseFloat(r.rate) || 0), 0);

    return h(
      Card,
      { title: "New quotation" },
      h(Banner, { tone: "info", style: { marginBottom: "16px" } }, "A quotation doesn't touch stock or the Ledger - nothing happens until you convert it into a real Sale."),
      h(
        "form",
        { method: "post", action: P.nav.quotations },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(ComboboxField, { name: "party_id", label: "Customer", options: P.customers.map((c) => ({ value: String(c.id), label: c.name })), placeholder: "Walk-in (optional)…", quickAddUrl: P.customerQuickAddUrl, entityLabel: "customer" })
        ),
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
          h(Button, { type: "submit", icon: "check" }, "Save Quotation")
        )
      )
    );
  }

  function ConvertButton(inv) {
    return h(
      "form",
      {
        method: "post",
        action: urlFor(P.convertUrlBase, inv.invoice_no),
        onClick: (e) => e.stopPropagation(),
        onSubmit: (e) => {
          if (!window.confirm("Convert this quotation into a real Sale? Stock and the Ledger will update.")) e.preventDefault();
        },
      },
      h(CsrfField, null),
      h(Button, { type: "submit", size: "sm", icon: "arrow-right-left" }, "Convert to Sale")
    );
  }

  function Root() {
    return h(
      React.Fragment,
      null,
      h(QuotationForm),
      h(InvoiceList, {
        title: "Open quotations",
        invoices: P.openQuotations,
        emptyIcon: "file-text",
        emptyMessage: "No open quotations.",
        printUrlBase: P.printUrlBase,
        editUrlBase: P.editTxnUrlBase,
        deleteUrlBase: P.deleteTxnUrlBase,
        canEdit: P.canEdit,
        isAdmin: P.isAdmin,
        renderRowExtra: ConvertButton,
      })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "quotations",
    topbar: { breadcrumb: "Hardware", title: "Quotations" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "quotations"),
  });
})();
