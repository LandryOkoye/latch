import uuid
from datetime import datetime, timedelta

from strands import Agent
from strands.models import BedrockModel

from latch_core import config, ledger
from latch_core.models import Loop, LoopEventType, LoopStatus, Verdict, VerdictType, WindowSource

from latch_agent.tools import sheet_tools

_SYSTEM_PROMPT = """You are the Adjudicator: you read a reply to a follow-up chase
about an overdue commitment ("loop") and decide what the reply actually means.
You do not take anyone's word for anything you can't see evidence of — your job is
judgment, and it is fine, expected even, to say you can't tell.

Classify the reply into exactly one verdict:

- CLOSED: the reply asserts the commitment is now done (e.g. "sent it Tuesday",
  "this is done"). You are not verifying the claim yourself — that happens
  separately — you are only recognising that a completion claim was made.
- DEFERRED: the reply makes a new promise without resolving the original one
  ("looking into it", "I'll have it by Friday instead", "still working on it").
  If a new date is mentioned, extract it into new_commitment / new_due_at. If no
  date is given, leave new_due_at unset.
- TRANSFERRED: the reply says responsibility has moved to someone else ("I've
  forwarded this to Dana", "Sam handles this now"). Extract the new owner's name
  and email into new_owner_name / new_owner_email if given (email may be absent
  from the reply itself — leave it unset rather than guessing one).
- DISPUTED: the reply rejects the premise of the original commitment ("we never
  received that request", "that's not what we agreed to").
- AMBIGUOUS: you cannot confidently tell what the reply means, or your confidence
  is below 0.7. This includes one-word replies like "Yes." with no context. Never
  guess — an AMBIGUOUS verdict with a clarifying question is far better than a
  confident wrong guess.

Always set evidence_span to the exact substring of the reply your decision rests
on — never paraphrase it, never leave it empty. Always set confidence honestly:
a genuinely ambiguous reply should score low confidence even if you're forced to
pick a verdict.
"""


def adjudicate(loop: Loop, reply_text: str) -> Verdict:
    model = BedrockModel(model_id=config.BEDROCK_MODEL_ID, region_name=config.AWS_REGION)
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)

    prompt = (
        f'Original commitment: "{loop.source_quote}"\n'
        f"Promise: {loop.promise}\n"
        f"Owner: {loop.owner_name} <{loop.owner_email}>\n"
        f"Due at: {loop.due_at.isoformat()}\n\n"
        f"Reply received:\n{reply_text}\n\n"
        "Classify this reply."
    )

    return agent.structured_output(Verdict, prompt)


_DEFAULT_DEFERRAL_DAYS = 5


def _history_summary(loop: Loop) -> str:
    parts = []
    if loop.touch_count:
        channels = "/".join(loop.channels_tried) or "email"
        plural = "s" if loop.touch_count != 1 else ""
        parts.append(f"we've followed up {loop.touch_count} time{plural} by {channels}")
    if loop.deferral_count:
        plural = "s" if loop.deferral_count != 1 else ""
        parts.append(f"it's been deferred {loop.deferral_count} time{plural} already")
    return "; ".join(parts) if parts else "this hasn't been followed up on yet"


def _draft_handoff_message(loop: Loop, new_owner_name: str) -> str:
    """A history-carrying message for a TRANSFERRED loop's new owner, so they
    don't start from zero."""
    return (
        f"Hi {new_owner_name},\n\n"
        f"This was originally with {loop.owner_name}, who mentioned you're picking it up:\n\n"
        f'"{loop.source_quote}"\n\n'
        f"This was expected by {loop.due_at:%B %d}. Since then, {_history_summary(loop)}.\n\n"
        f"Could you take it from here?"
    )


def apply_verdict(loop_id: str, reply_text: str, verdict: Verdict) -> Loop:
    """Carry out the taxonomy's required action for a verdict (BUILD_PLAN.md §5).
    This is mechanical, not another judgment call — the Adjudicator already
    decided what the reply meant; this makes the ledger reflect it. The full
    reply_text is stored on the event so the UI can highlight evidence_span
    within its original context."""
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise ValueError(f"unknown loop {loop_id}")

    if verdict.verdict == VerdictType.CLOSED:
        record = sheet_tools.check_sheet_record(loop_id)
        if record:
            ledger.update_loop(loop_id, status=LoopStatus.CLOSED_VERIFIED)
            ledger.record_event(
                loop_id, LoopEventType.CLOSED_VERIFIED,
                evidence_span=verdict.evidence_span, reply_text=reply_text,
                detail="verified against system of record",
            )
        else:
            ledger.update_loop(loop_id, status=LoopStatus.CLOSED_CLAIMED)
            ledger.record_event(
                loop_id, LoopEventType.CLOSED_CLAIMED,
                evidence_span=verdict.evidence_span, reply_text=reply_text,
                detail="claimed but not found in system of record; flagged for human review",
            )

    elif verdict.verdict == VerdictType.DEFERRED:
        new_due_at = verdict.new_due_at or (datetime.now() + timedelta(days=_DEFAULT_DEFERRAL_DAYS))
        child = ledger.create_loop(
            Loop(
                id=str(uuid.uuid4()),
                parent_id=loop.id,
                promise=verdict.new_commitment or loop.promise,
                source_quote=verdict.evidence_span,
                source_meeting_id=None,
                owner_name=loop.owner_name,
                owner_email=loop.owner_email,
                counterparty_org=loop.counterparty_org,
                due_at=new_due_at,
                window_source=WindowSource.STATED if verdict.new_due_at else WindowSource.INFERRED,
                closure_criterion=loop.closure_criterion,
                stakes=loop.stakes,
                created_at=datetime.now(),
            )
        )
        # Not LoopStatus.OPEN: that would leave the parent's now-superseded due_at
        # eligible for the scheduler to pursue it a second time alongside the
        # child. AWAITING_REPLY keeps it "not closed" (conceptually still open,
        # per §5) while the child carries the active thread.
        ledger.update_loop(loop_id, deferral_count=loop.deferral_count + 1, status=LoopStatus.AWAITING_REPLY)
        ledger.record_event(
            loop_id, LoopEventType.DEFERRED,
            evidence_span=verdict.evidence_span, reply_text=reply_text,
            detail=f"deferred; child loop {child.id} created",
        )

    elif verdict.verdict == VerdictType.TRANSFERRED:
        new_owner_name = verdict.new_owner_name or loop.owner_name
        new_owner_email = verdict.new_owner_email or loop.owner_email
        handoff_message = _draft_handoff_message(loop, new_owner_name)
        ledger.update_loop(loop_id, owner_name=new_owner_name, owner_email=new_owner_email)
        ledger.record_event(
            loop_id, LoopEventType.TRANSFERRED,
            evidence_span=verdict.evidence_span, reply_text=reply_text,
            detail=f"handoff to {new_owner_name} <{new_owner_email}>: {handoff_message}",
        )

    elif verdict.verdict == VerdictType.DISPUTED:
        ledger.update_loop(loop_id, status=LoopStatus.ESCALATED_TO_HUMAN)
        ledger.record_event(
            loop_id, LoopEventType.DISPUTED,
            evidence_span=verdict.evidence_span, reply_text=reply_text,
            detail="counterparty disputes the premise; escalated",
        )

    elif verdict.verdict == VerdictType.AMBIGUOUS:
        ledger.update_loop(loop_id, status=LoopStatus.ESCALATED_TO_HUMAN)
        ledger.record_event(
            loop_id, LoopEventType.ESCALATED,
            evidence_span=verdict.evidence_span, reply_text=reply_text,
            detail=f"ambiguous reply (confidence={verdict.confidence}); escalated for human review",
        )

    return ledger.get_loop(loop_id)
