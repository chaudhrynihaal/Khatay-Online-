/* Team - wired to app.py's team()/team_delete_user()/team_toggle_edit()/
   team_set_email() routes. Only reachable by a company admin (the
   route itself redirects anyone else away before rendering this
   template, and the sidebar only shows the Team link when isAdmin). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Select, Button, Badge, DataTable, EmptyState } = DS;
  const { SearchField } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function AddUserForm() {
    return h(
      Card,
      { title: "Add a team member" },
      h(
        "form",
        { method: "post", action: P.nav.team },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(5, minmax(140px, 1fr))", gap: "16px" } },
          h(Input, { label: "Username", name: "username", required: true }),
          h(Input, { label: "Password", name: "password", minLength: 6, required: true }),
          h(Input, { label: "Full name", name: "full_name" }),
          h(Input, { label: "Email", name: "email", type: "email", placeholder: 'Needed for "Forgot password?"' }),
          h(Select, { label: "Role", name: "role", options: [{ value: "staff", label: "Staff" }, { value: "admin", label: "Admin" }], defaultValue: "staff" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "user-plus" }, "Add User"))
      )
    );
  }

  function EmailCell({ user }) {
    const [value, setValue] = React.useState(user.email || "");
    return h(
      "form",
      { method: "post", action: urlFor(P.setEmailUrlBase, user.id), style: { display: "flex", gap: "4px" } },
      h(CsrfField, null),
      h("input", { type: "email", name: "email", value: value, onChange: (e) => setValue(e.target.value), placeholder: "email@…", style: { width: 160, padding: "6px 8px", fontSize: "12.5px", border: "1px solid var(--border-default)", borderRadius: "var(--radius-control)" } }),
      h(Button, { type: "submit", size: "sm", variant: "secondary" }, "Save")
    );
  }

  function EditToggleCell({ user }) {
    if (user.role === "admin") return h(Badge, { tone: "ok" }, "Always (Admin)");
    return h(
      "form",
      { method: "post", action: urlFor(P.toggleEditUrlBase, user.id) },
      h(CsrfField, null),
      h(Button, { type: "submit", size: "sm", variant: user.can_edit ? "primary" : "secondary" }, user.can_edit ? "✓ Can Edit" : "Grant Edit Rights")
    );
  }

  function RemoveCell({ user }) {
    if (user.id === P.currentUserId) return h("span", { style: { color: "var(--text-subtle)", fontSize: "12px" } }, "(you)");
    return h(
      "form",
      {
        method: "post",
        action: urlFor(P.deleteUserUrlBase, user.id),
        onSubmit: (e) => {
          if (!window.confirm("Remove this user?")) e.preventDefault();
        },
      },
      h(CsrfField, null),
      h(Button, { type: "submit", size: "sm", variant: "danger" }, "Remove")
    );
  }

  function columns() {
    return [
      { key: "username", label: "Username", emphasis: true },
      { key: "full_name", label: "Full name", render: (u) => u.full_name || "—" },
      { key: "email", label: "Email", render: (u) => h(EmailCell, { user: u }) },
      { key: "role", label: "Role", render: (u) => u.role.charAt(0).toUpperCase() + u.role.slice(1) },
      { key: "can_edit", label: "Can Edit Entries", render: (u) => h(EditToggleCell, { user: u }) },
      { key: "actions", label: "", align: "right", render: (u) => h(RemoveCell, { user: u }) },
    ];
  }

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.team, style: { display: "flex", gap: "8px" } },
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Find by username or name…", width: 240 }),
      h(Button, { type: "submit", variant: "secondary", size: "sm" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", size: "sm", onClick: () => (window.location.href = P.nav.team) }, "Clear") : null
    );
  }

  function Root() {
    const users = P.users || [];
    return h(
      React.Fragment,
      null,
      h(AddUserForm),
      h(
        Card,
        { title: "Everyone with access", actions: h(SearchBar), padding: "none" },
        users.length === 0
          ? h(EmptyState, { icon: "users", title: P.searchQ ? 'No users match "' + P.searchQ + '"' : "No team members yet." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: users }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "team",
    topbar: { breadcrumb: "Account", title: "Team" },
    content: h(Root),
  });
})();
