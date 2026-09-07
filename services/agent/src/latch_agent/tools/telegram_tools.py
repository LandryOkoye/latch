import json
import urllib.error
import urllib.request

from latch_core import config


def send_telegram(recipient_label: str, text: str) -> bool:
    """Send a message via the configured Telegram bot to the one dedicated pursuit
    chat. Returns False if not configured or on failure — callers must treat that
    as 'channel unavailable', not raise."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": config.TELEGRAM_CHAT_ID, "text": f"[{recipient_label}] {text}"}).encode()
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False
