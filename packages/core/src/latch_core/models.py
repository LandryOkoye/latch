from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class WindowSource(str, Enum):
    STATED = "stated"
    INFERRED = "inferred"


class LoopStatus(str, Enum):
    OPEN = "open"
    AWAITING_REPLY = "awaiting_reply"
    CLOSED_VERIFIED = "closed_verified"
    CLOSED_CLAIMED = "closed_claimed"
    ESCALATED_TO_HUMAN = "escalated_to_human"
    ABANDONED = "abandoned"


class LoopEventType(str, Enum):
    CREATED = "created"
    TOUCHED = "touched"
    REPLY_RECEIVED = "reply_received"
    DEFERRED = "deferred"
    TRANSFERRED = "transferred"
    DISPUTED = "disputed"
    ESCALATED = "escalated"
    CLOSED_VERIFIED = "closed_verified"
    CLOSED_CLAIMED = "closed_claimed"
    ABANDONED = "abandoned"


class VerdictType(str, Enum):
    CLOSED = "closed"
    DEFERRED = "deferred"
    TRANSFERRED = "transferred"
    DISPUTED = "disputed"
    AMBIGUOUS = "ambiguous"


class Participant(BaseModel):
    name: str
    email: str | None = None


class Utterance(BaseModel):
    speaker: str
    speaker_email: str | None = None
    timestamp: float
    text: str


class MeetingTranscript(BaseModel):
    meeting_id: str
    title: str
    occurred_at: datetime
    participants: list[Participant]
    utterances: list[Utterance]


class LoopEvent(BaseModel):
    id: str
    loop_id: str
    event_type: LoopEventType
    occurred_at: datetime
    channel: str | None = None
    detail: str = ""
    evidence_span: str | None = None


class Verdict(BaseModel):
    verdict: VerdictType
    confidence: float
    evidence_span: str
    new_owner_name: str | None = None
    new_owner_email: str | None = None
    new_commitment: str | None = None
    new_due_at: datetime | None = None


class Loop(BaseModel):
    id: str
    parent_id: str | None = None
    promise: str
    source_quote: str
    source_meeting_id: str | None = None
    owner_name: str
    owner_email: str
    counterparty_org: str
    due_at: datetime
    window_source: WindowSource
    closure_criterion: str
    stakes: Literal["low", "medium", "high"]
    status: LoopStatus = LoopStatus.OPEN
    touch_count: int = 0
    deferral_count: int = 0
    channels_tried: list[str] = Field(default_factory=list)
    created_at: datetime
    events: list[LoopEvent] = Field(default_factory=list)
