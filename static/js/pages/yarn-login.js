/* Sign in - wired to app.py's login() route. Pre-auth, so it uses the
   sidebar-less mountAuthShell instead of the normal app shell. Rate
   limited server-side (8/min) - errors surface as the usual flash ->
   Toast, exactly like every other migrated form. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Icon } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function AlreadySignedIn() {
    const u = P.alreadySignedIn;
    if (!u) return null;
    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "10px", padding: "12px 14px", background: "var(--status-info-bg)", border: "1px solid var(--status-info-border)", borderRadius: "var(--radius-md)" } },
      h(
        "div",
        { style: { display: "flex", gap: "10px", alignItems: "flex-start" } },
        h(Icon, { name: "info", size: 17, color: "var(--status-info-fg)", style: { marginTop: 1, flex: "0 0 auto" } }),
        h(
          "div",
          { style: { fontSize: "13.5px", color: "var(--text-heading)" } },
          "You're currently signed in as ",
          h("strong", null, u.full_name || u.username),
          u.role === "super_admin" ? " (platform admin)" : "",
          "."
        )
      ),
      h(
        "div",
        { style: { display: "flex", gap: "8px", flexWrap: "wrap" } },
        h(Button, { size: "sm", onClick: () => (window.location.href = u.role === "super_admin" ? P.adminDashboardUrl : P.dashboardUrl) }, "Continue"),
        h(Button, { size: "sm", variant: "secondary", onClick: () => (window.location.href = P.logoutUrl) }, "Sign out & use a different account")
      )
    );
  }

  function Root() {
    return h(
      Card,
      null,
      h(AlreadySignedIn),
      h(
        "form",
        { method: "post", action: P.loginUrl, style: { display: "flex", flexDirection: "column", gap: "16px" } },
        h(CsrfField, null),
        h(Input, { label: "Username", name: "username", autoFocus: true, required: true }),
        h(Input, { label: "Password", name: "password", type: "password", required: true }),
        h(Button, { type: "submit", fullWidth: true }, "Sign In")
      ),
      h(
        "p",
        { style: { textAlign: "center", marginTop: "16px", fontSize: "13px" } },
        h("a", { href: P.forgotPasswordUrl }, "Forgot password?")
      )
    );
  }

  window.KhatayDS.mountAuthShell({
    subtitle: "Sign in to your account",
    content: h(Root),
  });
})();
