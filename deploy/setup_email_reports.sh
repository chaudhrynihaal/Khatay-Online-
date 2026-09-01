#!/bin/bash
# deploy/setup_email_reports.sh
#
# Run this ONCE (as root) after deploy/setup.sh has finished, to turn
# on the daily automated email of Receivable/Payable/Cash Book/Stock
# reports to each company's configured notification email.
#
# Have your SMTP details ready first - the company email address plus
# its SMTP server, port, username, and password (most providers show
# these under "SMTP settings" or "Mail client setup" - Gmail/Google
# Workspace, Microsoft 365, and most hosting-provided email all work
# the same way here).
#
# Usage (as root):
#   bash /opt/ultraerp/deploy/setup_email_reports.sh

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Run this as root (or with sudo)."
  exit 1
fi

echo "== Daily email reports setup =="
echo

read -p "SMTP host (e.g. smtp.gmail.com): " SMTP_HOST
read -p "SMTP port (usually 587): " SMTP_PORT
read -p "SMTP username (usually the full email address): " SMTP_USERNAME
read -s -p "SMTP password (hidden as you type): " SMTP_PASSWORD
echo
read -p "\"From\" address to send as [default: same as username]: " SMTP_FROM
SMTP_FROM=${SMTP_FROM:-$SMTP_USERNAME}

# append to the existing .env file (created by setup.sh) rather than
# overwrite it, so ULTRAERP_SECRET_KEY stays intact
{
  echo "SMTP_HOST=$SMTP_HOST"
  echo "SMTP_PORT=$SMTP_PORT"
  echo "SMTP_USERNAME=$SMTP_USERNAME"
  echo "SMTP_PASSWORD=$SMTP_PASSWORD"
  echo "SMTP_FROM=$SMTP_FROM"
} >> /opt/ultraerp/.env
chmod 600 /opt/ultraerp/.env

echo "-- Restarting the app so it picks up the new settings --"
systemctl restart ultraerp

echo "-- Sending a test run now (check for errors below) --"
cd /opt/ultraerp
sudo -u ultraerp bash -c "set -a; source /opt/ultraerp/.env; set +a; /opt/ultraerp/venv/bin/python3 /opt/ultraerp/daily_reports.py"

echo "-- Scheduling this to run daily at 7 AM server time --"
CRON_LINE="0 7 * * * cd /opt/ultraerp && set -a && source /opt/ultraerp/.env && set +a && /opt/ultraerp/venv/bin/python3 /opt/ultraerp/daily_reports.py >> /opt/ultraerp/deploy/email_reports.log 2>&1"
( sudo -u ultraerp crontab -l 2>/dev/null | grep -v "daily_reports.py" ; echo "$CRON_LINE" ) | sudo -u ultraerp crontab -

echo
echo "============================================================"
echo " Daily email reports are set up and will run every day at 7 AM."
echo " Each company only receives reports if they've set a"
echo " notification email in their own Settings page."
echo " Log file: /opt/ultraerp/deploy/email_reports.log"
echo "============================================================"
