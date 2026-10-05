/* @ds-bundle: {"format":4,"namespace":"KhatayOnlineDesignSystem_90c3f9","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Reveal","sourcePath":"components/core/Reveal.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Wordmark","sourcePath":"components/core/Wordmark.jsx"},{"name":"DataTable","sourcePath":"components/data/DataTable.jsx"},{"name":"InvoiceGroup","sourcePath":"components/data/InvoiceGroup.jsx"},{"name":"StatCard","sourcePath":"components/data/StatCard.jsx"},{"name":"Banner","sourcePath":"components/feedback/Banner.jsx"},{"name":"Dialog","sourcePath":"components/feedback/Dialog.jsx"},{"name":"EmptyState","sourcePath":"components/feedback/EmptyState.jsx"},{"name":"Toast","sourcePath":"components/feedback/Toast.jsx"},{"name":"Tooltip","sourcePath":"components/feedback/Tooltip.jsx"},{"name":"Checkbox","sourcePath":"components/forms/Checkbox.jsx"},{"name":"Combobox","sourcePath":"components/forms/Combobox.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"RowList","sourcePath":"components/forms/RowList.jsx"},{"name":"SearchField","sourcePath":"components/forms/SearchField.jsx"},{"name":"Select","sourcePath":"components/forms/Select.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"Pagination","sourcePath":"components/navigation/Pagination.jsx"},{"name":"SidebarNav","sourcePath":"components/navigation/SidebarNav.jsx"},{"name":"Tabs","sourcePath":"components/navigation/Tabs.jsx"},{"name":"Topbar","sourcePath":"components/navigation/Topbar.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"6418cbc851ad","components/core/Button.jsx":"6bc92264bbd1","components/core/Card.jsx":"df55ca6e1cf7","components/core/Icon.jsx":"2f50dd1cde42","components/core/IconButton.jsx":"7b6dfa641079","components/core/Reveal.jsx":"87a4b610b3ea","components/core/Tag.jsx":"b8120079ae6b","components/core/Wordmark.jsx":"ad2aed22a486","components/data/DataTable.jsx":"54bc204302ea","components/data/InvoiceGroup.jsx":"5c3ccf351457","components/data/StatCard.jsx":"34d443f894fc","components/feedback/Banner.jsx":"275a77eb0347","components/feedback/Dialog.jsx":"77e0e64a7f74","components/feedback/EmptyState.jsx":"e4b62ca342ff","components/feedback/Toast.jsx":"a742ace3b0ea","components/feedback/Tooltip.jsx":"662afc701fed","components/forms/Checkbox.jsx":"16989d9c4b7e","components/forms/Combobox.jsx":"8c2d01836efc","components/forms/Input.jsx":"1f31d64028d5","components/forms/RowList.jsx":"e0a0c5641d22","components/forms/SearchField.jsx":"1eca87f0bb65","components/forms/Select.jsx":"325a3dd44351","components/forms/Switch.jsx":"5a7bd315b2f8","components/navigation/Pagination.jsx":"25f10d53cbd3","components/navigation/SidebarNav.jsx":"2aeaf29307bd","components/navigation/Tabs.jsx":"8305d69befe7","components/navigation/Topbar.jsx":"0b535da1b61e","ui_kits/dashboard/AddPartyYarn.jsx":"5b2bbf51fa27","ui_kits/dashboard/ContraEntry.jsx":"b292a877a607","ui_kits/dashboard/Dashboard.jsx":"d52715f3974e","ui_kits/dashboard/KiryanaSales.jsx":"96adee8d9297","ui_kits/dashboard/PartiesList.jsx":"5ed22835efef","ui_kits/dashboard/PurchaseSaleEntry.jsx":"701da9f63abd"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.KhatayOnlineDesignSystem_90c3f9 = window.KhatayOnlineDesignSystem_90c3f9 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const PAD = {
  none: 0,
  sm: '14px',
  md: 'var(--gutter-card)',
  lg: '24px'
};
function Card({
  title,
  subtitle,
  actions,
  footer,
  padding = 'md',
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("section", _extends({
    style: {
      background: 'var(--surface-card)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-card)',
      boxShadow: 'var(--shadow-sm)',
      overflow: 'hidden',
      ...style
    }
  }, rest), title || actions ? /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '14px var(--gutter-card)',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0,
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 'var(--text-h3-size)',
      lineHeight: 'var(--text-h3-lh)',
      letterSpacing: 'var(--text-h3-ls)',
      fontWeight: 'var(--text-h3-weight)'
    }
  }, title), subtitle ? /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '3px 0 0',
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--text-muted)'
    }
  }, subtitle) : null), actions ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      flex: '0 0 auto'
    }
  }, actions) : null) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: PAD[padding]
    }
  }, children), footer ? /*#__PURE__*/React.createElement("footer", {
    style: {
      padding: '12px var(--gutter-card)',
      borderTop: '1px solid var(--border-subtle)',
      background: 'var(--surface-sunken)'
    }
  }, footer) : null);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/* Lucide (CDN, UMD) is the brand icon set. The host page must include:
   <script src="https://unpkg.com/lucide@0.544.0/dist/umd/lucide.js"></script> */
function Icon({
  name,
  size = 18,
  strokeWidth = 2,
  color = 'currentColor',
  style,
  ...rest
}) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    const host = ref.current;
    if (!host) return;
    let timer = null;
    const draw = () => {
      if (!window.lucide || !host) return false;
      host.innerHTML = '';
      const i = document.createElement('i');
      i.setAttribute('data-lucide', name);
      i.setAttribute('width', size);
      i.setAttribute('height', size);
      i.setAttribute('stroke-width', strokeWidth);
      host.appendChild(i);
      window.lucide.createIcons();
      return true;
    };
    if (!draw()) timer = setInterval(() => {
      if (draw()) clearInterval(timer);
    }, 60);
    return () => timer && clearInterval(timer);
  }, [name, size, strokeWidth]);
  return /*#__PURE__*/React.createElement("span", _extends({
    ref: ref,
    "aria-hidden": "true",
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: size,
      height: size,
      color,
      flex: '0 0 auto',
      ...style
    }
  }, rest));
}
Object.assign(__ds_scope, { Icon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONE = {
  neutral: ['var(--status-neutral-fg)', 'var(--status-neutral-bg)', 'var(--status-neutral-border)'],
  ok: ['var(--status-ok-fg)', 'var(--status-ok-bg)', 'var(--status-ok-border)'],
  warn: ['var(--status-warn-fg)', 'var(--status-warn-bg)', 'var(--status-warn-border)'],
  danger: ['var(--status-danger-fg)', 'var(--status-danger-bg)', 'var(--status-danger-border)'],
  info: ['var(--status-info-fg)', 'var(--status-info-bg)', 'var(--status-info-border)'],
  brand: ['var(--text-brand)', 'var(--indigo-50)', 'var(--indigo-100)']
};
function Badge({
  tone = 'neutral',
  icon,
  dot = false,
  children,
  style,
  ...rest
}) {
  const [fg, bg, bd] = TONE[tone] || TONE.neutral;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '5px',
      height: '22px',
      padding: '0 8px',
      borderRadius: 'var(--radius-xs)',
      background: bg,
      color: fg,
      border: '1px solid ' + bd,
      fontSize: 'var(--text-caption-size)',
      fontWeight: 'var(--fw-semibold)',
      lineHeight: 1,
      whiteSpace: 'nowrap',
      ...style
    }
  }, rest), dot ? /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: '50%',
      background: fg
    }
  }) : null, icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 12
  }) : null, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const HEIGHT = {
  sm: 'var(--control-height-sm)',
  md: 'var(--control-height-md)',
  lg: 'var(--control-height-lg)'
};
const PAD = {
  sm: '0 10px',
  md: '0 14px',
  lg: '0 18px'
};
const FONT = {
  sm: '13px',
  md: '14px',
  lg: '15px'
};
const LOOK = {
  primary: {
    background: 'var(--indigo-600)',
    color: 'var(--text-on-brand)',
    border: '1px solid var(--indigo-600)',
    boxShadow: 'var(--shadow-xs)'
  },
  secondary: {
    background: 'var(--surface-card)',
    color: 'var(--text-body)',
    border: '1px solid var(--border-default)',
    boxShadow: 'var(--shadow-xs)'
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-body)',
    border: '1px solid transparent',
    boxShadow: 'none'
  },
  danger: {
    background: 'var(--red-500)',
    color: 'var(--white)',
    border: '1px solid var(--red-500)',
    boxShadow: 'var(--shadow-xs)'
  },
  highlight: {
    background: 'var(--amber-300)',
    color: 'var(--ink-900)',
    border: '1px solid var(--amber-400)',
    boxShadow: 'var(--shadow-xs)'
  }
};
const HOVER = {
  primary: {
    background: 'var(--indigo-700)',
    borderColor: 'var(--indigo-700)'
  },
  secondary: {
    background: 'var(--surface-hover)',
    borderColor: 'var(--border-strong)'
  },
  ghost: {
    background: 'var(--ink-50)'
  },
  danger: {
    background: 'var(--red-600)',
    borderColor: 'var(--red-600)'
  },
  highlight: {
    background: 'var(--amber-400)',
    borderColor: 'var(--amber-500)'
  }
};
function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconEnd,
  fullWidth = false,
  disabled = false,
  loading = false,
  type = 'button',
  children,
  style,
  onClick,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const [down, setDown] = React.useState(false);
  const base = LOOK[variant] || LOOK.primary;
  const off = disabled || loading;
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: off,
    onClick: off ? undefined : onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setDown(false);
    },
    onMouseDown: () => setDown(true),
    onMouseUp: () => setDown(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '7px',
      height: HEIGHT[size],
      padding: PAD[size],
      width: fullWidth ? '100%' : undefined,
      fontFamily: 'var(--font-sans)',
      fontSize: FONT[size],
      fontWeight: 'var(--fw-semibold)',
      letterSpacing: '-0.005em',
      whiteSpace: 'nowrap',
      borderRadius: 'var(--radius-control)',
      cursor: off ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-control), transform var(--dur-instant) var(--ease-standard)',
      transform: down && !off ? 'translateY(0.5px)' : 'none',
      ...base,
      ...(hover && !off ? HOVER[variant] : null),
      ...(off ? {
        background: variant === 'ghost' ? 'transparent' : 'var(--surface-disabled)',
        color: 'var(--text-disabled)',
        borderColor: 'var(--border-subtle)',
        boxShadow: 'none'
      } : null),
      ...style
    }
  }, rest), loading ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "loader-circle",
    size: size === 'sm' ? 14 : 16,
    style: {
      animation: 'khatay-spin 900ms linear infinite'
    }
  }) : icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: size === 'sm' ? 14 : 16
  }) : null, children, iconEnd && !loading ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: iconEnd,
    size: size === 'sm' ? 14 : 16
  }) : null);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Reveal.jsx
try { (() => {
/**
 * Wraps content that appears/disappears based on another field (e.g. Type=Broker, Mode=Cheque).
 * Always mount this - never conditionally render it away - so the height animates instead of jumping.
 */
function Reveal({
  show,
  children,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateRows: show ? '1fr' : '0fr',
      opacity: show ? 1 : 0,
      transition: 'grid-template-rows var(--dur-slow) var(--ease-out), opacity var(--dur-base) var(--ease-out)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      overflow: 'hidden',
      minHeight: 0
    }
  }, children));
}
Object.assign(__ds_scope, { Reveal });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Reveal.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Tag({
  children,
  selected = false,
  onRemove,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const interactive = Boolean(onClick);
  return /*#__PURE__*/React.createElement("span", _extends({
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      height: '26px',
      padding: onRemove ? '0 6px 0 10px' : '0 11px',
      borderRadius: 'var(--radius-chip)',
      background: selected ? 'var(--indigo-600)' : hover && interactive ? 'var(--ink-50)' : 'var(--surface-card)',
      color: selected ? 'var(--text-on-brand)' : 'var(--text-body)',
      border: '1px solid ' + (selected ? 'var(--indigo-600)' : 'var(--border-default)'),
      fontSize: '13px',
      fontWeight: 'var(--fw-medium)',
      cursor: interactive ? 'pointer' : 'default',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), children, onRemove ? /*#__PURE__*/React.createElement("span", {
    onClick: e => {
      e.stopPropagation();
      onRemove(e);
    },
    style: {
      display: 'inline-flex',
      cursor: 'pointer',
      opacity: 0.6
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 13
  })) : null);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/core/Wordmark.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const SIZES = {
  sm: [15, 26, 6.5],
  md: [17, 30, 7.5],
  lg: [22, 38, 9.5]
};
function Wordmark({
  size = 'md',
  mono = false,
  showTagline = false,
  style,
  ...rest
}) {
  const [fs, box, mfs] = SIZES[size] || SIZES.md;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '9px',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: box,
      height: box,
      borderRadius: 'var(--radius-md)',
      flex: '0 0 auto',
      background: mono ? 'var(--white)' : 'var(--indigo-600)',
      color: mono ? 'var(--indigo-700)' : 'var(--white)',
      fontFamily: 'var(--font-sans)',
      fontWeight: 'var(--fw-extrabold)',
      fontSize: mfs * 2 + 'px',
      letterSpacing: '-0.05em'
    }
  }, "KO"), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      lineHeight: 1.05
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: fs + 'px',
      fontWeight: 'var(--fw-bold)',
      letterSpacing: '-0.02em',
      color: mono ? 'var(--white)' : 'var(--text-heading)'
    }
  }, "Khatay", /*#__PURE__*/React.createElement("span", {
    style: {
      color: mono ? 'var(--white)' : 'var(--indigo-600)'
    }
  }, "\xA0Online")), showTagline ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: '10px',
      fontWeight: 'var(--fw-semibold)',
      letterSpacing: '0.07em',
      textTransform: 'uppercase',
      color: mono ? 'var(--ink-300)' : 'var(--text-subtle)',
      marginTop: 3
    }
  }, "Inventory for local shops") : null));
}
Object.assign(__ds_scope, { Wordmark });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Wordmark.jsx", error: String((e && e.message) || e) }); }

// components/data/DataTable.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function DataTable({
  columns = [],
  rows = [],
  dense = false,
  onRowClick,
  style,
  ...rest
}) {
  const [hoverRow, setHoverRow] = React.useState(null);
  const h = dense ? 'var(--row-height-dense)' : 'var(--row-height)';
  const cell = align => ({
    padding: '0 14px',
    textAlign: align || 'left',
    verticalAlign: 'middle'
  });
  return /*#__PURE__*/React.createElement("table", _extends({
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: 'var(--text-body-size)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      height: '38px',
      background: 'var(--surface-sunken)'
    }
  }, columns.map(c => /*#__PURE__*/React.createElement("th", {
    key: c.key,
    style: {
      ...cell(c.align),
      height: '38px',
      width: c.width,
      fontSize: 'var(--text-label-size)',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-muted)',
      borderBottom: '1px solid var(--border-subtle)',
      whiteSpace: 'nowrap'
    }
  }, c.label)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: r.id || i,
    onMouseEnter: () => setHoverRow(i),
    onMouseLeave: () => setHoverRow(null),
    onClick: () => onRowClick && onRowClick(r),
    style: {
      height: h,
      background: hoverRow === i ? 'var(--surface-hover)' : 'var(--surface-card)',
      borderBottom: '1px solid var(--border-subtle)',
      cursor: onRowClick ? 'pointer' : 'default',
      transition: 'background-color var(--dur-fast) var(--ease-standard)'
    }
  }, columns.map(c => /*#__PURE__*/React.createElement("td", {
    key: c.key,
    className: c.numeric ? 'tabular' : undefined,
    style: {
      ...cell(c.align),
      color: c.emphasis ? 'var(--text-heading)' : 'var(--text-body)',
      fontWeight: c.emphasis ? 'var(--fw-medium)' : 'var(--fw-regular)'
    }
  }, c.render ? c.render(r) : r[c.key]))))));
}
Object.assign(__ds_scope, { DataTable });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/DataTable.jsx", error: String((e && e.message) || e) }); }

// components/data/StatCard.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function StatCard({
  label,
  value,
  unit,
  delta,
  deltaDirection = 'up',
  caption,
  icon,
  tone = 'neutral',
  style,
  ...rest
}) {
  const good = deltaDirection === 'up';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      padding: 'var(--gutter-card)',
      background: tone === 'highlight' ? 'var(--surface-highlight)' : tone === 'danger' ? 'var(--status-danger-bg)' : 'var(--surface-card)',
      border: '1px solid ' + (tone === 'highlight' ? 'var(--status-warn-border)' : tone === 'danger' ? 'var(--status-danger-border)' : 'var(--border-subtle)'),
      borderRadius: 'var(--radius-card)',
      boxShadow: 'var(--shadow-sm)',
      minWidth: 0,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    }
  }, icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 16,
    color: tone === 'danger' ? 'var(--status-danger-fg)' : 'var(--text-subtle)'
  }) : null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-label-size)',
      fontWeight: 'var(--fw-medium)',
      color: tone === 'danger' ? 'var(--status-danger-fg)' : 'var(--text-muted)'
    }
  }, label)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: '6px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "tabular",
    style: {
      fontSize: 'var(--text-metric-size)',
      lineHeight: 'var(--text-metric-lh)',
      letterSpacing: 'var(--text-metric-ls)',
      fontWeight: 'var(--text-metric-weight)',
      color: tone === 'danger' ? 'var(--status-danger-fg)' : 'var(--text-heading)'
    }
  }, value), unit ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '14px',
      color: 'var(--text-muted)'
    }
  }, unit) : null), delta || caption ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      flexWrap: 'wrap'
    }
  }, delta ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '3px',
      fontSize: 'var(--text-caption-size)',
      fontWeight: 'var(--fw-semibold)',
      color: good ? 'var(--status-ok-fg)' : 'var(--status-danger-fg)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: good ? 'trending-up' : 'trending-down',
    size: 13
  }), delta) : null, caption ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: tone === 'danger' ? 'var(--status-danger-fg)' : 'var(--text-subtle)'
    }
  }, caption) : null) : null);
}
Object.assign(__ds_scope, { StatCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/StatCard.jsx", error: String((e && e.message) || e) }); }

// components/feedback/EmptyState.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function EmptyState({
  icon = 'package-open',
  title,
  message,
  action,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      textAlign: 'center',
      gap: '6px',
      padding: '40px 24px',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 44,
      height: 44,
      marginBottom: 6,
      borderRadius: 'var(--radius-lg)',
      background: 'var(--surface-sunken)',
      border: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 21,
    color: "var(--text-subtle)"
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 'var(--text-h3-size)',
      fontWeight: 'var(--text-h3-weight)'
    }
  }, title), message ? /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      maxWidth: 320,
      fontSize: '14px',
      color: 'var(--text-muted)'
    }
  }, message) : null, action ? /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10
    }
  }, action) : null);
}
Object.assign(__ds_scope, { EmptyState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/EmptyState.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Tooltip.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Tooltip({
  label,
  placement = 'top',
  children,
  style,
  ...rest
}) {
  const [show, setShow] = React.useState(false);
  const pos = {
    top: {
      bottom: '100%',
      left: '50%',
      transform: 'translate(-50%, -6px)'
    },
    bottom: {
      top: '100%',
      left: '50%',
      transform: 'translate(-50%, 6px)'
    },
    left: {
      right: '100%',
      top: '50%',
      transform: 'translate(-6px, -50%)'
    },
    right: {
      left: '100%',
      top: '50%',
      transform: 'translate(6px, -50%)'
    }
  }[placement];
  return /*#__PURE__*/React.createElement("span", _extends({
    onMouseEnter: () => setShow(true),
    onMouseLeave: () => setShow(false),
    style: {
      position: 'relative',
      display: 'inline-flex',
      ...style
    }
  }, rest), children, show ? /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      ...pos,
      zIndex: 70,
      whiteSpace: 'nowrap',
      pointerEvents: 'none',
      padding: '5px 8px',
      borderRadius: 'var(--radius-xs)',
      background: 'var(--ink-800)',
      color: 'var(--white)',
      fontSize: 'var(--text-caption-size)',
      fontWeight: 'var(--fw-medium)',
      boxShadow: 'var(--shadow-md)',
      animation: 'khatay-fade var(--dur-fast) var(--ease-out)'
    }
  }, label) : null);
}
Object.assign(__ds_scope, { Tooltip });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Tooltip.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const BOX = {
  sm: 'var(--control-height-sm)',
  md: 'var(--control-height-md)',
  lg: 'var(--control-height-lg)'
};
function IconButton({
  icon,
  label,
  size = 'md',
  variant = 'ghost',
  active = false,
  disabled = false,
  disabledReason,
  onClick,
  style,
  ...rest
}) {
  const [hover, setHover] = React.useState(false);
  const bordered = variant === 'secondary';
  const softDisabled = Boolean(disabledReason);
  const off = disabled || softDisabled;
  const btn = /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    "aria-label": label,
    "aria-disabled": off || undefined,
    title: softDisabled ? undefined : label,
    disabled: disabled,
    onClick: softDisabled ? undefined : onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: BOX[size],
      height: BOX[size],
      borderRadius: 'var(--radius-control)',
      background: active ? 'var(--surface-selected)' : hover && !off ? 'var(--ink-50)' : bordered ? 'var(--surface-card)' : 'transparent',
      color: off ? 'var(--text-disabled)' : active ? 'var(--text-brand)' : 'var(--text-muted)',
      border: bordered ? '1px solid var(--border-default)' : '1px solid transparent',
      boxShadow: bordered ? 'var(--shadow-xs)' : 'none',
      cursor: off ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: size === 'sm' ? 15 : size === 'lg' ? 20 : 17
  }));
  return softDisabled ? /*#__PURE__*/React.createElement(__ds_scope.Tooltip, {
    label: disabledReason
  }, btn) : btn;
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/data/InvoiceGroup.jsx
try { (() => {
const TYPE_TONE = {
  sale: 'ok',
  purchase: 'info',
  return: 'warn',
  quotation: 'neutral'
};
const TYPE_LABEL = {
  sale: 'Sale',
  purchase: 'Purchase',
  return: 'Return',
  quotation: 'Quotation'
};
const money = n => 'Rs ' + Math.round(n).toLocaleString('en-PK');
function InvoiceGroup({
  voucherNo,
  date,
  type = 'sale',
  party,
  lines = [],
  total,
  defaultExpanded = false,
  onPrint,
  onEditLine,
  onDeleteLine,
  style
}) {
  const [open, setOpen] = React.useState(defaultExpanded);
  const summary = lines.map(l => l.item).join(', ');
  const computedTotal = total != null ? total : lines.reduce((s, l) => s + l.qty * l.rate, 0);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      borderBottom: '1px solid var(--border-subtle)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: () => setOpen(o => !o),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '14px',
      padding: '14px 20px',
      cursor: 'pointer',
      background: open ? 'var(--surface-hover)' : 'var(--surface-card)',
      transition: 'var(--transition-control)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: open ? 'chevron-down' : 'chevron-right',
    size: 16,
    color: "var(--text-subtle)"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
      minWidth: 0,
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '14px',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-heading)'
    }
  }, voucherNo), /*#__PURE__*/React.createElement(__ds_scope.Badge, {
    tone: TYPE_TONE[type]
  }, TYPE_LABEL[type]), party ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)'
    }
  }, party) : null), /*#__PURE__*/React.createElement("span", {
    title: summary,
    style: {
      display: 'flex',
      alignItems: 'baseline',
      gap: '5px',
      minWidth: 0,
      fontSize: '13px',
      color: 'var(--text-muted)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, summary), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: '0 0 auto',
      color: 'var(--text-subtle)'
    }
  }, "(", lines.length, " ", lines.length === 1 ? 'item' : 'items', ")"))), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '13px',
      color: 'var(--text-subtle)',
      flex: '0 0 auto'
    }
  }, date), /*#__PURE__*/React.createElement("span", {
    className: "tabular",
    style: {
      fontSize: '15px',
      fontWeight: 'var(--fw-bold)',
      color: 'var(--text-heading)',
      flex: '0 0 auto',
      minWidth: 90,
      textAlign: 'right'
    }
  }, money(computedTotal)), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "printer",
    label: 'Print ' + voucherNo,
    size: "sm",
    onClick: e => {
      e.stopPropagation();
      onPrint && onPrint();
    }
  })), open ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '4px 20px 16px 50px',
      background: 'var(--surface-sunken)'
    }
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontSize: '13px'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      height: '32px'
    }
  }, /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'left',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-muted)',
      fontSize: 'var(--text-label-size)',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, "Item"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-muted)',
      fontSize: 'var(--text-label-size)',
      borderBottom: '1px solid var(--border-subtle)',
      width: 80
    }
  }, "Qty"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-muted)',
      fontSize: 'var(--text-label-size)',
      borderBottom: '1px solid var(--border-subtle)',
      width: 100
    }
  }, "Rate"), /*#__PURE__*/React.createElement("th", {
    style: {
      textAlign: 'right',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-muted)',
      fontSize: 'var(--text-label-size)',
      borderBottom: '1px solid var(--border-subtle)',
      width: 110
    }
  }, "Amount"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: 76,
      borderBottom: '1px solid var(--border-subtle)'
    }
  }))), /*#__PURE__*/React.createElement("tbody", null, lines.map((l, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      height: '36px',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      color: 'var(--text-body)'
    }
  }, l.item), /*#__PURE__*/React.createElement("td", {
    className: "tabular",
    style: {
      textAlign: 'right',
      color: 'var(--text-body)'
    }
  }, l.qty), /*#__PURE__*/React.createElement("td", {
    className: "tabular",
    style: {
      textAlign: 'right',
      color: 'var(--text-body)'
    }
  }, money(l.rate)), /*#__PURE__*/React.createElement("td", {
    className: "tabular",
    style: {
      textAlign: 'right',
      fontWeight: 'var(--fw-medium)',
      color: 'var(--text-heading)'
    }
  }, money(l.qty * l.rate)), /*#__PURE__*/React.createElement("td", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: '2px'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "pencil",
    label: 'Edit ' + l.item,
    size: "sm",
    onClick: () => onEditLine && onEditLine(l, i)
  }), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "trash-2",
    label: 'Delete ' + l.item,
    size: "sm",
    onClick: () => onDeleteLine && onDeleteLine(l, i)
  })))))))) : null);
}
Object.assign(__ds_scope, { InvoiceGroup });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/InvoiceGroup.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Banner.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONE = {
  info: ['info', 'var(--status-info-fg)', 'var(--status-info-bg)', 'var(--status-info-border)'],
  ok: ['circle-check', 'var(--status-ok-fg)', 'var(--status-ok-bg)', 'var(--status-ok-border)'],
  warn: ['triangle-alert', 'var(--status-warn-fg)', 'var(--status-warn-bg)', 'var(--status-warn-border)'],
  danger: ['circle-alert', 'var(--status-danger-fg)', 'var(--status-danger-bg)', 'var(--status-danger-border)']
};
function Banner({
  tone = 'info',
  title,
  children,
  action,
  onDismiss,
  style,
  ...rest
}) {
  const [icon, fg, bg, bd] = TONE[tone] || TONE.info;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
      padding: '12px 14px',
      background: bg,
      border: '1px solid ' + bd,
      borderRadius: 'var(--radius-md)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 17,
    color: fg,
    style: {
      marginTop: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, title ? /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      fontWeight: 'var(--fw-semibold)',
      color: 'var(--text-heading)'
    }
  }, title) : null, children ? /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--text-body)',
      marginTop: title ? 2 : 0
    }
  }, children) : null), action ? /*#__PURE__*/React.createElement("div", {
    style: {
      flex: '0 0 auto'
    }
  }, action) : null, onDismiss ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Dismiss",
    size: "sm",
    onClick: onDismiss
  }) : null);
}
Object.assign(__ds_scope, { Banner });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Banner.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Dialog.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Dialog({
  open = false,
  title,
  description,
  footer,
  width = 460,
  onClose,
  children,
  style,
  ...rest
}) {
  if (!open) return null;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--surface-overlay)',
      backdropFilter: 'blur(2px)',
      zIndex: 60,
      padding: '24px',
      animation: 'khatay-fade var(--dur-base) var(--ease-out)'
    },
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", _extends({
    role: "dialog",
    "aria-modal": "true",
    onClick: e => e.stopPropagation(),
    style: {
      width,
      maxWidth: '100%',
      maxHeight: '100%',
      background: 'var(--surface-card)',
      borderRadius: 'var(--radius-modal)',
      boxShadow: 'var(--shadow-modal)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      animation: 'khatay-rise var(--dur-slow) var(--ease-out)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("header", {
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '12px',
      padding: '18px 20px 0',
      flex: '0 0 auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 'var(--text-h2-size)',
      lineHeight: 'var(--text-h2-lh)',
      letterSpacing: 'var(--text-h2-ls)',
      fontWeight: 'var(--text-h2-weight)'
    }
  }, title), description ? /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '6px 0 0',
      fontSize: '14px',
      color: 'var(--text-muted)'
    }
  }, description) : null), onClose ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Close",
    size: "sm",
    onClick: onClose
  }) : null), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 20px',
      overflowY: 'auto',
      minHeight: 0
    }
  }, children), footer ? /*#__PURE__*/React.createElement("footer", {
    style: {
      display: 'flex',
      justifyContent: 'flex-end',
      gap: '8px',
      padding: '14px 20px',
      borderTop: '1px solid var(--border-subtle)',
      background: 'var(--surface-sunken)',
      flex: '0 0 auto'
    }
  }, footer) : null));
}
Object.assign(__ds_scope, { Dialog });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Dialog.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Toast.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONE = {
  ok: ['circle-check', 'var(--green-500)'],
  warn: ['triangle-alert', 'var(--amber-400)'],
  danger: ['circle-x', 'var(--red-500)'],
  info: ['info', 'var(--blue-500)']
};
function Toast({
  tone = 'ok',
  title,
  message,
  action,
  onDismiss,
  style,
  ...rest
}) {
  const [icon, color] = TONE[tone] || TONE.info;
  return /*#__PURE__*/React.createElement("div", _extends({
    role: "status",
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '10px',
      width: 360,
      padding: '12px 12px 12px 14px',
      background: 'var(--surface-inverse)',
      color: 'var(--text-inverse)',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-lg)',
      animation: 'khatay-rise var(--dur-slow) var(--ease-out)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 17,
    color: color,
    style: {
      marginTop: 1
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      fontWeight: 'var(--fw-semibold)'
    }
  }, title), message ? /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--ink-200)',
      marginTop: 2
    }
  }, message) : null, action ? /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8
    }
  }, action) : null), onDismiss ? /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "x",
    label: "Dismiss",
    size: "sm",
    onClick: onDismiss,
    style: {
      color: 'var(--ink-300)'
    }
  }) : null);
}
Object.assign(__ds_scope, { Toast });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Toast.jsx", error: String((e && e.message) || e) }); }

// components/forms/Checkbox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Checkbox({
  label,
  description,
  checked,
  indeterminate = false,
  disabled = false,
  onChange,
  style,
  ...rest
}) {
  const on = checked || indeterminate;
  return /*#__PURE__*/React.createElement("label", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'flex-start',
      gap: '9px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.55 : 1,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: Boolean(checked),
    disabled: disabled,
    onChange: onChange,
    style: {
      position: 'absolute',
      opacity: 0,
      width: 0,
      height: 0
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 17,
      height: 17,
      marginTop: 1,
      borderRadius: 'var(--radius-xs)',
      flex: '0 0 auto',
      background: on ? 'var(--indigo-600)' : 'var(--surface-card)',
      border: '1px solid ' + (on ? 'var(--indigo-600)' : 'var(--border-strong)'),
      transition: 'var(--transition-control)'
    }
  }, indeterminate ? /*#__PURE__*/React.createElement("span", {
    style: {
      width: 8,
      height: 1.5,
      background: 'var(--white)'
    }
  }) : checked ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "check",
    size: 12,
    color: "var(--white)",
    strokeWidth: 3
  }) : null), label ? /*#__PURE__*/React.createElement("span", {
    style: {
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: '14px',
      color: 'var(--text-body)'
    }
  }, label), description ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)',
      marginTop: 2
    }
  }, description) : null) : null);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Combobox.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const H = {
  sm: 'var(--control-height-sm)',
  md: 'var(--control-height-md)',
  lg: 'var(--control-height-lg)'
};
function Combobox({
  label,
  hint,
  error,
  required = false,
  placeholder = 'Search…',
  options = [],
  value,
  onChange,
  size = 'md',
  disabled = false,
  allowClear = true,
  allowCreate = false,
  entityLabel = 'entry',
  onCreate,
  id,
  containerStyle,
  defaultOpen = false,
  defaultQuery = '',
  ...rest
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const [query, setQuery] = React.useState(defaultQuery);
  const [menuRect, setMenuRect] = React.useState(null);
  const rootRef = React.useRef(null);
  const menuRef = React.useRef(null);
  const uid = id || React.useMemo(() => 'cb-' + Math.random().toString(36).slice(2, 8), []);
  const selected = options.find(o => o.value === value);
  React.useEffect(() => {
    const onDoc = e => {
      const insideRoot = rootRef.current && rootRef.current.contains(e.target);
      const insideMenu = menuRef.current && menuRef.current.contains(e.target);
      if (!insideRoot && !insideMenu) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);
  React.useEffect(() => {
    if (!open) return;
    const updateRect = () => {
      if (rootRef.current) setMenuRect(rootRef.current.getBoundingClientRect());
    };
    updateRect();
    window.addEventListener('scroll', updateRect, true);
    window.addEventListener('resize', updateRect);
    return () => {
      window.removeEventListener('scroll', updateRect, true);
      window.removeEventListener('resize', updateRect);
    };
  }, [open]);
  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter(o => o.label.toLowerCase().includes(q) || (o.meta || '').toLowerCase().includes(q));
  }, [options, query]);
  const borderColor = error ? 'var(--red-500)' : open ? 'var(--border-focus)' : 'var(--border-default)';
  const trimmed = query.trim();
  const exactMatch = trimmed && options.some(o => o.label.toLowerCase() === trimmed.toLowerCase());
  const showCreate = allowCreate && trimmed.length > 0 && !exactMatch;
  const handleCreate = () => {
    onCreate && onCreate(trimmed);
    setOpen(false);
    setQuery('');
  };
  const rowCount = filtered.length + (showCreate ? 1 : 0);
  const scrollable = rowCount > 6;
  return /*#__PURE__*/React.createElement("div", {
    ref: rootRef,
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      minWidth: 0,
      position: 'relative',
      ...containerStyle
    }
  }, label ? /*#__PURE__*/React.createElement("label", {
    htmlFor: uid,
    style: {
      fontSize: 'var(--text-label-size)',
      fontWeight: 'var(--text-label-weight)',
      color: 'var(--text-body)'
    }
  }, label, required ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--red-500)'
    }
  }, " *") : null) : null, /*#__PURE__*/React.createElement("div", {
    onClick: () => !disabled && setOpen(true),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      height: H[size],
      padding: '0 8px 0 10px',
      background: disabled ? 'var(--surface-disabled)' : 'var(--surface-card)',
      border: '1px solid ' + borderColor,
      borderRadius: 'var(--radius-control)',
      boxShadow: open ? 'var(--focus-ring)' : 'var(--shadow-xs)',
      cursor: disabled ? 'not-allowed' : 'text',
      transition: 'var(--transition-control)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "search",
    size: 15,
    color: "var(--text-subtle)"
  }), open ? /*#__PURE__*/React.createElement("input", _extends({
    id: uid,
    autoFocus: true,
    disabled: disabled,
    value: query,
    onChange: e => setQuery(e.target.value),
    placeholder: selected ? selected.label : placeholder,
    style: {
      flex: 1,
      minWidth: 0,
      border: 'none',
      outline: 'none',
      background: 'transparent',
      fontFamily: 'var(--font-sans)',
      fontSize: '14px',
      color: 'var(--text-heading)'
    }
  }, rest)) : /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      fontSize: '14px',
      color: selected ? 'var(--text-heading)' : 'var(--text-subtle)'
    }
  }, selected ? selected.label : placeholder), selected && allowClear && !disabled ? /*#__PURE__*/React.createElement("span", {
    onClick: e => {
      e.stopPropagation();
      onChange && onChange('');
    },
    style: {
      display: 'inline-flex',
      cursor: 'pointer',
      color: 'var(--text-subtle)'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "x",
    size: 14
  })) : /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 14,
    color: "var(--text-subtle)"
  })), open && !disabled && menuRect ? /*#__PURE__*/ReactDOM.createPortal(/*#__PURE__*/React.createElement("div", {
    ref: menuRef,
    style: {
      position: 'fixed',
      top: menuRect.bottom + 4,
      left: menuRect.left,
      width: menuRect.width,
      zIndex: 1000,
      maxHeight: scrollable ? '260px' : 'none',
      overflow: scrollable ? 'auto' : 'visible',
      background: 'var(--surface-card)',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-lg)',
      padding: '4px'
    }
  }, filtered.length === 0 && !showCreate ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '14px 10px',
      fontSize: '13px',
      color: 'var(--text-subtle)',
      textAlign: 'center'
    }
  }, "No matches") : filtered.map(o => /*#__PURE__*/React.createElement("div", {
    key: o.value,
    onClick: () => {
      onChange && onChange(o.value);
      setOpen(false);
      setQuery('');
    },
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '8px',
      padding: '8px 10px',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer',
      background: o.value === value ? 'var(--surface-selected)' : 'transparent'
    },
    onMouseEnter: e => {
      if (o.value !== value) e.currentTarget.style.background = 'var(--surface-hover)';
    },
    onMouseLeave: e => {
      if (o.value !== value) e.currentTarget.style.background = 'transparent';
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '14px',
      color: 'var(--text-heading)',
      fontWeight: o.value === value ? 'var(--fw-semibold)' : 'var(--fw-regular)'
    }
  }, o.label), o.meta ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)'
    }
  }, o.meta) : null)), showCreate ? /*#__PURE__*/React.createElement("div", {
    onClick: handleCreate,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 10px',
      marginTop: filtered.length ? '4px' : 0,
      borderTop: filtered.length ? '1px solid var(--border-subtle)' : 'none',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer'
    },
    onMouseEnter: e => {
      e.currentTarget.style.background = 'var(--surface-hover)';
    },
    onMouseLeave: e => {
      e.currentTarget.style.background = 'transparent';
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "circle-plus",
    size: 15,
    color: "var(--indigo-600)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '14px',
      color: 'var(--indigo-600)',
      fontWeight: 'var(--fw-semibold)'
    }
  }, "Add \"", trimmed, "\" as a new ", entityLabel)) : null), document.body) : null, error ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--status-danger-fg)'
    }
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Combobox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Combobox.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const H = {
  sm: 'var(--control-height-sm)',
  md: 'var(--control-height-md)',
  lg: 'var(--control-height-lg)'
};
function Input({
  label,
  hint,
  error,
  icon,
  prefix,
  suffix,
  size = 'md',
  required = false,
  disabled = false,
  id,
  style,
  containerStyle,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const uid = id || React.useMemo(() => 'in-' + Math.random().toString(36).slice(2, 8), []);
  const borderColor = error ? 'var(--red-500)' : focus ? 'var(--border-focus)' : 'var(--border-default)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      minWidth: 0,
      ...containerStyle
    }
  }, label ? /*#__PURE__*/React.createElement("label", {
    htmlFor: uid,
    style: {
      fontSize: 'var(--text-label-size)',
      lineHeight: 'var(--text-label-lh)',
      fontWeight: 'var(--text-label-weight)',
      color: 'var(--text-body)'
    }
  }, label, required ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--red-500)'
    }
  }, " *") : null) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      height: H[size],
      padding: '0 10px',
      background: disabled ? 'var(--surface-disabled)' : 'var(--surface-card)',
      border: '1px solid ' + borderColor,
      borderRadius: 'var(--radius-control)',
      boxShadow: focus ? 'var(--focus-ring)' : 'var(--shadow-xs)',
      transition: 'var(--transition-control)'
    }
  }, icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: icon,
    size: 16,
    color: "var(--text-subtle)"
  }) : null, prefix ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '13px',
      color: 'var(--text-muted)',
      flex: '0 0 auto'
    }
  }, prefix) : null, /*#__PURE__*/React.createElement("input", _extends({
    id: uid,
    disabled: disabled,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      flex: 1,
      minWidth: 0,
      border: 'none',
      outline: 'none',
      background: 'transparent',
      fontFamily: 'var(--font-sans)',
      fontSize: size === 'lg' ? '15px' : '14px',
      color: 'var(--text-heading)',
      ...style
    }
  }, rest)), suffix ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '13px',
      color: 'var(--text-muted)',
      flex: '0 0 auto'
    }
  }, suffix) : null), error ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--status-danger-fg)'
    }
  }, error) : hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/RowList.jsx
try { (() => {
/**
 * header renders once as column labels; each row is plain controls (no per-row <label>s) so the
 * remove icon sits center-aligned with the row's fields.
 */
function RowList({
  header,
  rows,
  renderRow,
  onAdd,
  onRemove,
  addLabel = 'Add row',
  minRows = 1,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      ...style
    }
  }, header ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      gap: '10px'
    }
  }, header), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 'var(--control-height-md)',
      flex: '0 0 auto'
    }
  })) : null, rows.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: r.id != null ? r.id : i,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      display: 'flex',
      gap: '10px'
    }
  }, renderRow(r, i)), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "trash-2",
    label: "Remove row",
    size: "md",
    disabled: rows.length <= minRows,
    disabledReason: rows.length <= minRows ? 'At least one row is required' : undefined,
    onClick: () => onRemove(i)
  }))), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "secondary",
    icon: "plus",
    onClick: onAdd,
    style: {
      alignSelf: 'flex-start'
    }
  }, addLabel));
}
Object.assign(__ds_scope, { RowList });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/RowList.jsx", error: String((e && e.message) || e) }); }

// components/forms/SearchField.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function SearchField({
  value,
  placeholder = 'Search products, barcodes…',
  shortcut,
  onChange,
  width = 320,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      width,
      height: 'var(--control-height-md)',
      padding: '0 10px',
      background: 'var(--surface-card)',
      border: '1px solid ' + (focus ? 'var(--border-focus)' : 'var(--border-default)'),
      borderRadius: 'var(--radius-control)',
      boxShadow: focus ? 'var(--focus-ring)' : 'var(--shadow-xs)',
      transition: 'var(--transition-control)',
      ...style
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "search",
    size: 16,
    color: "var(--text-subtle)"
  }), /*#__PURE__*/React.createElement("input", _extends({
    value: value,
    onChange: onChange,
    placeholder: placeholder,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      flex: 1,
      minWidth: 0,
      border: 'none',
      outline: 'none',
      background: 'transparent',
      fontFamily: 'var(--font-sans)',
      fontSize: '14px',
      color: 'var(--text-heading)'
    }
  }, rest)), shortcut ? /*#__PURE__*/React.createElement("kbd", {
    style: {
      padding: '2px 5px',
      borderRadius: 'var(--radius-xs)',
      background: 'var(--surface-sunken)',
      border: '1px solid var(--border-subtle)',
      fontSize: '11px',
      color: 'var(--text-subtle)',
      fontFamily: 'var(--font-mono)'
    }
  }, shortcut) : null);
}
Object.assign(__ds_scope, { SearchField });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/SearchField.jsx", error: String((e && e.message) || e) }); }

// components/forms/Select.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const H = {
  sm: 'var(--control-height-sm)',
  md: 'var(--control-height-md)',
  lg: 'var(--control-height-lg)'
};
function Select({
  label,
  hint,
  options = [],
  size = 'md',
  disabled = false,
  id,
  containerStyle,
  style,
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const uid = id || React.useMemo(() => 'sel-' + Math.random().toString(36).slice(2, 8), []);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '6px',
      minWidth: 0,
      ...containerStyle
    }
  }, label ? /*#__PURE__*/React.createElement("label", {
    htmlFor: uid,
    style: {
      fontSize: 'var(--text-label-size)',
      fontWeight: 'var(--text-label-weight)',
      color: 'var(--text-body)'
    }
  }, label) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      display: 'flex',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("select", _extends({
    id: uid,
    disabled: disabled,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      appearance: 'none',
      width: '100%',
      height: H[size],
      padding: '0 32px 0 10px',
      background: disabled ? 'var(--surface-disabled)' : 'var(--surface-card)',
      border: '1px solid ' + (focus ? 'var(--border-focus)' : 'var(--border-default)'),
      borderRadius: 'var(--radius-control)',
      boxShadow: focus ? 'var(--focus-ring)' : 'var(--shadow-xs)',
      fontFamily: 'var(--font-sans)',
      fontSize: '14px',
      color: disabled ? 'var(--text-disabled)' : 'var(--text-heading)',
      cursor: disabled ? 'not-allowed' : 'pointer',
      transition: 'var(--transition-control)',
      ...style
    }
  }, rest), options.map(o => {
    const opt = typeof o === 'string' ? {
      value: o,
      label: o
    } : o;
    return /*#__PURE__*/React.createElement("option", {
      key: opt.value,
      value: opt.value
    }, opt.label);
  })), /*#__PURE__*/React.createElement(__ds_scope.Icon, {
    name: "chevron-down",
    size: 15,
    color: "var(--text-subtle)",
    style: {
      position: 'absolute',
      right: 10,
      pointerEvents: 'none'
    }
  })), hint ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)'
    }
  }, hint) : null);
}
Object.assign(__ds_scope, { Select });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Select.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Switch({
  checked = false,
  label,
  disabled = false,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("label", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '10px',
      cursor: disabled ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.55 : 1,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    role: "switch",
    "aria-checked": checked,
    onClick: () => !disabled && onChange && onChange(!checked),
    style: {
      position: 'relative',
      width: 36,
      height: 20,
      borderRadius: 'var(--radius-pill)',
      flex: '0 0 auto',
      background: checked ? 'var(--indigo-600)' : 'var(--ink-200)',
      transition: 'background-color var(--dur-base) var(--ease-standard)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      top: 2,
      left: checked ? 18 : 2,
      width: 16,
      height: 16,
      borderRadius: '50%',
      background: 'var(--white)',
      boxShadow: 'var(--shadow-xs)',
      transition: 'left var(--dur-base) var(--ease-standard)'
    }
  })), label ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '14px',
      color: 'var(--text-body)'
    }
  }, label) : null);
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Pagination.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Pagination({
  page = 1,
  pageCount = 1,
  rangeLabel,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      ...style
    }
  }, rest), rangeLabel ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--text-muted)'
    }
  }, rangeLabel) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
      marginLeft: 'auto'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "chevron-left",
    label: "Previous page",
    size: "sm",
    variant: "secondary",
    disabled: page <= 1,
    onClick: () => onChange && onChange(page - 1)
  }), /*#__PURE__*/React.createElement("span", {
    className: "tabular",
    style: {
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--text-body)',
      padding: '0 4px'
    }
  }, page, " / ", pageCount), /*#__PURE__*/React.createElement(__ds_scope.IconButton, {
    icon: "chevron-right",
    label: "Next page",
    size: "sm",
    variant: "secondary",
    disabled: page >= pageCount,
    onClick: () => onChange && onChange(page + 1)
  })));
}
Object.assign(__ds_scope, { Pagination });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Pagination.jsx", error: String((e && e.message) || e) }); }

// components/navigation/SidebarNav.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function SidebarNav({
  items = [],
  value,
  onChange,
  footer,
  header,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("nav", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      width: 'var(--sidebar-width)',
      flex: '0 0 auto',
      background: 'var(--surface-card)',
      borderRight: '1px solid var(--border-subtle)',
      ...style
    }
  }, rest), header ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 16px 12px'
    }
  }, header) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '2px',
      padding: '4px 10px',
      flex: 1,
      overflowY: 'auto'
    }
  }, items.map((raw, i) => {
    if (raw.section) return /*#__PURE__*/React.createElement("div", {
      key: 's' + i,
      style: {
        padding: '14px 8px 6px',
        fontSize: 'var(--text-overline-size)',
        letterSpacing: 'var(--text-overline-ls)',
        textTransform: 'uppercase',
        fontWeight: 'var(--text-overline-weight)',
        color: 'var(--text-subtle)'
      }
    }, raw.section);
    const on = raw.id === value;
    return /*#__PURE__*/React.createElement(raw.href ? "a" : "button", {
      key: raw.id,
      href: raw.href,
      onClick: raw.href ? undefined : () => onChange && onChange(raw.id),
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        height: '36px',
        padding: '0 10px',
        width: '100%',
        background: on ? 'var(--surface-selected)' : 'transparent',
        border: 'none',
        borderRadius: 'var(--radius-control)',
        color: on ? 'var(--text-brand)' : 'var(--text-body)',
        fontFamily: 'var(--font-sans)',
        fontSize: '14px',
        fontWeight: on ? 'var(--fw-semibold)' : 'var(--fw-regular)',
        cursor: 'pointer',
        textAlign: 'left',
        textDecoration: 'none',
        boxSizing: 'border-box',
        transition: 'var(--transition-control)'
      }
    }, /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: raw.icon,
      size: 17,
      color: on ? 'var(--indigo-600)' : 'var(--text-subtle)'
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        flex: 1,
        minWidth: 0,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, raw.label), raw.badge != null ? /*#__PURE__*/React.createElement("span", {
      style: {
        padding: '1px 6px',
        borderRadius: 'var(--radius-pill)',
        background: 'var(--status-warn-bg)',
        color: 'var(--status-warn-fg)',
        fontSize: '11px',
        fontWeight: 'var(--fw-semibold)'
      }
    }, raw.badge) : null);
  })), footer ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '12px 16px',
      borderTop: '1px solid var(--border-subtle)'
    }
  }, footer) : null);
}
Object.assign(__ds_scope, { SidebarNav });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/SidebarNav.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Tabs.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Tabs({
  items = [],
  value,
  onChange,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    role: "tablist",
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '2px',
      borderBottom: '1px solid var(--border-subtle)',
      ...style
    }
  }, rest), items.map(raw => {
    const it = typeof raw === 'string' ? {
      id: raw,
      label: raw
    } : raw;
    const on = it.id === value;
    return /*#__PURE__*/React.createElement("button", {
      key: it.id,
      role: "tab",
      "aria-selected": on,
      onClick: () => onChange && onChange(it.id),
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        gap: '7px',
        height: '38px',
        padding: '0 12px',
        background: 'transparent',
        border: 'none',
        borderBottom: '2px solid ' + (on ? 'var(--indigo-600)' : 'transparent'),
        marginBottom: '-1px',
        color: on ? 'var(--text-heading)' : 'var(--text-muted)',
        fontFamily: 'var(--font-sans)',
        fontSize: '14px',
        fontWeight: on ? 'var(--fw-semibold)' : 'var(--fw-medium)',
        cursor: 'pointer',
        transition: 'var(--transition-control)'
      }
    }, it.icon ? /*#__PURE__*/React.createElement(__ds_scope.Icon, {
      name: it.icon,
      size: 15
    }) : null, it.label, it.count != null ? /*#__PURE__*/React.createElement("span", {
      style: {
        padding: '1px 6px',
        borderRadius: 'var(--radius-pill)',
        background: on ? 'var(--indigo-50)' : 'var(--surface-sunken)',
        color: on ? 'var(--text-brand)' : 'var(--text-muted)',
        fontSize: '11px',
        fontWeight: 'var(--fw-semibold)'
      }
    }, it.count) : null);
  }));
}
Object.assign(__ds_scope, { Tabs });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Tabs.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Topbar.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function Topbar({
  title,
  subtitle,
  breadcrumb,
  search,
  actions,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("header", _extends({
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      minHeight: 'var(--topbar-height)',
      padding: '0 var(--gutter-page)',
      background: 'var(--surface-card)',
      borderBottom: '1px solid var(--border-subtle)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      minWidth: 0,
      flex: 1
    }
  }, breadcrumb ? /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--text-caption-size)',
      color: 'var(--text-subtle)',
      marginBottom: 2
    }
  }, breadcrumb) : null, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--text-h2-size)',
      lineHeight: 'var(--text-h2-lh)',
      letterSpacing: 'var(--text-h2-ls)',
      fontWeight: 'var(--text-h2-weight)'
    }
  }, title), subtitle ? /*#__PURE__*/React.createElement("p", {
    style: {
      margin: '2px 0 0',
      fontSize: 'var(--text-body-sm-size)',
      color: 'var(--text-muted)'
    }
  }, subtitle) : null), search ? /*#__PURE__*/React.createElement("div", {
    style: {
      flex: '0 0 auto'
    }
  }, search) : null, actions ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      flex: '0 0 auto'
    }
  }, actions) : null);
}
Object.assign(__ds_scope, { Topbar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Topbar.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Reveal = __ds_scope.Reveal;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Wordmark = __ds_scope.Wordmark;

__ds_ns.DataTable = __ds_scope.DataTable;

__ds_ns.InvoiceGroup = __ds_scope.InvoiceGroup;

__ds_ns.StatCard = __ds_scope.StatCard;

__ds_ns.Banner = __ds_scope.Banner;

__ds_ns.Dialog = __ds_scope.Dialog;

__ds_ns.EmptyState = __ds_scope.EmptyState;

__ds_ns.Toast = __ds_scope.Toast;

__ds_ns.Tooltip = __ds_scope.Tooltip;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Combobox = __ds_scope.Combobox;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.RowList = __ds_scope.RowList;

__ds_ns.SearchField = __ds_scope.SearchField;

__ds_ns.Select = __ds_scope.Select;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.Pagination = __ds_scope.Pagination;

__ds_ns.SidebarNav = __ds_scope.SidebarNav;

__ds_ns.Tabs = __ds_scope.Tabs;

__ds_ns.Topbar = __ds_scope.Topbar;

})();
