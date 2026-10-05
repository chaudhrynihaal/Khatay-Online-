/* Edit Party - wired to app.py's hardware_edit_party()/
   hardware_add_customer_price()/hardware_delete_customer_price()
   routes. party_type itself isn't editable (delete + re-add instead).
   The Special Pricing section only applies to Customers - it overrides
   an item's normal Sale Rate for this one customer, auto-applied on
   the Sale Book once both are picked (see hardware-sales.js). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Banner, DataTable, EmptyState, IconButton } = DS;
  const { money, CsrfField, ComboboxField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const party = P.party;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/").replace("/0", "/" + id);
  }

  function PartyForm() {
    return h(
      Card,
      { title: "Edit " + party.name, subtitle: (party.party_type === "Customer" ? "Customer" : "Supplier") + " · Balance " + money(P.balance) },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Input, { label: "Name", name: "name", defaultValue: party.name, required: true }),
          h(Input, { label: "Phone", name: "phone", defaultValue: party.phone || "" })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Opening Balance", name: "opening_balance", type: "number", step: "0.01", defaultValue: party.opening_balance }),
          party.party_type === "Customer"
            ? h(Input, { label: "Credit Limit", name: "credit_limit", type: "number", step: "0.01", defaultValue: party.credit_limit, hint: "0 = no limit; going over only warns, never blocks a sale" })
            : h("input", { type: "hidden", name: "credit_limit", value: "0" }),
          h(Input, { label: "GST Number", name: "gst_number", defaultValue: party.gst_number || "" })
        ),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.nav.parties + "?type=" + party.party_type) }, "Cancel")
        )
      )
    );
  }

  function AddPriceForm() {
    return h(
      "form",
      { method: "post", action: P.addPriceUrl, style: { display: "grid", gridTemplateColumns: "2fr 1fr auto", gap: "10px", alignItems: "end" } },
      h(CsrfField, null),
      h(ComboboxField, { name: "item_id", label: "Item", options: P.items.map((i) => ({ value: String(i.id), label: i.display_name || i.name })), placeholder: "Search…" }),
      h(Input, { label: "Rate", name: "rate", type: "number", step: "0.01", required: true }),
      h(Button, { type: "submit", variant: "secondary" }, "Add Special Price")
    );
  }

  function SpecialPricing() {
    const prices = P.prices || [];
    return h(
      Card,
      { title: "Special Pricing" },
      h(Banner, { tone: "info", style: { marginBottom: "16px" } }, "These override the item's normal Sale Rate for this customer only - auto-applied on the Sale Book once both are picked."),
      h(AddPriceForm),
      prices.length === 0
        ? h("div", { style: { marginTop: "16px" } }, h(EmptyState, { icon: "tag", title: "No special prices set." }))
        : h(
            "div",
            { style: { marginTop: "16px", overflowX: "auto" } },
            h(DataTable, {
              columns: [
                { key: "item_name", label: "Item", emphasis: true },
                { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => money(r.rate) },
                {
                  key: "actions",
                  label: "",
                  align: "right",
                  render: (r) =>
                    h(
                      "form",
                      { method: "post", action: urlFor(P.deletePriceUrlBase, r.id), onSubmit: (e) => { if (!window.confirm("Remove this special price?")) e.preventDefault(); } },
                      h(CsrfField, null),
                      h(IconButton, { icon: "trash-2", label: "Remove", size: "sm", type: "submit" })
                    ),
                },
              ],
              rows: prices,
            })
          )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "parties",
    topbar: { breadcrumb: "Hardware", title: "Edit Party" },
    content: h(React.Fragment, null, h(PartyForm), party.party_type === "Customer" ? h(SpecialPricing) : null),
    navItems: window.KhatayDS.buildHardwareNavItems(P, "parties"),
  });
})();
