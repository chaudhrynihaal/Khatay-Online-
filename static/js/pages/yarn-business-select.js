/* Choose Business - wired to app.py's business_select() route (a
   static picker, no server-side data of its own beyond the standard
   page data). Sidebar-less, like the old page's content_bare block -
   this IS the "pick a business" screen, so there's no current
   business context to show a sidebar for yet. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Icon } = DS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const BUSINESSES = [
    { icon: "🧵", name: "Yarn", href: P.yarnUrl },
    { icon: "🌾", name: "Kiryana", href: P.kiryanaUrl },
    { icon: "🔩", name: "Hardware", href: P.hardwareUrl },
    { icon: "🧶", name: "Fabric", soon: true },
    { icon: "🤝", name: "Broker", soon: true },
  ];

  function BusinessCard({ biz }) {
    const [hover, setHover] = React.useState(false);
    const style = {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "10px",
      width: 140,
      height: 120,
      borderRadius: "var(--radius-card)",
      border: "1px solid var(--border-subtle)",
      background: "var(--surface-card)",
      boxShadow: hover && !biz.soon ? "var(--shadow-md)" : "var(--shadow-xs)",
      textDecoration: "none",
      color: "var(--text-heading)",
      opacity: biz.soon ? 0.55 : 1,
      cursor: biz.soon ? "not-allowed" : "pointer",
      transition: "var(--transition-control)",
    };
    const inner = h(
      React.Fragment,
      null,
      h("div", { style: { fontSize: "32px" } }, biz.icon),
      h("div", { style: { fontSize: "14px", fontWeight: "var(--fw-semibold)" } }, biz.name),
      biz.soon ? h("div", { style: { fontSize: "11px", color: "var(--text-subtle)" } }, "Coming soon") : null
    );
    if (biz.soon) return h("div", { style: style }, inner);
    return h("a", { href: biz.href, style: style, onMouseEnter: () => setHover(true), onMouseLeave: () => setHover(false) }, inner);
  }

  function Root() {
    return h(
      "div",
      { style: { display: "flex", flexWrap: "wrap", gap: "16px", justifyContent: "center" } },
      BUSINESSES.map((biz) => h(BusinessCard, { key: biz.name, biz: biz }))
    );
  }

  window.KhatayDS.mountAuthShell({
    title: "What do you deal in?",
    subtitle: "Pick a business type to open its tools.",
    content: h(Root),
    maxWidth: 620,
  });
})();
