/* Subscription Expired/Suspended - rendered by several of app.py's
   permission decorators (company_required, edit_permission_required,
   etc.) whenever master.is_subscription_active(g.company) is False,
   instead of the page the user actually asked for. No form, just a
   dead-end explaining why and a way to sign out. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Button } = DS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function Root() {
    return h(
      Card,
      { style: { textAlign: "center" } },
      h(
        "div",
        { style: { width: 44, height: 44, borderRadius: "50%", background: "var(--status-danger-bg)", margin: "0 auto 16px", display: "flex", alignItems: "center", justifyContent: "center" } },
        h(DS.Icon, { name: "circle-alert", size: 22, color: "var(--status-danger-fg)" })
      ),
      h("p", { style: { fontSize: "13px", color: "var(--text-subtle)" } }, P.companyName + "'s access has ended. Contact your administrator to renew."),
      h(Button, { variant: "secondary", fullWidth: true, onClick: () => (window.location.href = P.logoutUrl) }, "Sign out")
    );
  }

  window.KhatayDS.mountAuthShell({
    title: "Subscription " + (P.subscriptionStatus || "inactive"),
    content: h(Root),
  });
})();
