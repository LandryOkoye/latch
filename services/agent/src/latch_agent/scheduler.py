import argparse
import time
from datetime import datetime, timedelta

from latch_core import ledger
from latch_core.models import Loop, LoopEventType, LoopStatus

from latch_agent import inbox
from latch_agent.agents.pursuer import pursue

_NORMAL_TICK_SECONDS = 60
_FAST_TICK_SECONDS = 5
FOLLOW_UP_AFTER = timedelta(days=3)


def _last_touch(loop: Loop) -> datetime:
    touches = [e.occurred_at for e in loop.events if e.event_type == LoopEventType.TOUCHED]
    return max(touches) if touches else loop.due_at


def loops_due_for_pursuit(now: datetime) -> list[Loop]:
    """Overdue OPEN loops, plus AWAITING_REPLY loops whose last chase has gone
    unanswered for FOLLOW_UP_AFTER. A loop with children was deferred, and its
    newest child carries the live commitment, so it is never chased itself."""
    due = []
    for loop in ledger.list_loops():
        if loop.due_at > now:
            continue
        if loop.status == LoopStatus.OPEN:
            due.append(loop)
        elif loop.status == LoopStatus.AWAITING_REPLY and not ledger.fetch_children(loop.id):
            loop = ledger.get_loop(loop.id)
            if now - _last_touch(loop) >= FOLLOW_UP_AFTER:
                due.append(loop)
    return due


def tick() -> dict:
    """Adjudicate any new replies first (so a loop that was just answered isn't
    chased again), then invoke the Pursuer on every loop due for pursuit."""
    replies = inbox.process_replies()
    pursued = []
    for loop in loops_due_for_pursuit(datetime.now()):
        pursue(loop.id)
        pursued.append(loop.id)
    return {"replies": replies, "pursued": pursued}


def run(interval_seconds: float) -> None:
    print(f"scheduler starting, tick every {interval_seconds}s")
    while True:
        result = tick()
        stamp = datetime.now().isoformat(timespec="seconds")
        for reply in result["replies"]:
            print(f"[{stamp}] reply on {reply['loop_id']}: verdict={reply['verdict']} status={reply['status']}")
        if result["pursued"]:
            print(f"[{stamp}] pursued {len(result['pursued'])} loop(s): {result['pursued']}")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Adjudicate new replies and pursue overdue loops.")
    parser.add_argument("--fast", action="store_true", help="compressed tick interval for demo recording")
    args = parser.parse_args()
    run(_FAST_TICK_SECONDS if args.fast else _NORMAL_TICK_SECONDS)


if __name__ == "__main__":
    main()
