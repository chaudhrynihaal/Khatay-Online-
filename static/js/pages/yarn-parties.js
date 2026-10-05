/* Parties list - wired to app.py's parties() route. Search round-trips
   through the server (real GET, same as the old page) rather than
   client-side filtering, so results always match what /reports and
   everywhere else consider "the" party list. Add Party posts through a
   real <form> to the unchanged POST /parties route - full page reload
   on save, exactly like every other mutation in this app. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, IconButton, Card, Badge, Dialog, DataTable, EmptyState } = DS;
  const { SearchField, Pagination } = DS;
  const { money, CsrfField, PartyFormFields } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const STATUS_TONE = { Receivable: "info", Payable: "warn", Settled: "ok" };

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.parties, style: { display: "flex", gap: "8px" } },
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Search by name, city or phone…", width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = P.nav.parties) }, "Clear") : null
    );
  }

  function AddPartyDialog({ open, onClose }) {
    return h(
      Dialog,
      { open: open, onClose: onClose, width: 640, title: "Add Party", description: "Add a customer, supplier, broker, expense head or bank account" },
      h(
        "form",
        { method: "post", action: P.nav.parties },
        h(CsrfField, null),
        h("div", { style: { maxHeight: "56vh", overflowY: "auto", paddingRight: "4px" } }, h(PartyFormFields, { party: null })),
        h(
          "div",
          { style: { display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "20px" } },
          h(Button, { type: "button", variant: "secondary", onClick: onClose }, "Cancel"),
          h(Button, { type: "submit", icon: "check" }, "Save Party")
        )
      )
    );
  }

  function partyColumns() {
    return [
      {
        key: "name",
        label: "Name",
        emphasis: true,
        width: 220,
        render: (r) => h("span", { style: { display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, r.name),
      },
      { key: "party_type", label: "Type", width: 100 },
      { key: "city", label: "City", width: 130, render: (r) => r.city || "—" },
      { key: "phone", label: "Phone", width: 140, render: (r) => r.phone || "—" },
      { key: "balance", label: "Balance", numeric: true, align: "right", width: 130, render: (r) => (r.balance === 0 ? "—" : money(r.balance)) },
      { key: "status", label: "Status", width: 120, render: (r) => h(Badge, { tone: STATUS_TONE[r.status] }, r.status) },
      {
        key: "actions",
        label: "",
        align: "right",
        width: 96,
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, {
              icon: "pencil",
              label: "Edit " + r.name,
              size: "sm",
              onClick: () => (window.location.href = P.nav.parties + "/" + r.id + "/edit"),
            }),
            r.has_history
              ? h(IconButton, {
                  icon: "trash-2",
                  label: "Delete " + r.name,
                  size: "sm",
                  disabledReason: "Can't delete — this party has transaction history",
                })
              : h(
                  "form",
                  {
                    method: "post",
                    action: P.nav.parties + "/" + r.id + "/delete",
                    onSubmit: (e) => {
                      if (!window.confirm("Delete this party?")) e.preventDefault();
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
    const parties = P.parties || [];
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "flex", justifyContent: "center", marginBottom: "20px" } },
        h(Button, { size: "lg", icon: "plus", onClick: () => setDialogOpen(true) }, "Add Party")
      ),
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, h(SearchBar)),
      h(
        Card,
        { padding: "none", footer: h(Pagination, { page: 1, pageCount: 1, rangeLabel: parties.length + (parties.length === 1 ? " party" : " parties") }) },
        parties.length === 0
          ? h(EmptyState, {
              icon: "users",
              title: P.searchQ ? 'No parties match "' + P.searchQ + '"' : "No parties yet",
              message: P.searchQ ? "Try a different search." : "Add your first customer or supplier to get started.",
            })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: partyColumns(), rows: parties, style: { tableLayout: "fixed" } }))
      ),
      h(AddPartyDialog, { open: dialogOpen, onClose: () => setDialogOpen(false) })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "parties",
    topbar: {
      breadcrumb: "Master Data",
      title: "Parties",
      subtitle: P.parties.length + " part" + (P.parties.length === 1 ? "y" : "ies"),
    },
    content: h(Root),
  });
})();
