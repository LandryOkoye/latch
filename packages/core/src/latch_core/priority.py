from datetime import datetime

from latch_core.models import Loop

# priority = (days_past_window * W1) + (stakes_weight * W2) + (deferral_count * W3)
#          + (touch_count * W4) + (counterparty_unreliability * W5)
W1_DAYS_PAST = 3.0
W2_STAKES = 10.0
W3_DEFERRAL = 8.0
W4_TOUCH = 4.0
W5_UNRELIABILITY = 15.0

_STAKES_WEIGHT = {"low": 0.3, "medium": 0.6, "high": 1.0}


def days_past_window(loop: Loop, now: datetime | None = None) -> float:
    now = now or datetime.now()
    return max((now - loop.due_at).total_seconds() / 86400, 0.0)


def priority_score(loop: Loop, counterparty_unreliability: float = 0.0, now: datetime | None = None) -> dict:
    """Computed priority score with its breakdown, so the UI can show *why* a
    loop is ranked where it is, not just the ranking."""
    days = days_past_window(loop, now)
    breakdown = {
        "days_past_window": round(days * W1_DAYS_PAST, 1),
        "stakes": round(_STAKES_WEIGHT.get(loop.stakes, 0.5) * W2_STAKES, 1),
        "deferral_count": round(loop.deferral_count * W3_DEFERRAL, 1),
        "touch_count": round(loop.touch_count * W4_TOUCH, 1),
        "counterparty_unreliability": round(counterparty_unreliability * W5_UNRELIABILITY, 1),
    }
    return {"total": round(sum(breakdown.values()), 1), "breakdown": breakdown}
