import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import DATA_DIR, MAIL_TO, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER
from pcc_utils import today_taipei


def _write_local_report(subject: str, html_body: str) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"daily_report_{today_taipei().isoformat()}.html"
    path.write_text(html_body, encoding="utf-8")
    print(f"Local report written: {path}")
    print(f"Subject: {subject}")
    return str(path)


def send_html_email(subject: str, html_body: str, dry_run: bool = False) -> None:
    local_path = _write_local_report(subject, html_body)
    if dry_run:
        print("=== DRY RUN: Email not sent ===")
        print(f"To: {MAIL_TO}")
        preview = html_body[:800].encode("utf-8", errors="replace").decode("utf-8")
        print(preview, "...")
        return

    if not SMTP_USER or not SMTP_PASS:
        print(
            f"Email not sent: SMTP_USER 或 SMTP_PASS 未設定，已改寫本機日報檔 {local_path}"
        )
        return

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
