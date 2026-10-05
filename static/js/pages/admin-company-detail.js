/* Company Detail - wired to app.py's admin_update_subscription()/
   admin_create_user()/admin_delete_user() routes. The platform admin
   can only manage this company's subscription and user accounts here
   - never its business data (parties, transactions, reports); there is
   deliberately no "log in as this company" feature anywhere in the
   app (see design-brief.md's explicit no-impersonation scoping). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Select, Button, Banner, IconButton, DataTable, EmptyState } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const company = P.company;

  function urlFor(base, id) {
    return base.replace("/0", "/" + id);
  }

  function SubscriptionForm() {
    return h(
      Card,
      { title: "Subscription" },
      h(
        "form",
        { method: "post", action: P.updateSubscriptionUrl },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(160px, 1fr))", gap: "16px" } },
          h(Select, { label: "Status", name: "status", defaultValue: company.subscription_status, options: [{ value: "trial", label: "Trial" }, { value: "active", label: "Active" }, { value: "expired", label: "Expired" }, { value: "suspended", label: "Suspended" }] }),
          h(Input, { label: "Expiry", name: "expiry", type: "date", defaultValue: company.subscription_expiry || "" })
        ),
        h(
          "div",
          { style: { marginTop: "16px", display: "flex", flexDirection: "column", gap: "6px" } },
          h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Notes"),
          h("textarea", {
            name: "notes",
            defaultValue: company.notes || "",
            rows: 2,
            style: { resize: "vertical", minHeight: 56, padding: "10px 12px", fontFamily: "var(--font-sans)", fontSize: "14px", color: "var(--text-heading)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-control)", boxShadow: "var(--shadow-xs)", outline: "none", boxSizing: "border-box" },
          })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save Subscription"))
      )
    );
  }

  function AddUserForm() {
    return h(
      Card,
      { title: "Add a user" },
      h(
        "form",
        { method: "post", action: P.createUserUrl },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Username", name: "username", required: true }),
          h(Input, { label: "Password", name: "password", minLength: 6, required: true, hint: "Shown as plain text" }),
          h(Input, { label: "Full Name", name: "full_name" }),
          h(Input, { label: "Email", name: "email", type: "email" })
        ),
        h(
          "div",
          { style: { marginTop: "16px", maxWidth: 200 } },
          h(Select, { label: "Role", name: "role", defaultValue: "staff", options: [{ value: "staff", label: "Staff" }, { value: "admin", label: "Admin" }] })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "user-plus" }, "Add User"))
      )
    );
  }

  function usersColumns() {
    return [
      { key: "username", label: "Username", emphasis: true },
      { key: "full_name", label: "Full name", render: (r) => r.full_name || "—" },
      { key: "role", label: "Role", render: (r) => r.role.charAt(0).toUpperCase() + r.role.slice(1) },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          h(
            "form",
            {
              method: "post",
              action: urlFor(P.deleteUserUrlBase, r.id),
              onSubmit: (e) => {
                if (!window.confirm("Remove this user?")) e.preventDefault();
              },
            },
            h(CsrfField, null),
            h(IconButton, { icon: "trash-2", label: "Remove " + r.username, size: "sm", type: "submit" })
          ),
      },
    ];
  }

  function Root() {
    const users = P.users || [];
    return h(
      React.Fragment,
      null,
      h(
        Banner,
        { tone: "info" },
        "Platform admin view - you can manage " + company.name + "'s subscription and user accounts here, but you cannot see their parties, transactions, or reports, and you are never signed into their account."
      ),
      h(SubscriptionForm),
      h(AddUserForm),
      h(
        Card,
        { title: "Users", padding: "none" },
        users.length === 0
          ? h(EmptyState, { icon: "users", title: "No users yet." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: usersColumns(), rows: users }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "companies",
    topbar: { title: company.name, subtitle: "Platform Admin" },
    content: h(Root),
    navItems: window.KhatayDS.buildAdminNavItems(P, "companies"),
    hideSwitchBusiness: true,
  });
})();
