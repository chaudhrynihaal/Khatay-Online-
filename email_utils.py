"""
email_utils.py
---------------
Shared outbound-email helper for anything the running web app itself
needs to send (currently just password-reset links). Deliberately
separate from daily_reports.py, which is a standalone cron script with
its own copy of this same smtplib/ssl pattern - keeping them apart means
a change here can't accidentally break the unrelated daily report emails.

Uses the same SMTP env vars as the rest of the deployment (see
deploy/setup_email_reports.sh): SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
SMTP_PASSWORD, SMTP_FROM. If they're not set (e.g. local dev, or a
deployment that hasn't run that setup script), send_email() just
returns False instead of raising - callers should treat that as "email
isn't configured" and degrade gracefully, not crash the request.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_configured():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USERNAME") and os.environ.get("SMTP_PASSWORD"))


def send_email(to_addr, subject, body):
    if not smtp_configured():
        return False
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    from_addr = os.environ.get("SMTP_FROM", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(username, password)
        server.send_message(msg)
    return True
