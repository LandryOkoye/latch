from datetime import datetime, timedelta

from conftest import make_loop
from latch_agent.agents.pursuer import clean_agent_text
from latch_core import priority, reliability
from latch_core.models import LoopStatus


def test_priority_breakdown_sums_to_total_and_ranks_by_urgency():
    now = datetime.now()
    calm = make_loop(due_at=now - timedelta(days=1), stakes="low")
    urgent = make_loop(due_at=now - timedelta(days=10), stakes="high", deferral_count=2, touch_count=2)

    calm_score = priority.priority_score(calm, now=now)
    urgent_score = priority.priority_score(urgent, counterparty_unreliability=0.5, now=now)

    assert urgent_score["total"] > calm_score["total"]
    assert abs(sum(urgent_score["breakdown"].values()) - urgent_score["total"]) < 0.5


def test_loop_not_yet_due_scores_zero_days_past_window():
    loop = make_loop(due_at=datetime.now() + timedelta(days=3))
    assert priority.priority_score(loop)["breakdown"]["days_past_window"] == 0


def test_reliability_counts_verified_closures_deferrals_and_escalations():
    loops = [
        make_loop(counterparty_org="A", status=LoopStatus.CLOSED_VERIFIED, touch_count=1),
        make_loop(counterparty_org="A", status=LoopStatus.CLOSED_CLAIMED),
        make_loop(counterparty_org="B", deferral_count=1),
        make_loop(counterparty_org="B", status=LoopStatus.ESCALATED_TO_HUMAN),
    ]
    stats = reliability.compute_reliability(loops)

    assert stats["A"]["closed_on_time"] == 1
    assert stats["A"]["unreliability_score"] == 0
    assert stats["B"]["deferral_rate"] == 0.5
    assert stats["B"]["escalation_rate"] == 0.5
    assert stats["B"]["unreliability_score"] == 0.5


def test_clean_agent_text_strips_thinking_and_repeated_final_message():
    raw = (
        "<thinking> check the sheet first </thinking>\n"
        "I sent a follow-up to Marcus.<thinking> done </thinking>\n"
        "I sent a follow-up to Marcus."
    )
    assert clean_agent_text(raw) == "I sent a follow-up to Marcus."
