import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# In AWS, credentials live in one Secrets Manager secret (a JSON object of the
# same keys as .env). Real environment variables still win over the secret.
_SECRET_ID = os.environ.get("LATCH_SECRET_ID")
if _SECRET_ID:
    import boto3

    _secrets = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    for _key, _value in json.loads(_secrets.get_secret_value(SecretId=_SECRET_ID)["SecretString"]).items():
        os.environ.setdefault(_key, str(_value))

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

# Service-account key as a file path (local) or as the JSON content itself (AWS).
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SERVICE_ACCOUNT_INFO = os.environ.get("GOOGLE_SERVICE_ACCOUNT_INFO")
SHEET_ID = os.environ.get("SHEET_ID")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ATTENDEE_API_KEY = os.environ.get("ATTENDEE_API_KEY")

# Set in AWS so the deployed agents, API, and UI share one ledger; unset locally (SQLite).
DYNAMODB_TABLE = os.environ.get("LATCH_DYNAMODB_TABLE")

_db_path_raw = os.environ.get("LATCH_DB_PATH", "./latch.db")
DB_PATH = _db_path_raw if os.path.isabs(_db_path_raw) else str(_REPO_ROOT / _db_path_raw)
