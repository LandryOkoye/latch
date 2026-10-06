from fastapi import APIRouter

from latch_core import ledger, reliability

from latch_api.schemas import ReliabilityRow

router = APIRouter(prefix="/api", tags=["reliability"])


@router.get("/reliability", response_model=list[ReliabilityRow])
def get_reliability() -> list[ReliabilityRow]:
    stats = reliability.compute_reliability(ledger.list_loops())
    return [
        ReliabilityRow(counterparty_org=org, **s)
        for org, s in sorted(stats.items(), key=lambda kv: kv[1]["unreliability_score"])
    ]
