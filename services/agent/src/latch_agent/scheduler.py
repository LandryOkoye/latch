import argparse
import time
from datetime import datetime

from latch_core import ledger
from latch_core.models import LoopStatus

from latch_agent.agents.pursuer import pursue

_NORMAL_TICK_SECONDS = 60
_FAST_TICK_SECONDS = 5


def tick() -> list[str]:
    """Find OPEN loops past their due_at, invoke the Pursuer on each, and return
    the ids that were pursued this tick."""
    now = datetime.now()
    pursued = []
    for loop in ledger.list_loops(status=LoopStatus.OPEN):
        if loop.due_at <= now:
            pursue(loop.id)
            pursued.append(loop.id)
    return pursued


def run(interval_seconds: float) -> None:
    print(f"scheduler starting, tick every {interval_seconds}s")
    while True:
        pursued = tick()
        if pursued:
            print(f"[{datetime.now().isoformat()}] pursued {len(pursued)} loop(s): {pursued}")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find overdue loops and invoke the Pursuer.")
    parser.add_argument("--fast", action="store_true", help="compressed tick interval for demo recording")
    args = parser.parse_args()
    run(_FAST_TICK_SECONDS if args.fast else _NORMAL_TICK_SECONDS)


if __name__ == "__main__":
    main()
