/* Import Your Existing Data - wired to app.py's data_import_page()/
   data_import_parties()/data_import_quality()/data_import_opening_entries()
   routes. Three real multipart file-upload forms; each posts natively
   and redirects back to a real list page (Parties/Quality import) or
   back to this page (Opening Entries import) with the result as a
   flash message - unchanged server-side behavior. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Button, Banner } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function labelStyle() {
    return { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" };
  }

  function ImportStep({ title, description, templateUrl, importUrl, submitLabel, note }) {
    return h(
      Card,
      { title: title },
      description ? h("p", { style: { fontSize: "13.5px", color: "var(--text-subtle)", marginTop: 0 } }, description) : null,
      note ? h(Banner, { tone: "info", style: { marginBottom: "16px" } }, note) : null,
      h(
        "div",
        { style: { marginBottom: "14px" } },
        h(Button, { variant: "secondary", size: "sm", icon: "download", onClick: () => window.open(templateUrl, "_blank") }, "Download Template (Excel)")
      ),
      h(
        "form",
        { method: "post", action: importUrl, encType: "multipart/form-data", style: { display: "flex", gap: "10px", alignItems: "end" } },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "6px", flex: 1 } },
          h("label", { style: labelStyle() }, "Filled-in file (.xlsx or .csv)"),
          h("input", { type: "file", name: "file", accept: ".xlsx,.csv", required: true })
        ),
        h(Button, { type: "submit" }, submitLabel)
      )
    );
  }

  function Root() {
    return h(
      React.Fragment,
      null,
      h(
        Card,
        null,
        h(
          "p",
          { style: { fontSize: "13.5px", color: "var(--text-subtle)", margin: 0 } },
          "Moving from another system? Bring your customers, suppliers, brokers, and items over in one go, along with their current balances - instead of typing everything in one at a time. This brings in your ",
          h("strong", null, "master data and current balances"),
          ", not old individual invoices - set the right starting point here, then everything from today forward gets entered normally in the app."
        ),
        h("p", { style: { fontSize: "13px", color: "var(--text-subtle)", margin: "10px 0 0" } }, "Already-existing names are automatically skipped, so it's always safe to re-upload a corrected file.")
      ),
      h(ImportStep, {
        title: "Step 1 — Parties (customers, suppliers, brokers)",
        templateUrl: P.partiesTemplateUrl,
        importUrl: P.importPartiesUrl,
        submitLabel: "Import Parties",
      }),
      h(ImportStep, {
        title: "Step 2 — Items / Quality (with current stock)",
        templateUrl: P.qualityTemplateUrl,
        importUrl: P.importQualityUrl,
        submitLabel: "Import Items",
      }),
      h(ImportStep, {
        title: "Step 3 — Outstanding Invoices (Receivable / Payable detail)",
        templateUrl: P.openingEntriesTemplateUrl,
        importUrl: P.importOpeningEntriesUrl,
        submitLabel: "Import Outstanding Invoices",
        note:
          "Optional, but recommended - instead of just one lump-sum \"opening balance\" per party, list every individual invoice or bill that's still unpaid. This carries the real detail forward: what was sold, to whom, when, and how much of it is still outstanding - so your Receivable and Payable Ledgers show the actual breakdown from day one, not just one opaque total per party. Import your Parties first (Step 1) - this step needs the party names to already exist.",
      }),
      h(
        Card,
        { title: "A note on Opening Balance" },
        h(
          "p",
          { style: { fontSize: "13.5px", color: "var(--text-subtle)", margin: 0 } },
          "For parties: a ",
          h("strong", null, "positive"),
          " Opening Balance means they owe you money (receivable) - the same as your old software probably showed a customer's outstanding balance. A ",
          h("strong", null, "negative"),
          " number means you owe them (payable) - typical for a supplier balance. For items: Opening Balance is simply how much stock you currently have on hand, right now. If you use Step 3 above for a party, its detailed invoices are shown instead of the single Opening Balance number for that party - no need to fill in both for the same party."
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "import",
    topbar: { breadcrumb: "Master Data", title: "Import Your Existing Data" },
    content: h(Root),
  });
})();
