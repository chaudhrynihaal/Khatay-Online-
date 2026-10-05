#!/bin/bash
# deploy/backup.sh
#
# Backs up EVERY company completely separately - one zip file per
# company, uploaded to its own folder in Backblaze B2. This matters
# because each customer's data should be restorable (or handed back to
# them, or deleted on request) entirely on its own, with zero risk of
# ever touching another customer's data by accident.
#
# Layout in B2:
#   ultraerp-backups/
#     _platform/                    <- your companies/users/subscriptions list
#       platform_20260812_020000.zip
#     al-faisal-yarn-traders/       <- one folder per company (by slug)
#       al-faisal-yarn-traders_20260812_020000.zip
#     chenab-ginners/
#       chenab-ginners_20260812_020000.zip
#
# Runs daily via cron (installed automatically by setup_backups.sh) -
# you shouldn't need to run this by hand, but you can any time with:
#   bash deploy/backup.sh
#
# Every daily backup is kept FOREVER in Backblaze B2 (nothing is ever
# deleted there) - so each customer has a complete, permanent history
# going back to their very first day, not just a recent window. Only
# the last 3 copies are kept on the server's own local disk, since
# that's just a fast same-day restore cache, not the real archive -
# B2 is the permanent one.

set -e

APP_DIR="/opt/ultraerp"
LOCAL_BACKUP_DIR="$APP_DIR/local-backups"
B2_REMOTE="b2backup:khatay-backups"   # matches the rclone remote name set up in setup.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# --- failure alerting: a backup that silently stops working defeats the
# point of having one. Reuses the same SMTP env vars (SMTP_HOST/PORT/
# USERNAME/PASSWORD/FROM) that setup_email_reports.sh already writes to
# .env for the daily report emails - if that script hasn't been run on
# this server, SMTP_HOST is unset and alerting is just silently skipped
# (a real deploy still works without email set up, same as before). ---
set -a; [ -f "$APP_DIR/.env" ] && source "$APP_DIR/.env"; set +a
FAILURES=""

alert_failure() {
    local body="$1"
    echo "[$(date)] ALERT: $body"
    [ -n "$SMTP_HOST" ] || return 0
    "$APP_DIR/venv/bin/python3" - "$body" <<'PYEOF' || echo "[$(date)] (also failed to send the alert email itself - check SMTP settings)"
import os, smtplib, ssl, sys
from email.message import EmailMessage
msg = EmailMessage()
msg["Subject"] = "Khatay Online backup problem"
to_addr = os.environ.get("SMTP_FROM") or os.environ["SMTP_USERNAME"]
msg["From"] = to_addr
msg["To"] = to_addr
msg.set_content(sys.argv[1])
ctx = ssl.create_default_context()
with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as s:
    s.starttls(context=ctx)
    s.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
    s.send_message(msg)
PYEOF
}
# set -e means any failing command aborts the script - catch that and
# alert before exiting, instead of just leaving a silent gap in backup.log
trap 'alert_failure "backup.sh aborted unexpectedly at line $LINENO. Check backup.log on the server."' ERR

mkdir -p "$LOCAL_BACKUP_DIR"
cd "$APP_DIR"

echo "[$(date)] Starting backup run..."

# --- 1. back up the platform database (your list of companies, users,
#        and subscription status - not any one customer's business
#        data, just the account/billing records you manage) ---
if [ -f "ultra_erp_master.db" ]; then
    PLATFORM_ARCHIVE="platform_${TIMESTAMP}.zip"
    mkdir -p "$LOCAL_BACKUP_DIR/_platform"
    zip -q "$LOCAL_BACKUP_DIR/_platform/$PLATFORM_ARCHIVE" ultra_erp_master.db
    rclone copy "$LOCAL_BACKUP_DIR/_platform/$PLATFORM_ARCHIVE" "$B2_REMOTE/_platform/" --quiet
    echo "[$(date)] Platform database backed up."
else
    echo "[$(date)] No ultra_erp_master.db found - skipping platform backup."
fi

# --- 2. back up each company completely separately ---
if [ ! -d "tenants" ]; then
    echo "[$(date)] No tenants/ folder found - nothing else to back up."
    exit 0
fi

COMPANY_COUNT=0
for company_dir in tenants/*/; do
    [ -d "$company_dir" ] || continue
    SLUG=$(basename "$company_dir")
    ARCHIVE_NAME="${SLUG}_${TIMESTAMP}.zip"

    mkdir -p "$LOCAL_BACKUP_DIR/$SLUG"
    zip -rq "$LOCAL_BACKUP_DIR/$SLUG/$ARCHIVE_NAME" "tenants/$SLUG"

    if [ ! -f "$LOCAL_BACKUP_DIR/$SLUG/$ARCHIVE_NAME" ]; then
        echo "[$(date)] WARNING: backup for '$SLUG' was not created - skipping this company, continuing with the rest."
        FAILURES="$FAILURES- $SLUG: backup archive was not created\n"
        continue
    fi

    rclone copy "$LOCAL_BACKUP_DIR/$SLUG/$ARCHIVE_NAME" "$B2_REMOTE/$SLUG/" --quiet

    # local disk is limited, so only keep the last 3 copies here as a
    # fast same-day restore cache - the permanent, never-deleted copy
    # of every single day lives in B2 above
    (cd "$LOCAL_BACKUP_DIR/$SLUG" && ls -1t "${SLUG}"_*.zip 2>/dev/null | tail -n +4 | xargs -r rm --)

    COMPANY_COUNT=$((COMPANY_COUNT + 1))
    echo "[$(date)] Backed up '$SLUG' ($(du -h "$LOCAL_BACKUP_DIR/$SLUG/$ARCHIVE_NAME" | cut -f1))"
done

echo "[$(date)] Backup run complete - $COMPANY_COUNT compan$([ "$COMPANY_COUNT" = "1" ] && echo y || echo ies) backed up separately."

if [ -n "$FAILURES" ]; then
    alert_failure "Backup run finished, but some companies were skipped:\n\n$(echo -e "$FAILURES")\nEverything else backed up normally - check backup.log for details on these."
fi
