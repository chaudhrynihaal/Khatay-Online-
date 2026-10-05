/* Purchase & Sale Entry - wired to app.py's transactions() route. Two
   steps: Entry, then (only if "capture signature" is checked) a real
   canvas signature pad - ported from the old page's vanilla-JS drawing
   logic, not the design-reference mock's placeholder "tap to capture"
   button, since the captured PNG actually gets embedded on the printed
   D.O. slip server-side and has to be real. Submits through a genuine
   <form method="post"> to the unchanged /transactions route. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Button, Card, Badge, IconButton, DataTable, EmptyState, Banner, Input, Checkbox, Dialog } = DS;
  const { SearchField, Pagination } = DS;
  const { money, CsrfField, ComboboxField, Segmented, editUrlWithReturn, focusNextOnEnter } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  const partyOptions = P.parties.map((p) => ({ value: String(p.id), label: p.name, meta: p.type }));
  const brokerOptions = P.brokers.map((b) => ({ value: String(b.id), label: b.name }));
  const itemOptions = P.items.map((i) => ({ value: String(i.id), label: i.name, sale_rate: i.sale_rate }));

  function urlFor(base, id) {
    return base.replace("/0/", "/" + id + "/");
  }

  function SignaturePad({ onCapture, onBack }) {
    const canvasRef = React.useRef(null);
    const drawing = React.useRef(false);
    const hasStroke = React.useRef(false);

    React.useEffect(() => {
      const canvas = canvasRef.current;
      const ratio = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * ratio;
      canvas.height = rect.height * ratio;
      const ctx = canvas.getContext("2d");
      ctx.scale(ratio, ratio);
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#1c1c1f";

      function pos(e) {
        const r = canvas.getBoundingClientRect();
        const point = e.touches ? e.touches[0] : e;
        return { x: point.clientX - r.left, y: point.clientY - r.top };
      }
      function start(e) {
        e.preventDefault();
        drawing.current = true;
        const p = pos(e);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
      }
      function move(e) {
        if (!drawing.current) return;
        e.preventDefault();
        const p = pos(e);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        hasStroke.current = true;
      }
      function end() {
        drawing.current = false;
      }
      canvas.addEventListener("mousedown", start);
      canvas.addEventListener("mousemove", move);
      window.addEventListener("mouseup", end);
      canvas.addEventListener("touchstart", start, { passive: false });
      canvas.addEventListener("touchmove", move, { passive: false });
      canvas.addEventListener("touchend", end);
      return () => {
        canvas.removeEventListener("mousedown", start);
        canvas.removeEventListener("mousemove", move);
        window.removeEventListener("mouseup", end);
        canvas.removeEventListener("touchstart", start);
        canvas.removeEventListener("touchmove", move);
        canvas.removeEventListener("touchend", end);
      };
    }, []);

    function clear() {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      hasStroke.current = false;
    }
    function confirm() {
      if (!hasStroke.current) {
        window.alert("Please capture a signature first, or go back and uncheck the signature option.");
        return;
      }
      onCapture(canvasRef.current.toDataURL("image/png"));
    }

    return h(
      "div",
      { style: { display: "flex", flexDirection: "column", gap: "16px" } },
      h("p", { style: { margin: 0, fontSize: "13px", color: "var(--text-muted)" } }, "Ask the receiver to sign below using a finger, stylus, mouse, or a connected signature pad."),
      h("div", { style: { border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", background: "#fff", touchAction: "none" } },
        h("canvas", { ref: canvasRef, style: { width: "100%", height: "220px", display: "block", cursor: "crosshair" } })
      ),
      h(
        "div",
        { style: { display: "flex", gap: "8px" } },
        h(Button, { type: "button", variant: "secondary", onClick: clear }, "Clear"),
        h(Button, { type: "button", variant: "secondary", onClick: onBack }, "← Back"),
        h(Button, { type: "button", onClick: confirm }, "Confirm & Save")
      )
    );
  }

  /* One persistent <form> for the whole wizard, exactly like the old
     page - the earlier version of this screen rendered step 1 and step
     2 as two entirely separate <form>-owning components and swapped
     between them, which meant React unmounted (detached from the DOM)
     the step-1 form the moment "capture signature" moved to step 2;
     calling .submit() on a detached form is a silent no-op in Chrome,
     so nothing ever actually saved. Fixed by having EntryCard own one
     <form> for the whole component's life, with step 1's fields and
     step 2's signature pad as conditionally-rendered CHILDREN inside
     it (never removing the form itself), same as the old vanilla-JS
     #step1/#step2 div-toggling. */
  function EntryCard() {
    const [step, setStep] = React.useState(1);
    const [type, setType] = React.useState("SALE");
    const [mode, setMode] = React.useState("Cash");
    const [doNo, setDoNo] = React.useState(P.suggestedDoSale);
    const [rate, setRate] = React.useState("");
    const [qty, setQty] = React.useState("");
    const [wantSignature, setWantSignature] = React.useState(false);
    const formRef = React.useRef(null);
    const sigInputRef = React.useRef(null);

    function onTypeChange(v) {
      setType(v);
      setDoNo(v === "SALE" ? P.suggestedDoSale : P.suggestedDoPurchase);
      if (v !== "SALE") setWantSignature(false);
    }

    const amount = (parseFloat(qty) || 0) * (parseFloat(rate) || 0);

    function hasRequiredFields() {
      // DS.Input's `required` prop only draws the red label asterisk -
      // it doesn't forward to the underlying <input>, so
      // form.reportValidity() can't actually catch a missing Party/Item/
      // Qty/Rate here the way native HTML5 validation normally would.
      // The server still rejects a missing party_id/quality_id safely
      // (int('') raises, caught by the app-wide ValueError handler), but
      // that's a worse experience than catching it before the signature
      // step, so it's checked explicitly here instead.
      const fd = new FormData(formRef.current);
      return fd.get("party_id") && fd.get("quality_id") && fd.get("qty") && fd.get("rate");
    }

    function handleSubmit(e) {
      if (step === 1 && wantSignature) {
        e.preventDefault();
        if (!hasRequiredFields()) {
          window.alert("Pick a party and item, and enter a quantity and rate, before capturing a signature.");
          return;
        }
        setStep(2);
      }
      // step === 2 (or no signature wanted): let the native submission
      // through as-is - the signature hidden input, if any, was already
      // written directly onto the DOM node by onCapture below.
    }

    function onCapture(dataUrl) {
      sigInputRef.current.value = dataUrl;
      formRef.current.requestSubmit();
    }

    return h(
      Card,
      { title: step === 1 ? "New entry" : "Receiver Signature" },
      h(
        "form",
        { method: "post", ref: formRef, onSubmit: handleSubmit },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "voucher_type", value: type }),
        h("input", { type: "hidden", name: "mode", value: mode }),
        h("input", { type: "hidden", name: "signature_data", ref: sigInputRef, defaultValue: "" }),
        h(
          "div",
          { style: { display: step === 1 ? "flex" : "none", flexDirection: "column", gap: "0" } },
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(180px, 1fr))", gap: "20px" } },
            h(
              "div",
              { style: { display: "flex", flexDirection: "column", gap: "6px" } },
              h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Type"),
              h(Segmented, { value: type, onChange: onTypeChange, options: [{ value: "SALE", label: "Sale" }, { value: "PURCHASE", label: "Purchase" }] })
            ),
            h(Input, { label: "Date", type: "date", name: "date", defaultValue: P.today, required: true, onKeyDown: focusNextOnEnter }),
            h(Input, { label: "D.O. No.", name: "do_no", value: doNo, onChange: (e) => setDoNo(e.target.value), onKeyDown: focusNextOnEnter })
          ),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(180px, 1fr))", gap: "20px", marginTop: "20px" } },
            h(ComboboxField, { name: "broker_party_id", label: "Broker", options: brokerOptions, placeholder: "None" }),
            h(ComboboxField, {
              name: "party_id",
              label: "Party",
              options: partyOptions,
              required: step === 1,
              placeholder: "Search…",
              quickAddUrl: P.partyQuickAddUrl,
              entityLabel: "party",
              extraCreateFields: { party_type: type === "SALE" ? "Customer" : "Supplier" },
            }),
            h(ComboboxField, {
              name: "quality_id",
              label: "Item / Quality",
              options: itemOptions,
              required: step === 1,
              placeholder: "Search…",
              quickAddUrl: P.itemQuickAddUrl,
              entityLabel: "item",
              onPick: (v, opt) => {
                if (type === "SALE" && opt) setRate(String(opt.sale_rate || 0));
              },
            })
          ),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(180px, 1fr))", gap: "20px", marginTop: "20px" } },
            h(Input, { label: "Qty", name: "qty", required: step === 1, type: "number", step: "0.01", value: qty, onChange: (e) => setQty(e.target.value), onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Rate", name: "rate", required: step === 1, type: "number", step: "0.01", value: rate, onChange: (e) => setRate(e.target.value), onKeyDown: focusNextOnEnter }),
            h(Input, { label: "Amount", prefix: "Rs", readOnly: true, value: amount ? amount.toLocaleString("en-PK") : "" })
          ),
          h(
            "div",
            { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(180px, 1fr))", gap: "20px", marginTop: "20px" } },
            h(Input, { label: "Credit Days", name: "credit_days", type: "number", defaultValue: 0, onKeyDown: focusNextOnEnter }),
            h(
              "div",
              { style: { display: "flex", flexDirection: "column", gap: "6px" } },
              h("label", { style: { fontSize: "var(--text-label-size)", fontWeight: "var(--text-label-weight)", color: "var(--text-body)" } }, "Mode"),
              h(Segmented, { value: mode, onChange: setMode, options: [{ value: "Cash", label: "Cash" }, { value: "Cheque", label: "Cheque" }] })
            ),
            mode === "Cheque" ? h(Input, { label: "Cheque No.", name: "cheque_no", onKeyDown: focusNextOnEnter }) : h("div", null)
          ),
          h("div", { style: { marginTop: "20px" } }, h(Input, { label: "Description", name: "description", onKeyDown: focusNextOnEnter })),
          type === "SALE"
            ? h(Checkbox, {
                label: "Get the receiver's signature before saving",
                description: "Adds a signature step before this entry is saved",
                checked: wantSignature,
                onChange: (e) => setWantSignature(e.target.checked),
                style: { marginTop: "16px" },
              })
            : null,
          h("div", { style: { marginTop: "20px" } }, h(Button, { type: "submit", icon: "check" }, "Save Entry"))
        ),
        step === 2 ? h(SignaturePad, { onCapture: onCapture, onBack: () => setStep(1) }) : null
      )
    );
  }

  /* Alternative to a direct manual entry: pick one of the open Yarn
     bookings and record a (full or partial) delivery against it
     instead - same db.deliver_booking() backend the Bookings page's
     own Deliver dialog uses, just reachable from here too so daily
     data entry doesn't need a trip to the Bookings section. */
  function DeliverDialog({ booking, onClose }) {
    if (!booking) return null;
    return h(
      Dialog,
      { open: true, onClose: onClose, width: 520, title: "Deliver " + booking.booking_display, description: "Remaining: " + booking.remaining_qty },
      h(
        "form",
        { method: "post", action: urlFor(P.deliverBookingUrlBase, booking.id) },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "return_to", value: "transactions" }),
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

  function bookingFulfillColumns(setDelivering) {
    return [
      { key: "booking_display", label: "Booking #", emphasis: true },
      { key: "voucher_type", label: "Type", render: (r) => h(Badge, { tone: r.voucher_type === "SALE" ? "ok" : "info" }, r.voucher_type === "SALE" ? "Sale" : "Purchase") },
      { key: "party_name", label: "Party" },
      { key: "item_name", label: "Item" },
      { key: "remaining_qty", label: "Remaining", numeric: true, align: "right" },
      { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => money(r.rate) },
      { key: "actions", label: "", align: "right", render: (r) => h(Button, { size: "sm", onClick: () => setDelivering(r) }, "Deliver") },
    ];
  }

  function BookingFulfillCard() {
    const bookings = P.openBookings || [];
    const [delivering, setDelivering] = React.useState(null);
    if (bookings.length === 0) return null;
    return h(
      React.Fragment,
      null,
      h(
        Card,
        { title: "Fulfill an Open Booking", subtitle: "Deliver against an existing booking instead of a fresh direct entry" },
        h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: bookingFulfillColumns(setDelivering), rows: bookings }))
      ),
      h(DeliverDialog, { booking: delivering, onClose: () => setDelivering(null) })
    );
  }

  function SavedBanner() {
    if (!P.savedVoucher) return null;
    return h(
      Banner,
      { tone: "ok", title: "Saved as " + P.savedVoucher.voucher + " — ready for your next entry.",
        action: h(Button, { size: "sm", variant: "secondary", onClick: () => window.open(urlFor(P.printVoucherUrlBase, P.savedVoucher.id), "_blank") }, "Print This Voucher") }
    );
  }

  function SearchBar() {
    const [value, setValue] = React.useState(P.searchQ || "");
    return h(
      "form",
      { method: "get", action: P.nav.transactions, style: { display: "flex", gap: "8px" } },
      h(SearchField, { name: "q", value: value, onChange: (e) => setValue(e.target.value), placeholder: "Find by invoice #, D.O. #, or Sr. #…", width: 320 }),
      h(Button, { type: "submit", variant: "secondary" }, "Search"),
      P.searchQ ? h(Button, { type: "button", variant: "ghost", onClick: () => (window.location.href = P.nav.transactions) }, "Clear") : null
    );
  }

  function recentColumns() {
    return [
      { key: "voucher", label: "Voucher #", emphasis: true },
      { key: "date", label: "Date" },
      { key: "type", label: "Type", render: (r) => h(Badge, { tone: r.type === "SALE" ? "ok" : "info", icon: r.type === "SALE" ? "trending-up" : "truck" }, r.type === "SALE" ? "Sale" : "Purchase") },
      { key: "do_no", label: "D.O. #", render: (r) => r.do_no || "—" },
      { key: "party", label: "Party", render: (r) => r.party || "—" },
      { key: "item", label: "Item", render: (r) => r.item || "—" },
      { key: "qty", label: "Qty", numeric: true, align: "right", render: (r) => (r.qty ? r.qty : "—") },
      { key: "rate", label: "Rate", numeric: true, align: "right", render: (r) => (r.rate ? money(r.rate) : "—") },
      { key: "amount", label: "Amount", numeric: true, align: "right", emphasis: true, render: (r) => money(r.amount) },
      {
        key: "actions",
        label: "",
        align: "right",
        width: 120,
        render: (r) =>
          h(
            "div",
            { style: { display: "flex", justifyContent: "flex-end", gap: "4px" } },
            h(IconButton, { icon: "printer", label: "Print " + r.voucher, size: "sm", onClick: () => window.open(urlFor(P.printVoucherUrlBase, r.id), "_blank") }),
            P.canEdit
              ? h(IconButton, { icon: "pencil", label: "Edit " + r.voucher, size: "sm", onClick: () => (window.location.href = editUrlWithReturn(P.editTransactionUrlBase, r.id)) })
              : null,
            P.isAdmin
              ? h(
                  "form",
                  {
                    method: "post",
                    action: urlFor(P.deleteTransactionUrlBase, r.id),
                    onSubmit: (e) => {
                      if (!window.confirm("Delete this entry?")) e.preventDefault();
                    },
                  },
                  h(CsrfField, null),
                  h(IconButton, { icon: "trash-2", label: "Delete " + r.voucher, size: "sm", type: "submit" })
                )
              : null
          ),
      },
    ];
  }

  function RecentEntries() {
    const recent = P.recent || [];
    return h(
      React.Fragment,
      null,
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, h(SearchBar)),
      h(
        Card,
        { padding: "none", footer: h(Pagination, { page: 1, pageCount: 1, rangeLabel: recent.length + (recent.length === 1 ? " entry" : " entries") }) },
        recent.length === 0
          ? h(EmptyState, { icon: "file-text", title: P.searchQ ? 'No entries match "' + P.searchQ + '"' : "No entries yet" })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: recentColumns(), rows: recent }))
      )
    );
  }

  window.KhatayDS.mountShell({
    activeId: "transactions",
    topbar: { breadcrumb: "Entry", title: "Purchase & Sale Entry" },
    content: h(React.Fragment, null, h(SavedBanner), h(EntryCard), h(BookingFulfillCard), h(RecentEntries)),
  });
})();
