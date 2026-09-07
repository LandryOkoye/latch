from latch_core import config


def check_sheet_record(loop_id: str) -> dict | None:
    """Look up a row in the counterparty's system-of-record Google Sheet matching
    this loop. Returns None if the sheet isn't configured or no row matches.

    Real gspread-backed lookup lands in D2-T2 — this stub keeps the Pursuer's
    tool surface stable while that's built out.
    """
    if not config.GOOGLE_SERVICE_ACCOUNT_JSON or not config.SHEET_ID:
        return None
    return None
