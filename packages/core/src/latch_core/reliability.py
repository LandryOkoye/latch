from statistics import median

from latch_core.models import Loop, LoopStatus


def compute_reliability(loops: list[Loop]) -> dict[str, dict]:
    """Per-counterparty reliability stats, keyed by counterparty_org: loops
    opened, closed on time (verified, not just claimed), median touches to
    closure, deferral rate, escalation rate, and a single 0-1 unreliability
    score priority.py folds into the worklist ranking."""
    by_org: dict[str, list[Loop]] = {}
    for loop in loops:
        by_org.setdefault(loop.counterparty_org, []).append(loop)

    stats: dict[str, dict] = {}
    for org, org_loops in by_org.items():
        opened = len(org_loops)
        closed_verified = [l for l in org_loops if l.status == LoopStatus.CLOSED_VERIFIED]
        touches = [l.touch_count for l in closed_verified] or [0]
        deferred = sum(1 for l in org_loops if l.deferral_count > 0)
        escalated = sum(1 for l in org_loops if l.status == LoopStatus.ESCALATED_TO_HUMAN)

        deferral_rate = deferred / opened if opened else 0.0
        escalation_rate = escalated / opened if opened else 0.0
        unreliability_score = min(1.0, 0.5 * deferral_rate + 0.5 * escalation_rate)

        stats[org] = {
            "loops_opened": opened,
            "closed_on_time": len(closed_verified),
            "median_touches_to_closure": median(touches),
            "deferral_rate": round(deferral_rate, 2),
            "escalation_rate": round(escalation_rate, 2),
            "unreliability_score": round(unreliability_score, 2),
        }
    return stats
