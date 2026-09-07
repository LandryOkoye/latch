"""Reset the ledger and load a realistic, pre-aged 12-loop worklist for the demo.

Six of these reuse the real content from demo/transcripts/ (as if the Extractor
had already run on them a while ago); the other six invent two more vendors
(Harlow Legal, Union Freight) with their own aged history, standing in for
meetings that happened before the three transcripts shown live in the demo.
"""

import uuid
from datetime import datetime, timedelta

from latch_core import ledger
from latch_core.models import Loop, LoopEventType, LoopStatus, WindowSource

NOW = datetime.now()


def days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)


def new_loop(**kwargs) -> Loop:
    kwargs.setdefault("id", str(uuid.uuid4()))
    kwargs.setdefault("parent_id", None)
    kwargs.setdefault("status", LoopStatus.OPEN)
    kwargs.setdefault("touch_count", 0)
    kwargs.setdefault("deferral_count", 0)
    kwargs.setdefault("channels_tried", [])
    return Loop(**kwargs)


def seed() -> list[Loop]:
    loops: list[Loop] = []

    # --- 1/2: Marcus Lee / Crestline Print — the flagship "quietly goes stale" loop ---
    marcus_parent = new_loop(
        promise="Send the printed proofs",
        source_quote="We'll get the printed proofs over to you by Friday the 21st.",
        source_meeting_id="2026-08-10-acme-kickoff",
        owner_name="Marcus Lee",
        owner_email="marcus@crestlineprint.com",
        counterparty_org="Crestline Print",
        due_at=days_ago(18),
        window_source=WindowSource.STATED,
        closure_criterion="Printed proofs physically received by Acme",
        stakes="high",
        status=LoopStatus.AWAITING_REPLY,
        touch_count=1,
        deferral_count=1,
        channels_tried=["email"],
        created_at=days_ago(28),
    )
    loops.append(marcus_parent)

    marcus_child = new_loop(
        parent_id=marcus_parent.id,
        promise="Send the printed proofs (re-promised after slipping)",
        source_quote="Sorry — printer delay on our end. I can have them to you by the following Friday instead.",
        source_meeting_id=None,
        owner_name="Marcus Lee",
        owner_email="marcus@crestlineprint.com",
        counterparty_org="Crestline Print",
        due_at=days_ago(5),
        window_source=WindowSource.STATED,
        closure_criterion="Printed proofs physically received by Acme",
        stakes="high",
        status=LoopStatus.ESCALATED_TO_HUMAN,
        touch_count=2,
        deferral_count=0,
        channels_tried=["email"],
        created_at=days_ago(17),
    )
    loops.append(marcus_child)

    # --- 3: Jordan Alvarez / BrightPath Dev — staging env, resolved on time ---
    loops.append(
        new_loop(
            promise="Have the new staging environment ready and send login details",
            source_quote="I'll have the new staging environment ready by this Friday, the 28th, with login details sent over the same day.",
            source_meeting_id="2026-08-24-acme-checkin",
            owner_name="Jordan Alvarez",
            owner_email="jordan@brightpathdev.com",
            counterparty_org="BrightPath Dev",
            due_at=days_ago(10),
            window_source=WindowSource.STATED,
            closure_criterion="Staging URL and login sent to Dana",
            stakes="medium",
            status=LoopStatus.CLOSED_VERIFIED,
            touch_count=0,
            created_at=days_ago(14),
        )
    )

    # --- 4: Priya Shah / Acme Outfitters — vague budget follow-up, still fresh ---
    loops.append(
        new_loop(
            promise="Circle back on the additional budget ask",
            source_quote="We'll circle back on that once finance has looked at it.",
            source_meeting_id="2026-08-24-acme-checkin",
            owner_name="Priya Shah",
            owner_email="priya@acmeoutfitters.com",
            counterparty_org="Acme Outfitters",
            due_at=days_ago(6),
            window_source=WindowSource.INFERRED,
            closure_criterion="Reply with a budget decision",
            stakes="medium",
            created_at=days_ago(14),
        )
    )

    # --- 5: Dana Kim / Fieldstone Digital — timeline, resolved on time ---
    loops.append(
        new_loop(
            promise="Send the revised project timeline",
            source_quote="I'll get you the revised project timeline by Monday the 17th so you've got it ahead of your Tuesday leadership sync.",
            source_meeting_id="2026-08-10-acme-kickoff",
            owner_name="Dana Kim",
            owner_email="dana@fieldstonedigital.com",
            counterparty_org="Fieldstone Digital",
            due_at=days_ago(21),
            window_source=WindowSource.STATED,
            closure_criterion="Revised timeline document sent to Priya",
            stakes="medium",
            status=LoopStatus.CLOSED_VERIFIED,
            created_at=days_ago(28),
        )
    )

    # --- 6: Dana Kim / Fieldstone Digital — follow-up-by-tomorrow, resolved ---
    loops.append(
        new_loop(
            promise="Follow up with Marcus about the proofs and update Priya",
            source_quote="I'll follow up with Marcus about the proofs directly and get you an update by tomorrow.",
            source_meeting_id="2026-09-01-acme-status-sync",
            owner_name="Dana Kim",
            owner_email="dana@fieldstonedigital.com",
            counterparty_org="Fieldstone Digital",
            due_at=days_ago(4),
            window_source=WindowSource.STATED,
            closure_criterion="Update message sent to Priya",
            stakes="low",
            status=LoopStatus.CLOSED_VERIFIED,
            created_at=days_ago(5),
        )
    )

    # --- 7: Jordan Alvarez / BrightPath Dev — performance issue, mid-chase ---
    loops.append(
        new_loop(
            promise="Look into the homepage performance issue",
            source_quote="I'll take a look at that and let you both know what I find.",
            source_meeting_id="2026-09-01-acme-status-sync",
            owner_name="Jordan Alvarez",
            owner_email="jordan@brightpathdev.com",
            counterparty_org="BrightPath Dev",
            due_at=days_ago(4),
            window_source=WindowSource.INFERRED,
            closure_criterion="Reply with findings or a fix",
            stakes="low",
            status=LoopStatus.AWAITING_REPLY,
            touch_count=1,
            channels_tried=["email"],
            created_at=days_ago(5),
        )
    )

    # --- 8/9: Renee Ford / Harlow Legal — deep chase history, channel-switched ---
    harlow_parent = new_loop(
        promise="Send the redlined contract",
        source_quote="I'll get the redlined contract back to you by the end of the week.",
        source_meeting_id=None,
        owner_name="Renee Ford",
        owner_email="renee@harlowlegal.com",
        counterparty_org="Harlow Legal",
        due_at=days_ago(20),
        window_source=WindowSource.STATED,
        closure_criterion="Redlined contract received",
        stakes="high",
        status=LoopStatus.AWAITING_REPLY,
        touch_count=2,
        deferral_count=1,
        channels_tried=["email", "telegram"],
        created_at=days_ago(30),
    )
    loops.append(harlow_parent)

    harlow_child = new_loop(
        parent_id=harlow_parent.id,
        promise="Send the redlined contract (re-promised)",
        source_quote="Apologies, still with our compliance reviewer — I'll have it over in a few more days.",
        source_meeting_id=None,
        owner_name="Renee Ford",
        owner_email="renee@harlowlegal.com",
        counterparty_org="Harlow Legal",
        due_at=days_ago(6),
        window_source=WindowSource.STATED,
        closure_criterion="Redlined contract received",
        stakes="high",
        status=LoopStatus.ESCALATED_TO_HUMAN,
        touch_count=1,
        channels_tried=["email"],
        created_at=days_ago(19),
    )
    loops.append(harlow_child)

    # --- 10: Sam Osei / Union Freight — fresh, just past due ---
    loops.append(
        new_loop(
            promise="Confirm the delivery date for the signage order",
            source_quote="I'll confirm the delivery date with dispatch and send it over.",
            source_meeting_id=None,
            owner_name="Sam Osei",
            owner_email="sam@unionfreight.com",
            counterparty_org="Union Freight",
            due_at=days_ago(2),
            window_source=WindowSource.STATED,
            closure_criterion="Confirmed delivery date received",
            stakes="medium",
            created_at=days_ago(9),
        )
    )

    # --- 11: Sam Osei / Union Freight — vague, aging, one touch already ---
    loops.append(
        new_loop(
            promise="Send the replacement pallet count",
            source_quote="I'll look into the pallet shortage and get back to you.",
            source_meeting_id=None,
            owner_name="Sam Osei",
            owner_email="sam@unionfreight.com",
            counterparty_org="Union Freight",
            due_at=days_ago(9),
            window_source=WindowSource.INFERRED,
            closure_criterion="Reply with the corrected pallet count",
            stakes="low",
            status=LoopStatus.AWAITING_REPLY,
            touch_count=1,
            channels_tried=["email"],
            created_at=days_ago(16),
        )
    )

    # --- 12: Priya Shah / Acme Outfitters — low-stakes, barely overdue ---
    loops.append(
        new_loop(
            promise="Scope out the accessibility audit",
            source_quote="Let me get a rough scope together for that accessibility audit and send it your way.",
            source_meeting_id=None,
            owner_name="Priya Shah",
            owner_email="priya@acmeoutfitters.com",
            counterparty_org="Acme Outfitters",
            due_at=days_ago(1),
            window_source=WindowSource.INFERRED,
            closure_criterion="Scope document received",
            stakes="low",
            created_at=days_ago(8),
        )
    )

    return loops


def _backdated_events(loop: Loop) -> None:
    """Log a plausible event trail so the loop-detail timeline isn't empty."""
    ledger.record_event(loop.id, LoopEventType.CREATED, occurred_at=loop.created_at, detail=f"loop created: {loop.promise!r}")

    span = max((NOW - loop.created_at).total_seconds(), 1)
    for i in range(loop.touch_count):
        occurred_at = loop.created_at + timedelta(seconds=span * (i + 1) / (loop.touch_count + 2))
        channel = loop.channels_tried[min(i, len(loop.channels_tried) - 1)] if loop.channels_tried else "email"
        ledger.record_event(loop.id, LoopEventType.TOUCHED, occurred_at=occurred_at, channel=channel, detail=f"sent follow-up via {channel}")

    for i in range(loop.deferral_count):
        occurred_at = loop.created_at + timedelta(seconds=span * (i + 1) / (loop.deferral_count + 1.5))
        ledger.record_event(loop.id, LoopEventType.DEFERRED, occurred_at=occurred_at, detail="counterparty asked for more time")

    if loop.status == LoopStatus.ESCALATED_TO_HUMAN:
        ledger.record_event(loop.id, LoopEventType.ESCALATED, occurred_at=NOW - timedelta(hours=6), detail="repeated touches with no resolution")
    elif loop.status == LoopStatus.CLOSED_VERIFIED:
        ledger.record_event(loop.id, LoopEventType.CLOSED_VERIFIED, occurred_at=loop.due_at + timedelta(hours=4), detail="confirmed via system of record")


def main() -> None:
    ledger.init_db()
    ledger.reset_db()

    loops = seed()
    for loop in loops:
        ledger.create_loop(loop)
        # create_loop already logs its own CREATED event with occurred_at=now;
        # replace it so _backdated_events can lay down the real backdated trail.
        ledger.delete_events(loop.id)
        _backdated_events(loop)

    print(f"Seeded {len(loops)} loops across {len({loop.counterparty_org for loop in loops})} counterparties.")


if __name__ == "__main__":
    main()
