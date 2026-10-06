from datetime import datetime, timedelta

import pytest

from latch_agent.agents.adjudicator import adjudicate
from latch_core.models import Loop, VerdictType, WindowSource

_LOOP = Loop(
    id="fixture-loop",
    parent_id=None,
    promise="Send the signed report",
    source_quote="I'll send the signed report by end of week.",
    source_meeting_id=None,
    owner_name="Sample Vendor",
    owner_email="vendor@example.com",
    counterparty_org="Sample Vendor Co",
    due_at=datetime.now() - timedelta(days=5),
    window_source=WindowSource.STATED,
    closure_criterion="Signed report received",
    stakes="medium",
    created_at=datetime.now() - timedelta(days=12),
)

# The BUILD_PLAN.md case-manager hard case: the reply only reads as a closure
# against a commitment about getting the client seen.
_CASE_LOOP = _LOOP.model_copy(
    update={
        "promise": "Get the client seen at the clinic",
        "source_quote": "I'll make sure the patient gets seen at the clinic before the 15th.",
        "owner_name": "Clinic Intake",
        "owner_email": "intake@example-clinic.org",
        "counterparty_org": "Example Clinic",
        "closure_criterion": "Client has been seen at the clinic",
    }
)

# (loop, reply text, expected verdict). Includes the exact hard cases from
# BUILD_PLAN.md §D3-T3, plus additional fixtures for full coverage (>= 2 per verdict).
FIXTURES = [
    (_CASE_LOOP, "The patient/client was seen on the 14th.", VerdictType.CLOSED),
    (_LOOP, "Sorry for the delay, it went out Tuesday.", VerdictType.CLOSED),
    (_LOOP, "Done — this went out to the client this morning.", VerdictType.CLOSED),
    (_LOOP, "We're looking into it.", VerdictType.DEFERRED),
    (_LOOP, "I'll have it to you by Friday instead, ran into a snag.", VerdictType.DEFERRED),
    (_LOOP, "Still waiting on legal, should have an answer next week.", VerdictType.DEFERRED),
    (_LOOP, "I've forwarded this to Dana in scheduling.", VerdictType.TRANSFERRED),
    (_LOOP, "This actually falls under Raj's team now, loop him in going forward.", VerdictType.TRANSFERRED),
    (_LOOP, "We never received it.", VerdictType.DISPUTED),
    (_LOOP, "That's not something we agreed to — must be a mix-up.", VerdictType.DISPUTED),
    (_LOOP, "Yes.", VerdictType.AMBIGUOUS),
    (_LOOP, "Noted.", VerdictType.AMBIGUOUS),
]


@pytest.mark.parametrize("loop,reply_text,expected", FIXTURES, ids=[f[1] for f in FIXTURES])
def test_adjudicator_fixture(loop, reply_text, expected):
    verdict = adjudicate(loop, reply_text)
    assert verdict.evidence_span, f"empty evidence_span for {reply_text!r}"
    assert verdict.verdict == expected, (
        f"reply {reply_text!r}: expected {expected.value}, got {verdict.verdict.value} "
        f"(confidence={verdict.confidence}, evidence={verdict.evidence_span!r})"
    )


def test_relative_deferral_date_resolves_against_today():
    verdict = adjudicate(_LOOP, "Running behind, I'll have it to you next Wednesday instead.")
    assert verdict.verdict == VerdictType.DEFERRED
    assert verdict.new_due_at is not None, "relative date was not resolved"
    today = datetime.now().date()
    assert today < verdict.new_due_at.date() <= today + timedelta(days=14)
    assert verdict.new_due_at.weekday() == 2, f"expected a Wednesday, got {verdict.new_due_at:%A %Y-%m-%d}"
