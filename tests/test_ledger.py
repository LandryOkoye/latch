from datetime import datetime, timedelta

import pytest

from conftest import make_loop
from latch_core import ledger
from latch_core.models import LoopEventType, LoopStatus

pytestmark = pytest.mark.usefixtures("tmp_db")


def test_create_and_get_round_trip():
    loop = make_loop(channels_tried=["email"])
    created = ledger.create_loop(loop)

    assert created.model_dump(exclude={"events"}) == loop.model_dump(exclude={"events"})
    assert [e.event_type for e in created.events] == [LoopEventType.CREATED]


def test_get_unknown_loop_returns_none():
    assert ledger.get_loop("missing") is None


def test_update_loop_serialises_enums_lists_and_datetimes():
    loop = ledger.create_loop(make_loop())
    new_due = datetime.now() + timedelta(days=3)

    updated = ledger.update_loop(
        loop.id, status=LoopStatus.AWAITING_REPLY, channels_tried=["email", "telegram"], due_at=new_due,
    )

    assert updated.status == LoopStatus.AWAITING_REPLY
    assert updated.channels_tried == ["email", "telegram"]
    assert updated.due_at == new_due


def test_update_loop_rejects_unknown_and_immutable_fields():
    loop = ledger.create_loop(make_loop())
    with pytest.raises(ValueError):
        ledger.update_loop(loop.id, id="other")
    with pytest.raises(ValueError):
        ledger.update_loop(loop.id, not_a_field=1)


def test_list_loops_filters_by_status_and_orders_by_due_date():
    now = datetime.now()
    later = ledger.create_loop(make_loop(due_at=now + timedelta(days=2)))
    sooner = ledger.create_loop(make_loop(due_at=now - timedelta(days=2)))
    ledger.create_loop(make_loop(status=LoopStatus.ESCALATED_TO_HUMAN))

    assert [l.id for l in ledger.list_loops(status=LoopStatus.OPEN)] == [sooner.id, later.id]
    assert len(ledger.list_loops()) == 3


def test_fetch_children_returns_deferral_chain_in_creation_order():
    parent = ledger.create_loop(make_loop())
    first = ledger.create_loop(make_loop(parent_id=parent.id, created_at=datetime.now() - timedelta(days=2)))
    second = ledger.create_loop(make_loop(parent_id=parent.id, created_at=datetime.now()))

    assert [c.id for c in ledger.fetch_children(parent.id)] == [first.id, second.id]
    assert ledger.fetch_children(second.id) == []


def test_record_event_and_find_by_message_id():
    loop = ledger.create_loop(make_loop())
    ledger.record_event(loop.id, LoopEventType.TOUCHED, channel="email", message_id="<abc@mail>")

    found = ledger.find_event_by_message_id("<abc@mail>")
    assert found.loop_id == loop.id
    assert ledger.find_event_by_message_id("<nope@mail>") is None


def test_meeting_ingested():
    ledger.create_loop(make_loop(source_meeting_id="kickoff"))
    assert ledger.meeting_ingested("kickoff")
    assert not ledger.meeting_ingested("other")
