/* Shared 404/500 error page - the whole point of these is to still
   render correctly with nothing else known about the request (no
   guaranteed g.user/g.company), so they only ever use the minimal
   csrfToken/flashes/homeUrl/code/heading/message fields set directly
   in errors/404.html and errors/500.html, no shared page-data include. */
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
        { style: { width: 44, height: 44, borderRadius: "50%", background: "var(--status-neutral-bg)", margin: "0 auto 16px", display: "flex", alignItems: "center", justifyContent: "center" } },
        h(DS.Icon, { name: P.code === 404 ? "map-pin-off" : "server-crash", size: 22, color: "var(--text-subtle)" })
      ),
      h("div", { style: { fontSize: "13px", color: "var(--text-subtle)", marginBottom: 4 } }, "Error " + P.code),
      h("p", { style: { fontSize: "13.5px", color: "var(--text-body)" } }, P.message),
      h(Button, { fullWidth: true, onClick: () => (window.location.href = P.homeUrl) }, "Take me home")
    );
  }

  window.KhatayDS.mountAuthShell({
    title: P.heading,
    content: h(Root),
  });
})();
