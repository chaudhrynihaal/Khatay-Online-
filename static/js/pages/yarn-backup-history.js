/* Backup History - wired to app.py's backup_history()/restore_backup()
   routes. Every daily cloud backup, with a serious, deliberately
   friction-heavy Restore confirmation (type RESTORE in all caps) since
   it replaces all of the company's live data. */
(function () {
  const DS = window.KhatayOnlineDesignSystem_90c3f9;
  const { Card, Button, DataTable, EmptyState, Banner, Dialog, Input } = DS;
  const { CsrfField } = window.KhatayDS;
  const h = React.createElement;
  const P = window.__PAGE__;

  function RestoreDialog({ backup, onClose }) {
    const [confirmText, setConfirmText] = React.useState("");
    if (!backup) return null;
    return h(
      Dialog,
      { open: true, onClose: onClose, width: 480, title: "⚠️ Confirm Restore" },
      h("p", null, "You're about to replace ", h("strong", null, "all of your company's current data"), " with the backup from:"),
      h("p", { style: { fontWeight: "var(--fw-bold)", fontSize: "16px" } }, backup.modified),
      h(
        "p",
        { style: { color: "var(--text-subtle)", fontSize: "13px" } },
        "Anything entered after that date will be lost from the live app (though it's safe if you ever need it - today's data is saved separately before this runs). This cannot be undone from within the app."
      ),
      h(
        "form",
        { method: "post", action: P.nav.restoreBackup },
        h(CsrfField, null),
        h("input", { type: "hidden", name: "filename", value: backup.name }),
        h(Input, { label: "Type RESTORE (all capitals) to confirm", name: "confirm_text", value: confirmText, onChange: (e) => setConfirmText(e.target.value), autoComplete: "off" }),
        h(
          "div",
          { style: { display: "flex", gap: "8px", marginTop: "16px" } },
          h(Button, { type: "submit", variant: "danger" }, "Yes, Restore This Backup"),
          h(Button, { type: "button", variant: "secondary", onClick: onClose }, "Cancel")
        )
      )
    );
  }

  function columns(setRestoring) {
    return [
      { key: "modified", label: "Date", emphasis: true },
      { key: "size_kb", label: "Size", numeric: true, align: "right", render: (b) => b.size_kb + " KB" },
      { key: "actions", label: "", align: "right", render: (b) => h(Button, { size: "sm", variant: "danger", onClick: () => setRestoring(b) }, "Restore This") },
    ];
  }

  function Root() {
    const [restoring, setRestoring] = React.useState(null);
    if (!P.available) {
      return h(Card, null, h(EmptyState, { icon: "cloud", title: "Cloud backups aren't set up on this server yet.", message: "Ask your platform administrator to run the backup setup script." }));
    }
    if (P.error) {
      return h(Card, null, h(EmptyState, { icon: "triangle-alert", title: "Couldn't reach cloud storage right now", message: P.error }));
    }
    const backups = P.backups || [];
    return h(
      React.Fragment,
      null,
      h(
        Banner,
        { tone: "info" },
        "Every daily backup your company has ever had, kept permanently. You can restore your live data back to any of these points - this is a serious action, so we'll ask you to confirm carefully, and we always save a safety copy of what's live right now before making any change."
      ),
      h(
        Card,
        { title: "Your backups (" + backups.length + ")", padding: "none" },
        backups.length === 0
          ? h(EmptyState, { icon: "package", title: "No backups yet", message: "The first one is taken the day after backups are set up." })
          : h("div", { style: { overflowX: "auto" } }, h(DataTable, { columns: columns(setRestoring), rows: backups }))
      ),
      h(RestoreDialog, { backup: restoring, onClose: () => setRestoring(null) })
    );
  }

  window.KhatayDS.mountShell({
    activeId: "backup-history",
    topbar: { breadcrumb: "Account", title: "Backup History" },
    content: h(Root),
  });
})();
