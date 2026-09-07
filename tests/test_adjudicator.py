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

# (reply text, expected verdict). Includes the exact hard cases from BUILD_PLAN.md
# §D3-T3, plus additional fixtures for full coverage (>= 2 per verdict).
FIXTURES = [
    ("The patient/client was seen on the 14th.", VerdictType.CLOSED),
    ("Sorry for the delay, it went out Tuesday.", VerdictType.CLOSED),
    ("Done — this went out to the client this morning.", VerdictType.CLOSED),
    ("We're looking into it.", VerdictType.DEFERRED),
    ("I'll have it to you by Friday instead, ran into a snag.", VerdictType.DEFERRED),
    ("Still waiting on legal, should have an answer next week.", VerdictType.DEFERRED),
    ("I've forwarded this to Dana in scheduling.", VerdictType.TRANSFERRED),
    ("This actually falls under Raj's team now, loop him in going forward.", VerdictType.TRANSFERRED),
    ("We never received it.", VerdictType.DISPUTED),
    ("That's not something we agreed to — must be a mix-up.", VerdictType.DISPUTED),
    ("Yes.", VerdictType.AMBIGUOUS),
    ("Noted.", VerdictType.AMBIGUOUS),
]


@pytest.mark.parametrize("reply_text,expected", FIXTURES)
def test_adjudicator_fixture(reply_text, expected):
    verdict = adjudicate(_LOOP, reply_text)
    assert verdict.evidence_span, f"empty evidence_span for {reply_text!r}"
    assert verdict.verdict == expected, (
        f"reply {reply_text!r}: expected {expected.value}, got {verdict.verdict.value} "
        f"(confidence={verdict.confidence}, evidence={verdict.evidence_span!r})"
    )
