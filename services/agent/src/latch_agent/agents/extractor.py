import uuid
from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel

from latch_core import config
from latch_core.models import Loop, MeetingTranscript, WindowSource


class ExtractedLoop(BaseModel):
    promise: str
    source_quote: str
    owner_name: str
    owner_email: str
    counterparty_org: str
    due_at: datetime
    window_source: WindowSource
    closure_criterion: str
    stakes: Literal["low", "medium", "high"]


class ExtractionResult(BaseModel):
    loops: list[ExtractedLoop]


_SYSTEM_PROMPT = """You extract tracked commitments ("loops") from a meeting transcript.

A loop exists whenever someone personally commits to a follow-up action, even a
vague one with no date — "I'll send X by Y", "we'll get you Z", "I'll look into W
and get back to you", "we'll circle back on that". The commitment itself can be
vague (no date, no detail on what they'll find) — that just makes it an INFERRED
window, not a reason to exclude it. Only exclude a sentence when NOBODY actually
commits to anything: a suggestion, a hypothetical, or a "someday" aspiration with
no owner taking it on.

Examples of REAL loops (extract these, even though vague):
- "We'll circle back on that once finance has looked at it." → owner commits to
  following up, even with no date. Extract as INFERRED.
- "I'll look into the staging server slowness and get back to you." → owner
  commits to an action and a follow-up. Extract as INFERRED.

Examples of NEAR-MISSES (do NOT extract these):
- "We should probably think about doing a full accessibility audit at some
  point." → a suggestion, nobody commits to doing it.
- "We might want to revisit the color palette at some point down the line." →
  a hypothetical for later, nobody commits to anything now.

When in doubt about whether a real commitment was made at all, leave it out —
but do not require a date or detail for something to count as a loop.

For each real loop, extract:
- promise: a short paraphrase of what was committed to.
- source_quote: the exact verbatim sentence(s) from the transcript.
- owner_name / owner_email: whoever made the commitment (the promisor). Match
  owner_email against the participant list given below.
- counterparty_org: the organization the OWNER belongs to (their employer) — not
  the organization receiving the promise. This is the org whose reliability is
  being tracked over time. If no organization name is spoken aloud, derive a
  clean, readable name from the owner's email domain (e.g. brightpathdev.com ->
  BrightPath Dev) — always produce a readable name, never a raw domain string.
- due_at: a concrete date and time. If a date was explicitly stated ("by Friday
  the 21st"), resolve it against the meeting date given below. If no date was
  stated, this is an inferred window: pick a reasonable default (5 business days
  out from the meeting date) based on how the commitment was phrased.
- window_source: "stated" if a date was explicitly mentioned in the transcript,
  "inferred" otherwise.
- closure_criterion: what evidence would prove this loop closed (e.g. "revised
  timeline document sent to Priya").
- stakes: "high" if tied to a client-visible deadline or real consequence,
  "medium" for a normal operational deliverable, "low" for a minor or vague
  follow-up.
"""


def extract_loops(transcript: MeetingTranscript) -> list[Loop]:
    model = BedrockModel(model_id=config.BEDROCK_MODEL_ID, region_name=config.AWS_REGION)
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)

    participants_block = "\n".join(f"- {p.name} <{p.email}>" for p in transcript.participants)
    utterances_block = "\n".join(
        f"[{int(u.timestamp)}s] {u.speaker}: {u.text}" for u in transcript.utterances
    )
    # The model is unreliable at weekday arithmetic, so give it a calendar to read.
    calendar = ", ".join(
        f"{d:%A} {d:%Y-%m-%d}" for d in (transcript.occurred_at + timedelta(days=i) for i in range(1, 15))
    )
    prompt = (
        f"Meeting date: {transcript.occurred_at:%A} {transcript.occurred_at.isoformat()}\n"
        f"Dates after the meeting (use these to resolve weekdays and relative dates): {calendar}\n"
        f"Participants:\n{participants_block}\n\n"
        f"Transcript:\n{utterances_block}"
    )

    result = agent.structured_output(ExtractionResult, prompt)

    now = datetime.now()
    return [
        Loop(
            id=str(uuid.uuid4()),
            parent_id=None,
            promise=el.promise,
            source_quote=el.source_quote,
            source_meeting_id=transcript.meeting_id,
            owner_name=el.owner_name,
            owner_email=el.owner_email,
            counterparty_org=el.counterparty_org,
            due_at=el.due_at,
            window_source=el.window_source,
            closure_criterion=el.closure_criterion,
            stakes=el.stakes,
            created_at=now,
        )
        for el in result.loops
    ]
