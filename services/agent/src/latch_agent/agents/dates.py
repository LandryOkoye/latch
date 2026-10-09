from datetime import datetime, timedelta
from typing import Literal

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
Weekday = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def next_weekday(after: datetime, weekday: str, at: datetime) -> datetime:
    """The first `weekday` strictly after `after`, at `at`'s time of day. The model
    names the day; the arithmetic happens here, where it can't be miscounted."""
    days = (WEEKDAYS.index(weekday) - after.weekday()) % 7 or 7
    return datetime.combine((after + timedelta(days=days)).date(), at.time())
