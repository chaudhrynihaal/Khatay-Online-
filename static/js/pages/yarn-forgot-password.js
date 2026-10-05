/* Forgot Password - wired to app.py's forgot_password() route. Always
   shows the same generic success message regardless of whether the
   account/email actually exists (server-side anti-enumeration
   behavior, unchanged) - the flash message carries that text, this
   page has no client-side branching of its own. */
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
        { method: "post", action: P.forgotPasswordUrl, style: { display: "flex", flexDirection: "column", gap: "16px" } },
        h(CsrfField, null),
        h(Input, { label: "Username or Email", name: "identifier", autoFocus: true, required: true }),
        h(Button, { type: "submit", fullWidth: true }, "Send Reset Link")
      ),
      h(
        "p",
        { style: { textAlign: "center", marginTop: "16px", fontSize: "13px" } },
        h("a", { href: P.loginUrl }, "Back to sign in")
      )
    );
  }

  window.KhatayDS.mountAuthShell({
    title: "Forgot Password",
    subtitle: "Enter your username or email and we'll send you a reset link, if we have one on file.",
    content: h(Root),
  });
})();
