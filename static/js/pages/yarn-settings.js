/* Settings - wired to app.py's company_settings() route. One real
   multipart <form> covering four sections (Company, Color theme,
   Opening Cash Balance, Daily Email Reports) exactly like the old
   page - the color theme still matters even though the new UI doesn't
   use it: pdf_export.py/voucher_print.py read it for every printed
   invoice/voucher's color scheme. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Banner } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function labelStyle() {
    return { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" };
  }

  function ThemeSwatches() {
    const [theme, setTheme] = React.useState(P.theme);
    return h(
      Card,
      { title: "Color theme" },
      h("input", { type: "hidden", name: "theme", value: theme }),
      h(
        "div",
        { style: { display: "flex", flexWrap: "wrap", gap: "10px" } },
        Object.entries(P.themes).map(([name, palette]) =>
          h(
            "button",
            {
              key: name,
              type: "button",
              onClick: () => setTheme(name),
              style: {
                width: 92,
                height: 60,
                borderRadius: "var(--radius-md)",
                border: theme === name ? "2px solid var(--indigo-600)" : "2px solid transparent",
                background: palette.primary,
                color: "#fff",
                fontSize: "12px",
                fontWeight: "var(--fw-semibold)",
                cursor: "pointer",
                boxShadow: theme === name ? "var(--shadow-md)" : "var(--shadow-xs)",
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "flex-start",
                padding: "6px 8px",
              },
            },
            name
          )
        )
      )
    );
  }

  function Root() {
    return h(
      "form",
      { method: "post", action: P.nav.settings, encType: "multipart/form-data", style: { display: "flex", flexDirection: "column", gap: "22px" } },
      h(CsrfField, null),
      h(
        Card,
        { title: "Company" },
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "16px" } },
          h(Input, { label: "Company name (shown on every report and invoice)", name: "company_name", defaultValue: P.settingsCompanyName, containerStyle: { maxWidth: 360 } }),
          h(Input, { label: "Warehouse address (printed on sale/purchase D.O. slips)", name: "warehouse_address", defaultValue: P.warehouseAddress, placeholder: "e.g. Plot 12, Industrial Area, Faisalabad", containerStyle: { maxWidth: 480 } }),
          h(
            "div",
            { style: { display: "flex", flexDirection: "column", gap: "6px", maxWidth: 360 } },
            h("label", { style: labelStyle() }, "Logo (PNG/JPG, printed on invoices and vouchers)"),
            P.logoUrl ? h("img", { src: P.logoUrl, style: { height: 48, borderRadius: 6, border: "1px solid var(--border-default)" } }) : null,
            h("input", { type: "file", name: "logo", accept: "image/png,image/jpeg,image/gif" })
          )
        )
      ),
      h(ThemeSwatches),
      h(
        Card,
        { title: "Opening Cash Balance" },
        h(Banner, { tone: "info", style: { marginBottom: "16px" } }, "Cash-in-hand as of a starting date - the Cash Book adds every transaction from that date onward on top of it."),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Input, { label: "Amount", name: "opening_cash_balance", type: "number", step: "0.01", defaultValue: P.openingCashBalance }),
          h(Input, { label: "As of date", name: "opening_cash_date", type: "date", defaultValue: P.openingCashDate })
        )
      ),
      h(
        Card,
        { title: "Daily Email Reports" },
        h(Banner, { tone: "info", style: { marginBottom: "16px" } }, "If set, this address gets the Receivable, Payable, Cash Book, and Stock reports emailed automatically every day. Leave blank to turn this off."),
        h(Input, { label: "Notification email", name: "notification_email", type: "email", defaultValue: P.notificationEmail, placeholder: "admin@yourcompany.com", containerStyle: { maxWidth: 360 } })
      ),
      h("div", null, h(Button, { type: "submit", icon: "check" }, "Save Settings"))
    );
  }

  window.KhatayDS.mountShell({
    activeId: "settings",
    topbar: { breadcrumb: "Account", title: "Company Settings" },
    content: h(Root),
  });
})();
