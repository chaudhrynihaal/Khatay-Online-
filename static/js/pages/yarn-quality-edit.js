/* Edit Item (Quality) - wired to app.py's edit_quality() route. Same
   field set as the Add Item dialog on the Quality/Items page, including
   Purchase Rate - which only prices the Opening Stock Qty here, not the
   item's overall rate (that stays the quantity-weighted average across
   opening stock and every real Purchase entry - see
   db.get_weighted_avg_purchase_rate). */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Input, Button, Banner } = DS;
  const { CsrfField, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;
  const item = P.item;

  function Root() {
    return h(
      Card,
      { title: "Edit " + item.name },
      h(
        Banner,
        { tone: "info", style: { marginBottom: "16px" } },
        "Purchase Rate here only prices the opening stock. Once real Purchase entries exist for this item, its rate becomes the quantity-weighted average across the opening stock and every purchase."
      ),
      h(
        "form",
        { method: "post" },
        h(CsrfField, null),
        h(
          "div",
          { style: { display: "flex", flexDirection: "column", gap: "16px" } },
          h(Input, { label: "Name", name: "name", defaultValue: item.name, required: true, onKeyDown: focusNextOnEnter }),
          h(Input, { label: "City / Area", name: "city_area", defaultValue: item.area || "", onKeyDown: focusNextOnEnter }),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" } },
            h(Input, { label: "Sale Rate", name: "sale_rate", prefix: "Rs", type: "number", step: "0.01", defaultValue: item.sale_rate, onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Opening Stock Qty", name: "opening_balance", type: "number", step: "0.01", defaultValue: item.opening_balance, onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Purchase Rate (opening stock)", name: "purchase_rate", prefix: "Rs", type: "number", step: "0.01", defaultValue: item.purchase_rate, onKeyDown: focusNextOnEnter })
          )
        ),
        h(
          "div",
          { style: { display: "flex", gap: "10px", marginTop: "20px" } },
          h(Button, { type: "submit", icon: "check" }, "Save Changes"),
          h(Button, { type: "button", variant: "secondary", onClick: () => (window.location.href = P.nav.quality) }, "Cancel")
        )
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "quality",
    topbar: { breadcrumb: "Master Data", title: "Edit Item" },
    content: h(Root),
  });
})();
