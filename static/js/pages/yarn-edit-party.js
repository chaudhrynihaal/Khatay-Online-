/* Edit Party - wired to app.py's edit_party()/clear_opening_entries()
   routes. Same field set as the Add Party dialog (shared
   KhatayDS.PartyFormFields), prefilled from the real party record. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, Banner } = DS;
  const { CsrfField, PartyFormFields } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function EditPartyForm() {
    return h(
      Card,
      { padding: "lg" },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(PartyFormFields, { party: P.party }),
        h(
          "div",
          { style: { display: "flex", gap: "8px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.nav.parties) }, "Cancel")
        )
      )
    );
  }

  function OpeningEntriesCard() {
    if (P.openingCount <= 0) return null;
    const { money } = window.KhatayDS;
    return h(
      Card,
      { title: "Imported Outstanding Invoices" },
      h(
        Banner,
        { tone: "warn" },
        "This party has " +
          P.openingCount +
          (P.openingCount === 1 ? " imported outstanding invoice" : " imported outstanding invoices") +
          ", totaling " +
          money(P.openingTotal) +
          ". These show individually in the Receivable/Payable Ledger and Party Ledger. This is also why this party can't be deleted right now — remove them below first if you need to."
      ),
      P.isAdmin
        ? h(
            "form",
            {
              method: "post",
              action: P.clearOpeningEntriesUrl,
              style: { marginTop: "14px" },
              onSubmit: (e) => {
                if (
                  !window.confirm(
                    "Remove all " + P.openingCount + " imported outstanding invoices for " + P.party.name + "? This cannot be undone, though you can always re-upload the import file if needed."
                  )
                ) {
                  e.preventDefault();
                }
              },
            },
            h(CsrfField, null),
            h(Button, { type: "submit", variant: "danger", size: "sm" }, "Remove All Imported Invoices for This Party")
          )
        : null
    );
  }

  window.KhatayDS.mountShell({
    activeId: "parties",
    topbar: {
      breadcrumb: "Master Data · Parties",
      title: "Edit " + P.party.name,
      subtitle: P.party.party_type,
    },
    content: h(React.Fragment, null, h(EditPartyForm), h(OpeningEntriesCard)),
  });
})();
