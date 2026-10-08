from fastapi import APIRouter, HTTPException

from latch_core import ledger, priority, reliability
from latch_core.models import Loop, LoopStatus

from latch_agent.agents.pursuer import draft_followup, pursue

from latch_api.schemas import LoopDetail, PursueResult, WorklistItem

router = APIRouter(prefix="/api", tags=["loops"])

_TERMINAL_STATUSES = {LoopStatus.CLOSED_VERIFIED, LoopStatus.ABANDONED}


def _score(loop, reliability_stats: dict) -> dict:
    unreliability = reliability_stats.get(loop.counterparty_org, {}).get("unreliability_score", 0.0)
    return priority.priority_score(loop, unreliability)


@router.get("/worklist", response_model=list[WorklistItem])
def get_worklist() -> list[WorklistItem]:
    all_loops = ledger.list_loops()
    reliability_stats = reliability.compute_reliability(all_loops)
    # A deferred loop is superseded by its newest child, which carries the live
    # commitment; ranking the parent too would double-count it on its stale due date.
    superseded = {loop.parent_id for loop in all_loops if loop.parent_id}
    active = [loop for loop in all_loops if loop.status not in _TERMINAL_STATUSES and loop.id not in superseded]

    items = []
    for loop in active:
        score = _score(loop, reliability_stats)
        items.append(WorklistItem(loop=loop, priority_total=score["total"], priority_breakdown=score["breakdown"]))
    items.sort(key=lambda item: item.priority_total, reverse=True)
    return items


@router.get("/loops", response_model=list[Loop])
def get_loops() -> list[Loop]:
    return ledger.list_loops()


@router.get("/loops/{loop_id}", response_model=LoopDetail)
def get_loop_detail(loop_id: str) -> LoopDetail:
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="loop not found")

    ancestors = []
    current = loop
    while current.parent_id:
        parent = ledger.get_loop(current.parent_id)
        if parent is None:
            break
        ancestors.insert(0, parent)
        current = parent
    children = ledger.fetch_children(loop.id)

    reliability_stats = reliability.compute_reliability(ledger.list_loops())
    score = _score(loop, reliability_stats)
    draft = draft_followup(loop_id)

    return LoopDetail(
        loop=loop,
        ancestors=ancestors,
        children=children,
        draft=draft,
        priority_total=score["total"],
        priority_breakdown=score["breakdown"],
    )


@router.post("/loops/{loop_id}/pursue", response_model=PursueResult)
def post_pursue(loop_id: str) -> PursueResult:
    loop = ledger.get_loop(loop_id)
    if loop is None:
        raise HTTPException(status_code=404, detail="loop not found")
    result = pursue(loop_id)
    updated = ledger.get_loop(loop_id)
    return PursueResult(result=result, loop=updated)
