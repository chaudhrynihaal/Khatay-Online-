/* Customers & Suppliers - wired to app.py's hardware_parties()/
   hardware_delete_party() routes. No add-party form here (unlike Yarn's
   Parties page) - new customers/suppliers are still added inline via
   the quick-add mini-forms on Sale Book/Purchase List, matching the old
   page's design; this is purely the browse/manage view. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Tabs, DataTable, EmptyState, IconButton, Badge } = DS;
  const { money, CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function switchType(type) {
    const u = new URL(P.nav.parties, window.location.origin);
    u.searchParams.set("type", type);
    window.location.href = u.pathname + u.search;
  }

  function columns() {
    const cols = [
      { key: "name", label: "Name", emphasis: true },
      { key: "phone", label: "Phone", render: (r) => r.phone || "—" },
      {
        key: "balance",
        label: "Balance",
        numeric: true,
        align: "right",
        render: (r) => h("span", { style: { color: r.balance > 0 ? "var(--red-600)" : undefined, fontWeight: r.balance > 0 ? "var(--fw-semibold)" : undefined } }, money(r.balance)),
      },
    ];
    if (P.partyType === "Customer") {
      cols.push({
        key: "credit_limit",
        label: "Credit Limit",
        numeric: true,
        align: "right",
        render: (r) => h("span", { style: { color: r.credit_limit > 0 && r.balance > r.credit_limit ? "var(--red-600)" : undefined } }, r.credit_limit > 0 ? money(r.credit_limit) : "—"),
      });
    }
    cols.push(
      { key: "gst_number", label: "GST No.", render: (r) => r.gst_number || "—" },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, { icon: "book-user", label: "Ledger for " + r.name, size: "sm", onClick: () => (window.location.href = P.nav.ledger + "?type=" + P.partyType + "&party_id=" + r.id) }),
            h(IconButton, { icon: "pencil", label: "Edit " + r.name, size: "sm", onClick: () => (window.location.href = urlFor(P.editPartyUrlBase, r.id)) }),
            h(
              "form",
              {
                method: "post",
                action: urlFor(P.deletePartyUrlBase, r.id),
                style: { display: "inline" },
                onSubmit: (e) => {
                  if (!window.confirm("Delete this " + P.partyType.toLowerCase() + "?")) e.preventDefault();
                },
              },
              h(CsrfField, null),
              h(IconButton, { icon: "trash-2", label: "Delete " + r.name, size: "sm", type: "submit" })
            )
          ),
      }
    );
    return cols;
  }

  function Root() {
    const parties = P.parties || [];
    return h(
      React.Fragment,
      null,
      h(Tabs, { value: P.partyType, onChange: switchType, items: [{ id: "Customer", label: "Customers" }, { id: "Supplier", label: "Suppliers" }] }),
      h(
        Card,
        { padding: "none" },
        parties.length === 0
          ? h(EmptyState, {
              icon: "users",
              title: "No " + P.partyType.toLowerCase() + "s yet",
              message: "Add one from the " + (P.partyType === "Customer" ? "Sale Book" : "Purchase List") + " page.",
            })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: parties }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "parties",
    topbar: { breadcrumb: "Hardware", title: "Customers & Suppliers" },
    content: h(Root),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "parties"),
  });
})();
