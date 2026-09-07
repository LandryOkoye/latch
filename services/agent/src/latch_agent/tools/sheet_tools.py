import gspread

from latch_core import config

_client: gspread.Client | None = None


def _get_worksheet() -> gspread.Worksheet:
    global _client
    if _client is None:
        _client = gspread.service_account(filename=config.GOOGLE_SERVICE_ACCOUNT_JSON)
    return _client.open_by_key(config.SHEET_ID).sheet1


def check_sheet_record(loop_id: str) -> dict | None:
    """Look up a row in the counterparty's system-of-record Google Sheet matching
    this loop's id (sheet columns: loop_id, status). Returns the row as a dict,
    or None if not configured or no row matches."""
    if not config.GOOGLE_SERVICE_ACCOUNT_JSON or not config.SHEET_ID:
        return None

    worksheet = _get_worksheet()
    for row in worksheet.get_all_records():
        if str(row.get("loop_id", "")).strip() == loop_id:
            return dict(row)
    return None
