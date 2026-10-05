/* Companies - wired to app.py's admin_dashboard()/admin_create_company()
   routes. The platform super-admin's landing page: create a new tenant
   company (which also provisions its own empty database on disk) and
   browse/manage every existing one. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Badge, DataTable, EmptyState } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0", "/" + id);
  }

  function statusBadge(c) {
    if (c.subscription_status === "trial" && !c.is_expired) return h(Badge, { tone: "info" }, "Trial");
    const tone = c.subscription_status === "active" ? "ok" : c.subscription_status === "suspended" ? "warn" : "danger";
    const label = c.subscription_status.charAt(0).toUpperCase() + c.subscription_status.slice(1) + (c.is_expired ? " (expired)" : "");
    return h(Badge, { tone: tone }, label);
  }

  function CreateCompanyForm() {
    return h(
      Card,
      { title: "Add a new company" },
      h(
        "form",
        { method: "post", action: P.createCompanyUrl },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" } },
          h(Input, { label: "Company Name", name: "company_name", required: true, placeholder: "e.g. Al-Falah Traders" }),
          h(Input, { label: "Trial Days", name: "trial_days", type: "number", min: "1", defaultValue: "14" })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Admin Username", name: "admin_username", required: true }),
          h(Input, { label: "Admin Password", name: "admin_password", minLength: 6, required: true, hint: "Shown as plain text so you can hand it to the customer" })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Admin Full Name", name: "admin_full_name" }),
          h(Input, { label: "Admin Email", name: "admin_email", type: "email" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "plus" }, "Create Company"))
      )
    );
  }

  function columns() {
    return [
      { key: "name", label: "Name", emphasis: true, render: (r) => h("a", { href: urlFor(P.companyDetailUrlBase, r.id) }, r.name) },
      { key: "subscription_status", label: "Status", render: (r) => statusBadge(r) },
      { key: "subscription_expiry", label: "Expiry", render: (r) => r.subscription_expiry || "—" },
      { key: "created_at", label: "Created", render: (r) => (r.created_at || "").slice(0, 10) },
      { key: "actions", label: "", align: "right", render: (r) => h(Button, { size: "sm", variant: "secondary", onClick: () => (window.location.href = urlFor(P.companyDetailUrlBase, r.id)) }, "Manage") },
    ];
  }

  function Root() {
    const companies = P.companies || [];
    return h(
      React.Fragment,
      null,
      h(CreateCompanyForm),
      h(
        Card,
        { title: "All companies", padding: "none" },
        companies.length === 0
          ? h(EmptyState, { icon: "building-2", title: "No companies yet", message: "Add your first one above." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: companies }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "companies",
    topbar: { title: "Companies", subtitle: "Platform Admin" },
    content: h(Root),
    navItems: window.KhatayDS.buildAdminNavItems(P, "companies"),
    hideSwitchBusiness: true,
  });
})();
