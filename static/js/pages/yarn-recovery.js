/* Receipt & Payment - wired to app.py's recovery() route. Three modes:
   Cash (the sign typed into Amount picks Receipt vs Payment - the Type
   control is just a live readout, matching the server which ignores
   the submitted voucher_type entirely in this mode), Cheque (an
   explicit Receipt/Payment choice, one voucher covering a repeatable
   list of individual cheque lines whose amounts sum to the total), and
   Contra (an internal balance transfer between 2+ parties/accounts,
   e.g. Cash to Bank - no real cash movement, total Dr must equal total
   Cr). Cash/Cheque submit to the unchanged /recovery route; Contra
   submits to the unchanged /contra route instead (same <form>, just a
   different action/fields depending on Mode) - contra entries used to
   live on their own separate page, now they're just another Mode here.
   Cheque lines are serialized as real hidden inputs
   (cheque_date[]/cheque_bank[]/cheque_no[]/cheque_amount[]), contra
   legs the same way (party_id[]/direction[]/amount[]) - not a
   client-side fetch either way. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, IconButton, DataTable, EmptyState, Banner, Input, Combobox, Badge } = DS;
  const { SearchField, Pagination } = DS;
  const { money, CsrfField, ComboboxField, Segmented, editUrlWithReturn, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const partyOptions = P.parties.map((p) => ({ value: String(p.id), label: p.name, meta: p.type }));

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function ChequeLines({ rows, onAdd, onRemove }) {
    const [draft, setDraft] = React.useState({ date: P.today, bank: "", cheque_no: "", amount: "" });
    const total = rows.reduce((s, r) => s + r.amount, 0);

    function set(field) {
      return (e) => setDraft((d) => Object.assign({}, d, { [field]: e.target.value }));
    }

    function add() {
      const amt = parseFloat(draft.amount);
      if (!amt || amt <= 0) {
        window.alert("Enter a valid cheque amount.");
        return;
      }
      onAdd({ date: draft.date, bank: draft.bank, cheque_no: draft.cheque_no, amount: amt });
      setDraft({ date: P.today, bank: "", cheque_no: "", amount: "" });
    }

    return h(
      "div",
      { style: { padding: "14px 16px", background: "var(--surface-brand-soft)", border: "1px dashed var(--indigo-100)", borderRadius: "var(--radius-md)", display: "flex", flexDirection: "column", gap: "12px" } },
      h("div", { style: { fontSize: "14px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, "Cheque lines"),
      h("div", { style: { fontSize: "12.5px", color: "var(--text-subtle)", marginTop: "-8px" } }, "Add every cheque covered by this one voucher - the total is always their sum."),
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr auto", gap: "10px", alignItems: "end" } },
        h(Input, { label: "Date", type: "date", value: draft.date, onChange: set("date"), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Bank", value: draft.bank, onChange: set("bank"), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Cheque #", value: draft.cheque_no, onChange: set("cheque_no"), onKeyDown: focusNextOnEnter }),
        h(Input, { label: "Amount", type: "number", step: "0.01", value: draft.amount, onChange: set("amount"), onKeyDown: focusNextOnEnter }),
        h(Button, { type: "button", size: "sm", icon: "plus", onClick: add }, "Add")
      ),
      rows.length
        ? h(
            "table",
            { style: { width: "100%", borderCollapse: "collapse", fontSize: "13px" } },
            h(
              "thead",
              null,
              h(
                "tr",
                null,
                ["Date", "Bank", "Cheque #", "Amount", ""].map((label) =>
                  h("th", { key: label, style: { textAlign: label === "Amount" ? "right" : "left", padding: "6px 8px", color: "var(--text-subtle)", fontWeight: "var(--fw-medium)" } }, label)
                )
              )
            ),
            h(
              "tbody",
              null,
              rows.map((r, i) =>
                h(
                  "tr",
                  { key: i, style: { borderTop: "1px solid var(--border-subtle)" } },
                  h("td", { style: { padding: "6px 8px" } }, r.date),
                  h("td", { style: { padding: "6px 8px" } }, r.bank || "—"),
                  h("td", { style: { padding: "6px 8px" } }, r.cheque_no || "—"),
                  h("td", { style: { padding: "6px 8px", textAlign: "right" } }, money(r.amount)),
                  h("td", { style: { padding: "6px 8px", textAlign: "right" } }, h(IconButton, { icon: "x", label: "Remove", size: "sm", onClick: () => onRemove(i) }))
                )
              )
            )
          )
        : null,
      h("div", { style: { textAlign: "right", fontSize: "14px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, "Total: " + money(total)),
      rows.map((r, i) =>
        h(
          React.Fragment,
          { key: i },
          h("input", { type: "hidden", name: "cheque_date[]", value: r.date }),
          h("input", { type: "hidden", name: "cheque_bank[]", value: r.bank }),
          h("input", { type: "hidden", name: "cheque_no[]", value: r.cheque_no }),
          h("input", { type: "hidden", name: "cheque_amount[]", value: r.amount })
        )
      )
    );
  }

  function ContraLegsBuilder({ legs, onAdd, onRemove }) {
    const [partyId, setPartyId] = React.useState("");
    const [direction, setDirection] = React.useState("DR");
    const [amount, setAmount] = React.useState("");

    const totalDr = legs.filter((l) => l.direction === "DR").reduce((s, l) => s + l.amount, 0);
    const totalCr = legs.filter((l) => l.direction === "CR").reduce((s, l) => s + l.amount, 0);
    const balanced = legs.length >= 2 && Math.abs(totalDr - totalCr) < 0.01;

    function add() {
      if (!partyId) {
        window.alert("Select a party.");
        return;
      }
      const amt = parseFloat(amount);
      if (!amt || amt <= 0) {
        window.alert("Enter a valid amount.");
        return;
      }
      const opt = partyOptions.find((o) => o.value === partyId);
      onAdd({ partyId, partyName: opt ? opt.label : "", direction, amount: amt });
      setPartyId("");
      setAmount("");
    }

    return h(
      "div",
      { style: { padding: "14px 16px", background: "var(--surface-brand-soft)", border: "1px dashed var(--indigo-100)", borderRadius: "var(--radius-md)", display: "flex", flexDirection: "column", gap: "12px" } },
      h("div", { style: { fontSize: "14px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, "Contra legs"),
      h("div", { style: { fontSize: "12.5px", color: "var(--text-subtle)", marginTop: "-8px" } }, "Add at least two parties/accounts - total Dr must equal total Cr."),
      legs.length
        ? h(
            "table",
            { style: { width: "100%", borderCollapse: "collapse", fontSize: "13px" } },
            h(
              "thead",
              null,
              h(
                "tr",
                null,
                ["Party", "Impact", "Amount", ""].map((label) =>
                  h("th", { key: label, style: { textAlign: label === "Amount" ? "right" : "left", padding: "6px 8px", color: "var(--text-subtle)", fontWeight: "var(--fw-medium)" } }, label)
                )
              )
            ),
            h(
              "tbody",
              null,
              legs.map((l, i) =>
                h(
                  "tr",
                  { key: i, style: { borderTop: "1px solid var(--border-subtle)" } },
                  h("td", { style: { padding: "6px 8px" } }, l.partyName),
                  h("td", { style: { padding: "6px 8px" } }, h(Badge, { tone: l.direction === "DR" ? "info" : "warn" }, l.direction === "DR" ? "Dr (increase)" : "Cr (decrease)")),
                  h("td", { style: { padding: "6px 8px", textAlign: "right" } }, money(l.amount)),
                  h("td", { style: { padding: "6px 8px", textAlign: "right" } }, h(IconButton, { icon: "x", label: "Remove", size: "sm", onClick: () => onRemove(i) }))
                )
              )
            )
          )
        : null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "2fr 1.4fr 1fr auto", gap: "10px", alignItems: "end" } },
        h(Combobox, { label: "Party", options: partyOptions, value: partyId, onChange: setPartyId, placeholder: "Search…" }),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "6px" } },
          h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Impact"),
          h(Segmented, { value: direction, onChange: setDirection, options: [{ value: "DR", label: "Dr (increase)" }, { value: "CR", label: "Cr (decrease)" }] })
        ),
        h(Input, { label: "Amount", type: "number", step: "0.01", value: amount, onChange: (e) => setAmount(e.target.value), onKeyDown: focusNextOnEnter }),
        h(Button, { type: "button", icon: "plus", onClick: add }, "Add Party")
      ),
      h(
        "div",
        { style: { display: "flex", alignItems: "center", gap: "20px", fontSize: "14px" } },
        h("span", null, "Total Dr: ", h("strong", { className: "tabular" }, money(totalDr))),
        h("span", null, "Total Cr: ", h("strong", { className: "tabular" }, money(totalCr))),
        legs.length > 0
          ? h(Badge, { tone: balanced ? "ok" : "danger" }, balanced ? "Balanced" : "Not balanced yet")
          : null
      ),
      legs.map((l, i) =>
        h(
          React.Fragment,
          { key: i },
          h("input", { type: "hidden", name: "party_id[]", value: l.partyId }),
          h("input", { type: "hidden", name: "direction[]", value: l.direction }),
          h("input", { type: "hidden", name: "amount[]", value: l.amount })
        )
      )
    );
  }

  function EntryForm() {
    const [mode, setMode] = React.useState("Cash");
    const [voucherType, setVoucherType] = React.useState("RECEIPT");
    const [cashAmount, setCashAmount] = React.useState("");
    const [chequeRows, setChequeRows] = React.useState([]);
    const [contraLegs, setContraLegs] = React.useState([]);
    const isCheque = mode === "Cheque";
    const isContra = mode === "Contra";
    const autoType = parseFloat(cashAmount) < 0 ? "Payment" : "Receipt";

    function onSubmit(e) {
      if (isCheque && chequeRows.length === 0) {
        e.preventDefault();
        window.alert("Add at least one cheque, or switch Mode to Cash.");
        return;
      }
      if (isContra) {
        const totalDr = contraLegs.filter((l) => l.direction === "DR").reduce((s, l) => s + l.amount, 0);
        const totalCr = contraLegs.filter((l) => l.direction === "CR").reduce((s, l) => s + l.amount, 0);
        if (contraLegs.length < 2) {
          e.preventDefault();
          window.alert("Add at least two parties.");
        } else if (Math.abs(totalDr - totalCr) > 0.01) {
          e.preventDefault();
          window.alert("Total Debit must equal total Credit before saving.");
        }
      }
    }

    return h(
      Card,
      { title: "New entry" },
      h(
        "form",
        { method: "post", action: isContra ? P.nav.contra : P.nav.recovery, onSubmit: onSubmit },
        h(CsrfField, null),
        !isContra ? h("input", { type: "hidden", name: "mode", value: mode }) : null,
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px" } },
          h(
            "div",
            { style: { display: "flex", flexDirection: "column", gap: "6px" } },
            h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
            h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash" }, { value: "Cheque", label: "Cheque" }, { value: "Contra", label: "Contra" }] })
          ),
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true, onKeyDown: focusNextOnEnter }),
          isContra
            ? null
            : h(ComboboxField, {
                name: "party_id",
                label: "Party",
                options: partyOptions,
                required: true,
                placeholder: "Search…",
                quickAddUrl: P.partyQuickAddUrl,
                entityLabel: "party",
                extraCreateFields: { party_type: (isCheque ? voucherType : autoType.toUpperCase()) === "PAYMENT" ? "Supplier" : "Customer" },
              })
        ),
        isContra
          ? h(Banner, { tone: "info", style: { marginTop: "16px" } }, "An internal balance transfer between 2+ parties/accounts (e.g. Cash to Bank) - no real cash movement, total Dr must equal total Cr. Doesn't appear in the Cash Book.")
          : null,
        isCheque
          ? h(
              "div",
              { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
              h(
                "div",
                { style: { display: "flex", flexDirection: "column", gap: "6px" } },
                h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Type"),
                h(Segmented, { value: voucherType, onChange: setVoucherType, options: [{ value: "RECEIPT", label: "Receipt" }, { value: "PAYMENT", label: "Payment" }] })
              ),
              h(Input, { label: "Description", name: "description", onKeyDown: focusNextOnEnter })
            )
          : isContra
          ? null
          : h(
              "div",
              { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
              h(Input, {
                label: "Amount",
                hint: "Positive = Receipt, negative = Payment (set automatically as " + autoType + ")",
                name: "amount",
                type: "number",
                step: "0.01",
                value: cashAmount,
                onChange: (e) => setCashAmount(e.target.value),
                required: true,
                onKeyDown: focusNextOnEnter,
              }),
              h(Input, { label: "Description", name: "description", onKeyDown: focusNextOnEnter })
            ),
        !isContra
          ? isCheque
            ? h("input", { type: "hidden", name: "voucher_type", value: voucherType })
            : h("input", { type: "hidden", name: "voucher_type", value: "RECEIPT" })
          : null,
        isCheque
          ? h("div", { style: { marginTop: "16px" } }, h(ChequeLines, { rows: chequeRows, onAdd: (r) => setChequeRows((rows) => rows.concat([r])), onRemove: (i) => setChequeRows((rows) => rows.filter((_, idx) => idx !== i)) }))
          : null,
        isContra
          ? h(
              "div",
              { style: { marginTop: "16px" } },
              h(ContraLegsBuilder, { legs: contraLegs, onAdd: (l) => setContraLegs((rows) => rows.concat([l])), onRemove: (i) => setContraLegs((rows) => rows.filter((_, idx) => idx !== i)) }),
              h(Input, { label: "Description", name: "description", containerStyle: { marginTop: "16px" } })
            )
          : null,
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, isContra ? "Save Contra Entry" : "Save Entry"))
      )
    );
  }

  function SavedBanner() {
    if (!P.savedVoucher) return null;
    return h(Banner, {
      tone: "ok",
      title: "Saved as " + P.savedVoucher.voucher + " - ready for your next entry.",
      action: h(Button, { size: "sm", variant: "secondary", onClick: () => window.open(urlFor(P.printVoucherUrlBase, P.savedVoucher.id), "_blank") }, "Print This Voucher"),
    });
  }

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.recovery, style: { display: "flex", gap: "8px" } },
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Find by party, voucher #, or description…", width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = P.nav.recovery) }, "Clear") : null
    );
  }

  function recentColumns() {
    return [
      { key: "voucher", label: "Voucher #", emphasis: true },
      { key: "date", label: "Date" },
      {
        key: "type", label: "Type",
        render: (r) => (r.type === "CONTRA_DR" ? "Contra (Dr)" : r.type === "CONTRA_CR" ? "Contra (Cr)" : r.type === "RECEIPT" ? "Receipt" : "Payment"),
      },
      { key: "party", label: "Party", render: (r) => r.party || "—" },
      { key: "mode", label: "Mode" },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      { key: "description", label: "Description", render: (r) => r.description || "—" },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) => {
          // a contra entry is 2+ paired rows sharing one voucher - print/
          // edit/delete all assume a single self-contained transaction,
          // so none of those are offered here (unlike Receipt/Payment)
          if (r.type === "CONTRA_DR" || r.type === "CONTRA_CR") return null;
          return h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, { icon: "printer", label: "Print " + r.voucher, size: "sm", onClick: () => window.open(urlFor(P.printVoucherUrlBase, r.id), "_blank") }),
            P.canEdit
              ? h(IconButton, { icon: "pencil", label: "Edit " + r.voucher, size: "sm", onClick: () => (window.location.href = editUrlWithReturn(P.editTransactionUrlBase, r.id)) })
              : null,
            P.isAdmin
              ? h(
                  "form",
                  {
                    method: "post",
                    action: urlFor(P.deleteTransactionUrlBase, r.id),
                    onSubmit: (e) => {
                      if (!window.confirm("Delete this entry?")) e.preventDefault();
                    },
                  },
                  h(CsrfField, null),
                  h(IconButton, { icon: "trash-2", label: "Delete " + r.voucher, size: "sm", type: "submit" })
                )
              : null
          );
        },
      },
    ];
  }

  function Root() {
    const recent = P.recent || [];
    return h(
      React.Fragment,
      null,
      h(SavedBanner),
      h(EntryForm),
      h(SearchBar),
      h(
        Card,
        { title: P.searchQ ? "Search results" : "Recent entries", padding: "none", footer: h(Pagination, { page: 1, pageCount: 1, rangeLabel: recent.length + (recent.length === 1 ? " entry" : " entries") }) },
        recent.length === 0
          ? h(EmptyState, { icon: "banknote", title: P.searchQ ? 'No entries match "' + P.searchQ + '"' : "No entries yet" })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: recentColumns(), rows: recent }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "recovery",
    topbar: { breadcrumb: "Entry", title: "Receipt & Payment" },
    content: h(Root),
  });
})();
