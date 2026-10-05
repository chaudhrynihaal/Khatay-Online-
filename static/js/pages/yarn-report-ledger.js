/* Party Ledger - wired to app.py's report_ledger() route. Every entry
   for one chosen party (opening-entry-derived rows merged with real
   transactions, in date order) with a running balance, bookended by a
   synthetic Opening Balance row and a TOTAL row. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Select, DataTable, EmptyState } = DS;
  const { money, ExportButtons } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function PartyPicker() {
    return h(
      "form",
      { method: "get", action: P.nav.reportLedger, style: { display: "flex", gap: "10px", alignItems: "end", flexWrap: "wrap" } },
      h(Select, {
        label: "Party",
        name: "party_id",
        options: [{ value: "", label: "Select a party…" }].concat(P.parties.map((p) => ({ value: String(p.id), label: p.name + " (" + p.type + ")" }))),
        defaultValue: P.partyId ? String(P.partyId) : "",
        onChange: (e) => {
          const u = new URL(P.nav.reportLedger, window.location.origin);
          if (e.target.value) u.searchParams.set("party_id", e.target.value);
          window.location.href = u.pathname + u.search;
        },
        containerStyle: { minWidth: 280 },
      }),
      P.partyId ? h(ExportButtons, { pdfUrl: P.pdfUrl, excelUrl: P.excelUrl, params: { party_id: P.partyId } }) : null
    );
  }

  function PartyHeader() {
    const party = P.party;
    const cb = P.closingBalance;
    const label = cb > 0 ? "(Receivable)" : cb < 0 ? "(Payable)" : "(Settled)";
    const bits = [party.city, party.phone ? "Phone " + party.phone : null, party.ntn ? "NTN " + party.ntn : null].filter(Boolean);
    return h(
      Card,
      null,
      h(
        "div",
        { style: { display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" } },
        h(
          "div",
          null,
          h("div", { style: { fontSize: "16px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } }, party.name),
          h("div", { style: { fontSize: "13px", color: "var(--text-subtle)" } }, bits.join(" · "))
        ),
        h(
          "div",
          { style: { textAlign: "right" } },
          h("div", { style: { fontSize: "12px", color: "var(--text-subtle)" } }, "Closing Balance"),
          h(
            "div",
            { className: "tabular", style: { fontSize: "20px", fontWeight: "var(--fw-bold)", color: cb < 0 ? "var(--red-600)" : "var(--text-heading)" } },
            money(Math.abs(cb)),
            " ",
            h("span", { style: { fontSize: "12px", fontWeight: "var(--fw-medium)", color: "var(--text-subtle)" } }, label)
          )
        )
      )
    );
  }

  const TYPE_LABELS = {
    SALE: "Sale", PURCHASE: "Purchase", RECEIPT: "Receipt", PAYMENT: "Payment",
    EXPENSE: "Expense", CAPITAL_IN: "Capital In", CAPITAL_OUT: "Capital Out",
    CONTRA_DR: "Contra (Dr)", CONTRA_CR: "Contra (Cr)",
  };

  function columns() {
    return [
      { key: "date", label: "Date", render: (r) => (r._isOpening ? "" : r._isTotal ? "" : r.date) },
      { key: "ref", label: "Reference", render: (r) => (r._isOpening ? h("strong", null, "Opening Balance") : r._isTotal ? h("strong", null, "TOTAL") : r.ref) },
      { key: "type", label: "Type", render: (r) => (r._isOpening || r._isTotal ? "" : TYPE_LABELS[r.type] || r.type) },
      { key: "do_no", label: "D.O.#", render: (r) => (r._isOpening || r._isTotal ? "" : r.do_no || "—") },
      { key: "item", label: "Item", render: (r) => (r._isOpening || r._isTotal ? "" : r.item || "—") },
      { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => (r._isOpening || r._isTotal ? "" : r.qty || "—") },
      { key: "debit", label: "Debit", numeric: true, align: "right", render: (r) => (r._isOpening || r._isTotal ? (r._isTotal ? money(r.debit) : "") : r.debit ? money(r.debit) : "") },
      { key: "credit", label: "Credit", numeric: true, align: "right", render: (r) => (r._isOpening || r._isTotal ? (r._isTotal ? money(r.credit) : "") : r.credit ? money(r.credit) : "") },
      { key: "balance", label: "Balance", numeric: true, align: "right", emphasis: true, render: (r) => h("span", { style: { fontWeight: r._isOpening || r._isTotal ? "var(--fw-bold)" : undefined } }, money(r.balance)) },
    ];
  }

  function Root() {
    const party = P.party;
    let body;
    if (party) {
      const rows = [{ _isOpening: true, balance: party.opening_balance }]
        .concat(P.rows || [])
        .concat([{ _isTotal: true, debit: P.totalDebit, credit: P.totalCredit, balance: P.closingBalance }]);
      body = h(
        React.Fragment,
        null,
        h(PartyHeader),
        h(Card, { padding: "none", style: { marginTop: "16px" } }, h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: rows })))
      );
    } else if (P.partyId) {
      body = h(EmptyState, { title: "Party not found." });
    } else {
      body = h(EmptyState, { icon: "book-open", title: "Select a party above to see their complete ledger", message: "Every entry, in order, with a running balance." });
    }
    return h(React.Fragment, null, h(PartyPicker), body);
  }

  window.KhatayDS.mountShell({
    activeId: "report-ledger",
    topbar: { breadcrumb: "Reports", title: "Party Ledger" },
    content: h(Root),
  });
})();
