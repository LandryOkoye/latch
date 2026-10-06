from datetime import datetime, timedelta

import pytest

from conftest import make_loop
from latch_agent import scheduler
from latch_core import ledger
from latch_core.models import LoopEventType, LoopStatus

pytestmark = pytest.mark.usefixtures("tmp_db")

NOW = datetime.now()


def _due_ids():
    return {loop.id for loop in scheduler.loops_due_for_pursuit(NOW)}


def _touched(days_ago: float, **overrides):
    loop = ledger.create_loop(make_loop(status=LoopStatus.AWAITING_REPLY, **overrides))
    ledger.record_event(loop.id, LoopEventType.TOUCHED, channel="email", occurred_at=NOW - timedelta(days=days_ago))
    return loop


def test_overdue_open_loop_is_due_but_future_one_is_not():
    overdue = ledger.create_loop(make_loop(due_at=NOW - timedelta(hours=1)))
    ledger.create_loop(make_loop(due_at=NOW + timedelta(days=1)))
    assert _due_ids() == {overdue.id}


def test_unanswered_chase_is_re_chased_only_after_follow_up_interval():
    stale = _touched(days_ago=scheduler.FOLLOW_UP_AFTER.days + 1)
    _touched(days_ago=1)
    assert _due_ids() == {stale.id}


def test_deferred_parent_is_never_chased_itself():
    parent = _touched(days_ago=10)
    ledger.create_loop(make_loop(parent_id=parent.id, due_at=NOW + timedelta(days=2)))
    assert _due_ids() == set()


def test_terminal_and_escalated_loops_are_never_chased():
    for status in (LoopStatus.ESCALATED_TO_HUMAN, LoopStatus.CLOSED_CLAIMED, LoopStatus.CLOSED_VERIFIED, LoopStatus.ABANDONED):
        ledger.create_loop(make_loop(status=status, due_at=NOW - timedelta(days=30)))
    assert _due_ids() == set()


def test_tick_processes_replies_before_pursuing(monkeypatch):
    calls = []
    loop = ledger.create_loop(make_loop())
    monkeypatch.setattr(scheduler.inbox, "process_replies", lambda: calls.append("replies") or [])
    monkeypatch.setattr(scheduler, "pursue", lambda loop_id: calls.append(loop_id))

    result = scheduler.tick()

    assert calls == ["replies", loop.id]
    assert result == {"replies": [], "pursued": [loop.id]}
