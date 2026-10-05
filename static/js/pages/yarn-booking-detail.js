/* Booking detail - wired to app.py's booking_detail() route. Read-only:
   booking info + the full delivery history against it. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Badge, IconButton, DataTable, EmptyState, StatCard } = DS;
  const { money } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const b = P.booking;

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  const STATUS_TONE = { Open: "info", Delivered: "ok", Cancelled: "danger" };

  function Summary() {
    return h(
      Card,
      { title: b.booking_display, subtitle: (b.voucher_type === "SALE" ? "Sale" : "Purchase") + " booking with " + (b.party_name || "—") },
      h(
        "div",
        { style: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px" } },
        h(StatCard, { label: "Qty", value: b.qty }),
        h(StatCard, { label: "Rate", value: money(b.rate) }),
        h(StatCard, { label: "Delivered", value: b.delivered_qty }),
        h(StatCard, { label: "Remaining", value: b.remaining_qty })
      ),
      h(
        "div",
        { style: { display: "flex", gap: "20px", marginTop: "20px", flexWrap: "wrap" } },
        h("div", null, h("div", { style: { fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" } }, "Item"), h("div", { style: { fontSize: "14px" } }, b.item_name || "—")),
        h("div", null, h("div", { style: { fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" } }, "Date"), h("div", { style: { fontSize: "14px" } }, b.date)),
        h("div", null, h("div", { style: { fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" } }, "Delivery Terms"), h("div", { style: { fontSize: "14px" } }, b.delivery_terms || "—")),
        h("div", null, h("div", { style: { fontSize: "var(--text-caption-size)", color: "var(--text-subtle)" } }, "Status"), h(Badge, { tone: STATUS_TONE[b.status] }, b.status))
      )
    );
  }

  function Deliveries() {
    const deliveries = P.deliveries || [];
    const columns = [
      { key: "voucher_display", label: "Voucher #", emphasis: true },
      { key: "date", label: "Date" },
      { key: "do_no", label: "D.O. #", render: (r) => r.do_no || "—" },
      { key: "qty", label: "Qty", numeric: true, align: "right" },
      { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => money(r.rate) },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      { key: "mode", label: "Mode", render: (r) => r.mode || "Cash" },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) => h(IconButton, { icon: "printer", label: "Print " + r.voucher_display, size: "sm", onClick: () => window.open(urlFor(P.printVoucherUrlBase, r.transaction_id), "_blank") }),
      },
    ];
    return h(
      Card,
      { title: "Delivery history", subtitle: deliveries.length + (deliveries.length === 1 ? " delivery" : " deliveries") },
      deliveries.length === 0
        ? h(EmptyState, { icon: "truck", title: "No deliveries yet", message: "Deliveries against this booking will show up here." })
        : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns, rows: deliveries }))
    );
  }

  window.KhatayDS.mountShell({
    activeId: "bookings",
    topbar: { breadcrumb: "Entry · Bookings", title: b.booking_display },
    content: h(React.Fragment, null, h(Summary), h(Deliveries)),
  });
})();
