/* Yarn Dashboard - wired to real data via window.__PAGE__ (injected by
   templates/app/dashboard.html from app.py's dashboard() route). Built
   from the design system's reusable primitives rather than the
   prebuilt YarnDashboard demo in ds-bundle.js, which is a static mock
   with no props - see the design-reference prompt notes. Shell (sidebar
   nav + topbar frame) comes from ds-shell.js, shared by every migrated
   screen. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Icon, Button, Card, IconButton, StatCard } = DS;
  const { money } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function QuickAction({ icon, label, href }) {
    const [hover, setHover] = React.useState(false);
    return h(
      "a",
      {
        href: href,
        onMouseEnter: () => setHover(true),
        onMouseLeave: () => setHover(false),
        style: {
          display: "flex",
          alignItems: "center",
          gap: "10px",
          padding: "13px 16px",
          flex: 1,
          minWidth: 200,
          background: hover ? "var(--surface-hover)" : "var(--surface-card)",
          border: "1px solid " + (hover ? "var(--border-strong)" : "var(--border-default)"),
          borderRadius: "var(--radius-md)",
          boxShadow: "var(--shadow-xs)",
          cursor: "pointer",
          fontFamily: "var(--font-sans)",
          textAlign: "left",
          textDecoration: "none",
          transition: "var(--transition-control)",
          boxSizing: "border-box",
        },
      },
      h(
        "span",
        {
          style: {
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 34,
            height: 34,
            borderRadius: "var(--radius-sm)",
            background: "var(--indigo-50)",
            flex: "0 0 auto",
          },
        },
        h(Icon, { name: icon, size: 17, color: "var(--indigo-600)" })
      ),
      h(
        "span",
        { style: { fontSize: "14px", fontWeight: "var(--fw-semibold)", color: "var(--text-heading)" } },
        label
      )
    );
  }

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const content = h(
    React.Fragment,
    null,
    h(
      "div",
      { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" } },
      h(StatCard, {
        icon: "wallet",
        label: "Total Receivable",
        value: money(P.stats.totalReceivable),
        caption: "Across " + P.stats.receivablePartyCount + " part" + (P.stats.receivablePartyCount === 1 ? "y" : "ies"),
      }),
      h(StatCard, {
        tone: P.stats.overdueReceivable > 0 ? "danger" : "neutral",
        icon: "triangle-alert",
        label: "Overdue Receivable",
        value: money(P.stats.overdueReceivable),
        caption: P.stats.overduePartyCount + " part" + (P.stats.overduePartyCount === 1 ? "y" : "ies") + " overdue",
      }),
      h(StatCard, {
        icon: "hand-coins",
        label: "Total Payable",
        value: money(P.stats.totalPayable),
        caption: "Across " + P.stats.payablePartyCount + " part" + (P.stats.payablePartyCount === 1 ? "y" : "ies"),
      }),
      h(StatCard, {
        icon: "trending-up",
        label: "Net Profit",
        value: money(P.stats.netProfit),
        tone: P.stats.netProfit < 0 ? "danger" : "neutral",
        caption: "This month so far",
      })
    ),
    h(
      Card,
      { title: "Quick actions", padding: "md" },
      h(
        "div",
        { style: { display: "flex", gap: "12px", flexWrap: "wrap" } },
        h(QuickAction, { icon: "file-plus-2", label: "New Sale / Purchase", href: P.nav.transactions }),
        h(QuickAction, { icon: "banknote", label: "New Receipt / Payment", href: P.nav.recovery }),
        h(QuickAction, { icon: "user-plus", label: "New Party", href: P.nav.parties }),
        h(QuickAction, { icon: "book-open-text", label: "View Receivable Ledger", href: P.nav.reportReceivable })
      )
    ),
    h(
      "div",
      {
        style: {
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "var(--text-body-sm-size)",
          color: "var(--text-muted)",
          padding: "0 4px",
        },
      },
      h(Icon, { name: "users", size: 14, color: "var(--text-subtle)" }),
      h("span", null, P.stats.partyCount, " parties"),
      h("span", { style: { color: "var(--border-strong)" } }, "·"),
      h(Icon, { name: "boxes", size: 14, color: "var(--text-subtle)" }),
      h("span", null, P.stats.itemCount.toLocaleString("en-PK"), " items in stock master")
    )
  );

  window.KhatayDS.mountShell({
    activeId: "dashboard",
    topbar: {
      breadcrumb: "Yarn Trading",
      title: "Dashboard",
      subtitle: today,
      actions: h(IconButton, { icon: "settings-2", label: "Settings", variant: "secondary", onClick: () => (window.location.href = P.nav.settings) }),
    },
    content: content,
  });
})();
