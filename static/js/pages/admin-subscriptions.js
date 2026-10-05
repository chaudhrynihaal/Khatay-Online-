/* Subscriptions - wired to app.py's admin_subscriptions() route.
   Read-only, no filters - a pre-sorted (overdue first, then soonest-
   due, no-expiry last) full list of every company's subscription
   status, for the platform admin to see who needs a follow-up. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, StatCard, Badge, DataTable, EmptyState, Button } = DS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function urlFor(base, id) {
    return base.replace("/0", "/" + id);
  }

  function statusBadge(c) {
    if (c.subscription_status === "trial" && !c.is_expired) return h(Badge, { tone: "info" }, "Trial");
    const tone = c.subscription_status === "active" ? "ok" : c.subscription_status === "suspended" ? "warn" : "danger";
    const label = c.subscription_status.charAt(0).toUpperCase() + c.subscription_status.slice(1) + (c.is_expired ? " (expired)" : "");
    return h(Badge, { tone: tone }, label);
  }

  function daysText(c) {
    if (c.days_until_due == null) return "—";
    if (c.days_until_due < 0) return "Overdue by " + Math.abs(c.days_until_due) + "d";
    if (c.days_until_due === 0) return "Due today";
    return "Due in " + c.days_until_due + "d";
  }

  function columns() {
    return [
      { key: "name", label: "Company", emphasis: true, render: (r) => h("a", { href: urlFor(P.companyDetailUrlBase, r.id) }, r.name) },
      { key: "subscription_status", label: "Status", render: (r) => statusBadge(r) },
      { key: "subscription_expiry", label: "Expiry Date", render: (r) => r.subscription_expiry || "No expiry" },
      {
        key: "days_until_due",
        label: "Days",
        render: (r) => h("span", { style: { color: r.is_expired ? "var(--red-600)" : undefined, fontWeight: r.is_expired ? "var(--fw-semibold)" : undefined } }, daysText(r)),
      },
      { key: "actions", label: "", align: "right", render: (r) => h(Button, { size: "sm", variant: "secondary", onClick: () => (window.location.href = urlFor(P.companyDetailUrlBase, r.id)) }, "Manage") },
    ];
  }

  function Root() {
    const companies = P.companies || [];
    return h(
      React.Fragment,
      null,
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Overdue", value: P.overdueCount, icon: "triangle-alert", tone: P.overdueCount > 0 ? "danger" : "neutral" }),
        h(StatCard, { label: "Due within 7 days", value: P.dueSoonCount, icon: "clock-alert", tone: P.dueSoonCount > 0 ? "highlight" : "neutral" }),
        h(StatCard, { label: "Total Companies", value: companies.length, icon: "building-2" })
      ),
      h(
        Card,
        { title: "All companies", padding: "none" },
        companies.length === 0
          ? h(EmptyState, { icon: "calendar", title: "No companies yet." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(), rows: companies }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "subscriptions",
    topbar: { title: "Subscriptions", subtitle: "Platform Admin" },
    content: h(Root),
    navItems: window.KhatayDS.buildAdminNavItems(P, "subscriptions"),
    hideSwitchBusiness: true,
  });
})();
