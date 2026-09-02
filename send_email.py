import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import MAIL_TO, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER


def send_html_email(subject: str, html_body: str, dry_run: bool = False) -> None:
    if dry_run:
        print("=== DRY RUN: Email not sent ===")
        print(f"To: {MAIL_TO}")
        print(f"Subject: {subject}")
        preview = html_body[:800].encode("utf-8", errors="replace").decode("utf-8")
        print(preview, "...")
        return

    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER 或 SMTP_PASS 未設定，請檢查 .env")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = MAIL_TO
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [MAIL_TO], message.as_string())

    print(f"Email sent to {MAIL_TO}")
