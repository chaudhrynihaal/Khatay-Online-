/* Change Password - wired to app.py's admin_change_password() route.
   The super-admin's own account only - no current-password
   confirmation field and no "confirm new password" field, matching
   the old page exactly (unlike the self-service reset-password flow,
   which does ask for both). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function Root() {
    return h(
      Card,
      { title: "Change Password", style: { maxWidth: 420 } },
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(Input, { label: "New Password", name: "new_password", type: "password", minLength: 6, required: true, autoFocus: true }),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Change Password"))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "changePassword",
    topbar: { title: "Change Password", subtitle: "Platform Admin" },
    content: h(Root),
    navItems: window.KhatayDS.buildAdminNavItems(P, "changePassword"),
    hideSwitchBusiness: true,
  });
})();
