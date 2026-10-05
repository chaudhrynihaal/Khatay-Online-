/* Bookings - wired to app.py's bookings()/deliver_booking()/
   cancel_booking() routes. Recording a booking never touches stock or a
   party's balance; only a Deliver (full or partial, repeatable) creates
   a real Sale/Purchase transaction at the booking's locked-in rate. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, Badge, Dialog, DataTable, EmptyState, Banner, Input, Tabs } = DS;
  const { SearchField, Pagination } = DS;
  const { money, CsrfField, ComboboxField, Segmented } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const partyOptions = P.parties.map((p) => ({ value: String(p.id), label: p.name, meta: p.type }));
  const itemOptions = P.items.map((i) => ({ value: String(i.id), label: i.name }));

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/").replace("/0", "/" + id);
  }

  function statusUrl(status) {
    const u = new URL(P.nav.bookings, window.location.origin);
    u.searchParams.set("status", status);
    return u.pathname + u.search;
  }

  function NewBookingForm() {
    const [type, setType] = React.useState("SALE");
    return h(
      Card,
      { title: "New booking" },
      h(
        Banner,
        { tone: "info", style: { marginBottom: "16px" } },
        "A booking is a deal struck now for delivery later — it doesn't touch stock or the party's balance until you record an actual delivery against it (in full or in parts)."
      ),
      h(
        "form",
        { method: "post", action: P.nav.bookings },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "voucher_type", value: type }),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(4, minmax(160px, 1fr))", gap: "16px" } },
          h(
            "div",
            { style: { display: "flex", flexDirection: "column", gap: "6px" } },
            h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Type"),
            h(Segmented, { value: type, onChange: setType, options: [{ value: "SALE", label: "Sale" }, { value: "PURCHASE", label: "Purchase" }] })
          ),
          h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true }),
          h(ComboboxField, {
            name: "party_id",
            label: "Party",
            options: partyOptions,
            required: true,
            placeholder: "Search…",
            quickAddUrl: P.partyQuickAddUrl,
            entityLabel: "party",
            extraCreateFields: { party_type: type === "SALE" ? "Customer" : "Supplier" },
          }),
          h(ComboboxField, {
            name: "quality_id",
            label: "Item / Quality",
            options: itemOptions,
            required: true,
            placeholder: "Search…",
            quickAddUrl: P.itemQuickAddUrl,
            entityLabel: "item",
          })
        ),
        h(
          "div",
          { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(160px, 1fr))", gap: "16px", marginTop: "16px" } },
          h(Input, { label: "Qty", name: "qty", type: "number", step: "0.01", required: true }),
          h(Input, { label: "Rate", name: "rate", type: "number", step: "0.01", required: true }),
          h(Input, { label: "Delivery Terms", name: "delivery_terms", placeholder: "e.g. within 30 days, ex-warehouse" })
        ),
        h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Create Booking"))
      )
    );
  }

  function DeliverDialog({ booking, onClose }) {
    if (!booking) return null;
    return h(
      Dialog,
      { open: true, onClose: onClose, width: 520, title: "Deliver " + booking.booking_display, description: "Remaining: " + booking.remaining_qty },
      h(
        "form",
        { method: "post", action: urlFor(P.deliverBookingUrlBase, booking.id) },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "16px" } },
          h(Input, { label: "Deliver Qty (max " + booking.remaining_qty + ")", name: "deliver_qty", type: "number", step: "0.01", max: booking.remaining_qty, defaultValue: booking.remaining_qty, required: true }),
          h(Input, { label: "Delivery Date", name: "delivery_date", type: "date", defaultValue: P.today }),
          h(Input, { label: "D.O. No.", name: "do_no" }),
          h(Input, { label: "Credit Days", name: "credit_days", type: "number", defaultValue: 0 }),
          h(DeliverModeFields)
        ),
        h(
          "div",
          { style: { display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "20px" } },
          h(Button, { type: "button", variant: "secondary", onClick: onClose }, "Cancel"),
          h(Button, { type: "submit", icon: "check" }, "Confirm Delivery")
        )
      )
    );
  }

  function DeliverModeFields() {
    const [mode, setMode] = React.useState("Cash");
    return h(
      React.Fragment,
      null,
      h("input", { type: "hidden", name: "mode", value: mode }),
      h(
        "div",
        { style: { display: "flex", flexDirection: "column", gap: "6px" } },
        h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
        h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash" }, { value: "Cheque", label: "Cheque" }] })
      ),
      mode === "Cheque" ? h(Input, { label: "Cheque No.", name: "cheque_no" }) : null
    );
  }

  const STATUS_TONE = { Open: "info", Delivered: "ok", Cancelled: "danger" };

  function bookingColumns(setDelivering) {
    return [
      { key: "booking_display", label: "Booking #", emphasis: true, render: (r) => h("a", { href: urlFor(P.bookingDetailUrlBase, r.id) }, r.booking_display) },
      { key: "voucher_type", label: "Type", render: (r) => (r.voucher_type === "SALE" ? "Sale" : "Purchase") },
      { key: "date", label: "Date" },
      { key: "party_name", label: "Party", render: (r) => r.party_name || "—" },
      { key: "item_name", label: "Item", render: (r) => r.item_name || "—" },
      { key: "qty", label: "Qty", numeric: true, align: "right" },
      { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => money(r.rate) },
      { key: "delivered_qty", label: "Delivered", numeric: true, align: "right" },
      { key: "remaining_qty", label: "Remaining", numeric: true, align: "right" },
      { key: "delivery_terms", label: "Terms", render: (r) => r.delivery_terms || "—" },
      { key: "status", label: "Status", render: (r) => h(Badge, { tone: STATUS_TONE[r.status] }, r.status) },
      {
        key: "actions",
        label: "",
        align: "right",
        render: (r) =>
          r.status !== "Open"
            ? null
            : h(
                "div",
                { style: { display: "flex", justifyContent: "flex-end", gap: "6px" } },
                h(Button, { size: "sm", onClick: () => setDelivering(r) }, "Deliver"),
                r.delivered_qty === 0
                  ? h(
                      "form",
                      {
                        method: "post",
                        action: urlFor(P.cancelBookingUrlBase, r.id),
                        onSubmit: (e) => {
                          if (!window.confirm("Cancel this booking?")) e.preventDefault();
                        },
                      },
                      h(CsrfField, null),
                      h(Button, { type: "submit", size: "sm", variant: "danger" }, "Cancel")
                    )
                  : null
              ),
      },
    ];
  }

  function SavedBanner() {
    if (!P.savedVoucher) return null;
    return h(Banner, {
      tone: "ok",
      title: "Delivery recorded as " + P.savedVoucher.voucher + ".",
      action: h(Button, { size: "sm", variant: "secondary", onClick: () => window.open(urlFor(P.printVoucherUrlBase, P.savedVoucher.id), "_blank") }, "Print This Voucher"),
    });
  }

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.bookings, style: { display: "flex", gap: "8px" } },
      h("input", { type: "hidden", name: "status", value: P.statusFilter }),
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Find by booking #, party, or item…", width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = statusUrl(P.statusFilter)) }, "Clear") : null
    );
  }

  function Root() {
    const [delivering, setDelivering] = React.useState(null);
    const bookings = P.bookings || [];
    return h(
      React.Fragment,
      null,
      h(SavedBanner),
      h(NewBookingForm),
      h(Tabs, {
        value: P.statusFilter,
        onChange: (id) => (window.location.href = statusUrl(id)),
        items: [
          { id: "Open", label: "Open" },
          { id: "Delivered", label: "Delivered" },
          { id: "Cancelled", label: "Cancelled" },
          { id: "All", label: "All" },
        ],
      }),
      h(SearchBar),
      h(
        Card,
        { padding: "none", footer: h(Pagination, { page: 1, pageCount: 1, rangeLabel: bookings.length + (bookings.length === 1 ? " booking" : " bookings") }) },
        bookings.length === 0
          ? h(EmptyState, { icon: "calendar-check", title: P.searchQ ? 'No bookings match "' + P.searchQ + '"' : "No " + P.statusFilter.toLowerCase() + " bookings" })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: bookingColumns(setDelivering), rows: bookings }))
      ),
      h(DeliverDialog, { booking: delivering, onClose: () => setDelivering(null) })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "bookings",
    topbar: { breadcrumb: "Entry", title: "Purchase & Sale Bookings" },
    content: h(Root),
  });
})();
