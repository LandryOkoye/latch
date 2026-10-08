import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# packages/core/src/latch_core/config.py -> repo root is 4 parents up. Anchoring
# here keeps every process (API, scheduler, scripts, tests) on the same db file
# regardless of the directory it was launched from.
_REPO_ROOT = Path(__file__).resolve().parents[4]

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
# Spam is polled too: first-contact replies from a new counterparty often land there.
IMAP_REPLY_FOLDERS = os.environ.get("IMAP_REPLY_FOLDERS", "INBOX,[Gmail]/Spam").split(",")

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
SHEET_ID = os.environ.get("SHEET_ID")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ATTENDEE_API_KEY = os.environ.get("ATTENDEE_API_KEY")

_db_path_raw = os.environ.get("LATCH_DB_PATH", "./latch.db")
DB_PATH = _db_path_raw if os.path.isabs(_db_path_raw) else str(_REPO_ROOT / _db_path_raw)
