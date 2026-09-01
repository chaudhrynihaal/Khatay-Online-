"""
daily_reports.py
------------------
Emails the Receivable, Payable, Cash Book, and Stock reports (as PDF
attachments) to each company's configured notification email, once
per day. Runs completely separately per company - one company's
report failing to send (bad email, no SMTP config, etc.) never blocks
or affects any other company's report.

Meant to run once a day via cron (see deploy/setup_email_reports.sh),
NOT imported by the web app itself.

Requires SMTP credentials as environment variables (set once on the
server, in /opt/ultraerp/.env alongside ULTRAERP_SECRET_KEY):
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM
"""

import os
import smtplib
import ssl
from datetime import date, timedelta
from email.message import EmailMessage

import master
import db
import settings
import pdf_export


def _smtp_config():
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    from_addr = os.environ.get("SMTP_FROM", username)
    if not all([host, username, password]):
        return None
    return {"host": host, "port": port, "username": username, "password": password, "from_addr": from_addr}


def _send_email(smtp_cfg, to_addr, subject, body, attachments):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_cfg["from_addr"]
    msg["To"] = to_addr
    msg.set_content(body)

    for path in attachments:
        if not path or not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            data = f.read()
        msg.add_attachment(data, maintype="application", subtype="pdf",
                            filename=os.path.basename(path))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"]) as server:
        server.starttls(context=context)
        server.login(smtp_cfg["username"], smtp_cfg["password"])
        server.send_message(msg)


def send_daily_reports_for_company(slug, smtp_cfg):
    """Returns (sent: bool, message: str) - never raises, so the
    caller can safely loop over every company regardless of failures."""
    try:
        db.set_active_db_path(master.tenant_db_path(slug))
        to_addr = settings.get_notification_email()
        if not to_addr:
            return False, "no notification email configured"

        as_of = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()

        attachments = [
            pdf_export.generate_receivable_ledger_pdf(as_of),
            pdf_export.generate_payable_ledger_pdf(as_of),
            pdf_export.generate_cash_book_pdf(month_start, as_of),
            pdf_export.generate_stock_report_pdf(),
        ]

        company_name = settings.get_company_name()
        subject = f"{company_name} — Daily Reports for {as_of}"
        body = (
            f"Attached are today's Receivable Ledger, Payable Ledger, "
            f"Cash Book (month to date), and Stock Report for {company_name}.\n\n"
            f"This is an automated daily email."
        )
        _send_email(smtp_cfg, to_addr, subject, body, attachments)
        return True, f"sent to {to_addr}"
    except Exception as exc:
        return False, f"error: {exc}"


def main():
    smtp_cfg = _smtp_config()
    if not smtp_cfg:
        print("SMTP not configured (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD env vars) - nothing to do.")
        return

    master.init_master_db()
    companies = master.list_companies()
    print(f"[{date.today().isoformat()}] Checking {len(companies)} compan{'y' if len(companies)==1 else 'ies'} for daily reports...")

    for c in companies:
        if not master.is_subscription_active(c):
            print(f"  {c['slug']}: skipped (subscription not active)")
            continue
        sent, message = send_daily_reports_for_company(c["slug"], smtp_cfg)
        status = "OK" if sent else "skipped"
        print(f"  {c['slug']}: {status} - {message}")


if __name__ == "__main__":
    main()
