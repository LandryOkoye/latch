from pydantic import BaseModel

from latch_core.models import Loop


class WorklistItem(BaseModel):
    loop: Loop
    priority_total: float
    priority_breakdown: dict[str, float]


class LoopDetail(BaseModel):
    loop: Loop
    ancestors: list[Loop]
    children: list[Loop]
    draft: str
    priority_total: float
    priority_breakdown: dict[str, float]


class ReliabilityRow(BaseModel):
    counterparty_org: str
    loops_opened: int
    closed_on_time: int
    median_touches_to_closure: float
    deferral_rate: float
    escalation_rate: float
    unreliability_score: float


class PursueResult(BaseModel):
    result: str
    loop: Loop
