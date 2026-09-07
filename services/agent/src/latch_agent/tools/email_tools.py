import email
import imaplib
import smtplib
import time
from email.message import EmailMessage
from email.utils import make_msgid

from latch_core import config


def send_email(to: str, subject: str, body: str, in_reply_to: str | None = None) -> str:
    """Send an email via SMTP. Returns the Message-ID of the sent message."""
    msg = EmailMessage()
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid()
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    return msg["Message-ID"]


def fetch_recent_emails(folder: str = "INBOX", limit: int = 10) -> list[dict]:
    """Fetch the most recent emails from the given folder, newest first."""
    with imaplib.IMAP4_SSL(config.IMAP_HOST, config.IMAP_PORT) as imap:
        imap.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        imap.select(folder)
        _, data = imap.search(None, "ALL")
        ids = data[0].split()[-limit:]
        return [_fetch_and_parse(imap, msg_id) for msg_id in reversed(ids)]


def _fetch_and_parse(imap: imaplib.IMAP4_SSL, msg_id: bytes) -> dict:
    _, msg_data = imap.fetch(msg_id, "(RFC822)")
    parsed = email.message_from_bytes(msg_data[0][1])

    body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                break
    else:
        body = parsed.get_payload(decode=True).decode(parsed.get_content_charset() or "utf-8", errors="replace")

    return {
        "message_id": parsed.get("Message-ID"),
        "in_reply_to": parsed.get("In-Reply-To"),
        "from": parsed.get("From"),
        "to": parsed.get("To"),
        "subject": parsed.get("Subject"),
        "body": body.strip(),
    }


def wait_for_email(subject_contains: str, timeout: float = 60.0, poll_interval: float = 5.0) -> dict | None:
    """Poll the inbox until a message with a matching subject shows up, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for msg in fetch_recent_emails(limit=10):
            if subject_contains in (msg["subject"] or ""):
                return msg
        time.sleep(poll_interval)
    return None
