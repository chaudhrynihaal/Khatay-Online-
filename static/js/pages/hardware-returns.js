/* Returns - wired to app.py's hardware_returns() route. A single-line
   return (not a multi-line builder like Sales/Purchases), optionally
   started from an existing bill: pick a bill from "Return against a
   bill" and either it auto-fills (single-line bill) or a small picker
   of that bill's lines appears to choose which one. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Tabs, Banner, Combobox } = DS;
  const { money, CsrfField, ComboboxField, Segmented, InvoiceList, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function switchType(type) {
    const u = new URL(P.nav.returns, window.location.origin);
    u.searchParams.set("type", type);
    window.location.href = u.pathname + u.search;
  }

  function ReturnForm() {
    const isSale = P.returnType === "Sale";
    const parties = isSale ? P.customers : P.suppliers;
    const partyLabel = isSale ? "Customer" : "Supplier";
    const rateKey = isSale ? "sale_rate" : "purchase_rate";
    const itemOptions = P.items.map((i) => ({ value: String(i.id), label: i.display_name || i.name, rate: i[rateKey] }));

    const [itemId, setItemId] = React.useState("");
    const [partyId, setPartyId] = React.useState("");
    const [qty, setQty] = React.useState("");
    const [rate, setRate] = React.useState("");
    const [mode, setMode] = React.useState("Cash");
    const [sourceBillId, setSourceBillId] = React.useState("");
    const [linePicker, setLinePicker] = React.useState(null); // lines array when a multi-line bill was picked
    const [formKey, setFormKey] = React.useState(0); // bump to force item/party comboboxes to re-seed from state

    function fillFromLine(line, bill) {
      setItemId(String(line.item_id));
      setQty(String(line.qty));
      setRate(String(line.rate));
      if (bill && bill.party_id) setPartyId(String(bill.party_id));
      setLinePicker(null);
      setFormKey((k) => k + 1);
    }

    function onSourceBillChange(billId) {
      setSourceBillId(billId);
      const bill = P.sourceBills.find((b) => String(b.invoice_no) === billId || (b.invoice_no == null && "single-" + b.lines[0].id === billId));
      if (!bill) return;
      if (bill.lines.length === 1) {
        fillFromLine(bill.lines[0], bill);
      } else {
        setLinePicker({ bill: bill });
      }
    }

    const sourceBillOptions = P.sourceBills.map((b) => ({
      value: b.invoice_no != null ? String(b.invoice_no) : "single-" + b.lines[0].id,
      label: b.invoice + " — " + (b.party || "Walk-in") + " (" + window.KhatayDS.money(b.total_amount) + ")",
    }));

    const amount = (parseFloat(qty) || 0) * (parseFloat(rate) || 0);

    return h(
      React.Fragment,
      null,
      h(
        Card,
        { title: "Return against a bill" },
        h(Combobox, { label: "Source bill", options: sourceBillOptions, value: sourceBillId, onChange: onSourceBillChange, placeholder: "Search a past " + P.returnType.toLowerCase() + "…" }),
        linePicker
          ? h(
              "div",
              { style: { marginTop: "12px", display: "flex", flexDirection: "column", gap: "6px" } },
              h("div", { style: { fontSize: "12.5px", color: "var(--text-subtle)" } }, "This bill has multiple items - pick one:"),
              linePicker.bill.lines.map((line) =>
                h(
                  "button",
                  {
                    key: line.id,
                    type: "button",
                    onClick: () => fillFromLine(line, linePicker.bill),
                    style: { textAlign: "left", padding: "8px 10px", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-sm)", background: "var(--surface-card)", cursor: "pointer", fontSize: "13.5px" },
                  },
                  line.item + " — " + line.qty + " @ " + money(line.rate) + " = " + money(line.amount)
                )
              )
            )
          : null
      ),
      h(
        Card,
        { title: "Return details" },
        h(
          "form",
          { key: formKey, method: "post", action: P.nav.returns },
          h(CsrfField, null),
          h("input", { type: "hidden", name: "return_type", value: P.returnType }),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
            h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
            h(ComboboxField, { name: "item_id", label: "Item", options: itemOptions, defaultValue: itemId, required: true, placeholder: "Search…", onPick: (v, opt) => setRate(opt ? String(opt.rate || 0) : "") }),
            h(ComboboxField, { name: "party_id", label: partyLabel, options: parties.map((p) => ({ value: String(p.id), label: p.name })), defaultValue: partyId, placeholder: "Search…" })
          ),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
            h(Input, { label: "Qty", type: "number", step: "0.01", name: "qty", value: qty, onChange: (e) => setQty(e.target.value), required: true, onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Rate", type: "number", step: "0.01", name: "rate", value: rate, onChange: (e) => setRate(e.target.value), required: true, onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Amount", value: money(amount), disabled: true })
          ),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
            h(
              "div",
              { style: { display: "flex", flexDirection: "column", gap: "6px" } },
              h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
              h("input", { type: "hidden", name: "mode", value: mode }),
              h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash refund" }, { value: "Credit", label: "Credit note" }] })
            ),
            h(Input, { label: "Reason / Description", name: "description" })
          ),
          mode === "Credit" ? h(Banner, { tone: "info", style: { marginTop: "16px" } }, "This will reduce what the " + partyLabel.toLowerCase() + " owes/is owed - pick one above.") : null,
          h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save " + P.returnType + " Return"))
        )
      )
    );
  }

  function Root() {
    return h(
      React.Fragment,
      null,
      h(Tabs, {
        value: P.returnType,
        onChange: switchType,
        items: [{ id: "Sale", label: "Sale Return" }, { id: "Purchase", label: "Purchase Return" }],
      }),
      h(ReturnForm),
      h(InvoiceList, {
        title: "Recent " + P.returnType.toLowerCase() + " returns",
        invoices: P.invoices,
        emptyIcon: "undo-2",
        emptyMessage: "No " + P.returnType.toLowerCase() + " returns recorded yet.",
        printUrlBase: P.returnType === "Sale" ? P.printUrlBase : P.purchasePrintUrlBase,
        editUrlBase: P.editTxnUrlBase,
        deleteUrlBase: P.deleteTxnUrlBase,
        canEdit: P.canEdit,
        isAdmin: P.isAdmin,
      })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "returns",
    topbar: { breadcrumb: "Hardware", title: "Returns" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "returns"),
  });
})();
