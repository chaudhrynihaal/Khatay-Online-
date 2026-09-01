#!/bin/bash
# deploy/setup_backups.sh
#
# Run this ONCE after deploy/setup.sh has finished, to connect your
# Backblaze B2 account and turn on daily automated backups.
#
# Before running this, sign up at backblaze.com, create a Bucket
# (name it e.g. "ultraerp-backups" - private, not public), then go to
# "Application Keys" and create a New Application Key scoped to just
# that bucket. You'll need the three values it shows you ONCE:
#   - keyID
#   - applicationKey
#   - bucket name
#
# Usage (as root):
#   bash /opt/ultraerp/deploy/setup_backups.sh

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Run this as root (or with sudo)."
  exit 1
fi

echo "== Backblaze B2 backup setup =="
echo "Have your B2 keyID, applicationKey, and bucket name ready (from backblaze.com)."
echo

read -p "B2 bucket name: " B2_BUCKET
read -p "B2 keyID: " B2_KEY_ID
read -s -p "B2 applicationKey (hidden as you type): " B2_APP_KEY
echo

sudo -u ultraerp mkdir -p /home/ultraerp/.config/rclone
sudo -u ultraerp bash -c "cat > /home/ultraerp/.config/rclone/rclone.conf" <<EOF
[b2backup]
type = b2
account = $B2_KEY_ID
key = $B2_APP_KEY
EOF
chmod 600 /home/ultraerp/.config/rclone/rclone.conf

# patch the bucket name into the backup script
sed -i "s#b2backup:ultraerp-backups#b2backup:$B2_BUCKET#" /opt/ultraerp/deploy/backup.sh
chmod +x /opt/ultraerp/deploy/backup.sh

echo "-- Testing the connection --"
sudo -u ultraerp rclone lsd "b2backup:$B2_BUCKET" && echo "Connection OK." || {
  echo "Could not reach the bucket - double check the bucket name, keyID, and applicationKey and try again.";
  exit 1;
}

echo "-- Running a first backup now --"
sudo -u ultraerp bash /opt/ultraerp/deploy/backup.sh

echo "-- Scheduling daily backups at 2 AM server time --"
CRON_LINE="0 2 * * * /opt/ultraerp/deploy/backup.sh >> /opt/ultraerp/deploy/backup.log 2>&1"
( sudo -u ultraerp crontab -l 2>/dev/null | grep -v "ultraerp/deploy/backup.sh" ; echo "$CRON_LINE" ) | sudo -u ultraerp crontab -

echo
echo "============================================================"
echo " Backups are set up and running daily at 2 AM."
echo " First backup already completed - check your B2 bucket."
echo " Log file: /opt/ultraerp/deploy/backup.log"
echo "============================================================"
