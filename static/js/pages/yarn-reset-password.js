/* Set a New Password - wired to app.py's reset_password(token) route.
   The token itself was already validated server-side before this
   template rendered at all (an invalid/expired token redirects to
   Forgot Password before ever reaching here). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function Root() {
    return h(
      Card,
      null,
      h(
        "form",
        { method: "post", action: P.resetPasswordUrl, style: { display: "flex", flexDirection: "column", gap: "16px" } },
        h(CsrfField, null),
        h(Input, { label: "New Password", name: "password", type: "password", minLength: 6, required: true, autoFocus: true }),
        h(Input, { label: "Confirm New Password", name: "confirm", type: "password", minLength: 6, required: true }),
        h(Button, { type: "submit", fullWidth: true }, "Set Password")
      )
    );
  }

  window.KhatayDS.mountAuthShell({
    title: "Set a New Password",
    subtitle: P.username ? "For " + P.username : "",
    content: h(Root),
  });
})();
