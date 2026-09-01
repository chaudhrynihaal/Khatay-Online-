#!/bin/bash
# deploy/setup.sh
#
# Run this ONCE on a brand-new Ubuntu 24.04 DigitalOcean droplet, as
# root, after uploading the UltraERP-Web folder. It installs Python,
# Caddy (for automatic HTTPS), rclone (for Backblaze backups), creates
# a dedicated non-root user to run the app, installs the systemd
# service, and sets up the daily backup cron job.
#
# Usage (as root, from inside the UltraERP-Web folder you uploaded):
#   bash deploy/setup.sh
#
# You will be prompted for your domain name partway through - have it
# ready. You'll set up the Backblaze B2 connection details afterward
# with a separate one-time command shown at the end.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Run this as root (or with sudo)."
  exit 1
fi

echo "== ULTRA ERP server setup =="
echo

read -p "Your domain name (e.g. erp.yourcompany.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
  echo "A domain is required for automatic HTTPS. Point its DNS A record at this server's IP first, then re-run this script."
  exit 1
fi

echo "-- Installing Python, zip, and basic tools --"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip zip unzip curl ufw

echo "-- Installing Caddy (automatic HTTPS) --"
apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list > /dev/null
apt-get update -qq
apt-get install -y -qq caddy

echo "-- Installing rclone (for Backblaze B2 backups) --"
curl -s https://rclone.org/install.sh | bash

echo "-- Creating a dedicated user to run the app (not root, for safety) --"
id -u ultraerp &>/dev/null || useradd -m -s /bin/bash ultraerp

echo "-- Copying the app to /opt/ultraerp --"
mkdir -p /opt/ultraerp
cp -r ./* /opt/ultraerp/
chown -R ultraerp:ultraerp /opt/ultraerp

echo "-- Setting up the Python environment --"
sudo -u ultraerp python3 -m venv /opt/ultraerp/venv
sudo -u ultraerp /opt/ultraerp/venv/bin/pip install --quiet -r /opt/ultraerp/requirements.txt

echo "-- Generating a secret key and .env file --"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
cat > /opt/ultraerp/.env <<EOF
ULTRAERP_SECRET_KEY=$SECRET_KEY
# Caddy (see deploy/Caddyfile) always terminates HTTPS in front of this
# app, so it's safe to tell Flask to only ever send the session cookie
# over HTTPS.
ULTRAERP_FORCE_SECURE_COOKIES=1
EOF
chown ultraerp:ultraerp /opt/ultraerp/.env
chmod 600 /opt/ultraerp/.env

echo "-- Installing the systemd service --"
cp /opt/ultraerp/deploy/ultraerp.service /etc/systemd/system/ultraerp.service
systemctl daemon-reload
systemctl enable ultraerp
systemctl restart ultraerp

echo "-- Configuring Caddy for $DOMAIN --"
sed "s/yourdomain.com/$DOMAIN/" /opt/ultraerp/deploy/Caddyfile > /etc/caddy/Caddyfile
systemctl restart caddy

echo "-- Configuring the firewall --"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo
echo "============================================================"
echo " Setup complete!"
echo
echo " Your app should now be live at: https://$DOMAIN"
echo " (it can take a minute for the HTTPS certificate to issue)"
echo
echo " Next steps:"
echo " 1. Check it's running:  systemctl status ultraerp"
echo " 2. Set up automated backups - run:  bash /opt/ultraerp/deploy/setup_backups.sh"
echo "============================================================"
