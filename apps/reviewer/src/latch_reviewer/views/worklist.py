import pandas as pd
import streamlit as st

from latch_core import ledger, priority, reliability
from latch_core.models import LoopStatus

from latch_reviewer.components import status_pill
from latch_reviewer.views import loop_detail

_TERMINAL_STATUSES = {LoopStatus.CLOSED_VERIFIED, LoopStatus.ABANDONED}


def render() -> None:
    st.subheader("Worklist")
    st.caption("Overdue commitments, ranked by what actually needs attention first — not just by age.")

    all_loops = ledger.list_loops()
    reliability_stats = reliability.compute_reliability(all_loops)
    active_loops = [loop for loop in all_loops if loop.status not in _TERMINAL_STATUSES]

    if not active_loops:
        st.info("Nothing overdue right now.")
        return

    scored = []
    for loop in active_loops:
        unreliability = reliability_stats.get(loop.counterparty_org, {}).get("unreliability_score", 0.0)
        score = priority.priority_score(loop, unreliability)
        scored.append((score["total"], score["breakdown"], loop))
    scored.sort(key=lambda row: row[0], reverse=True)

    for total, breakdown, loop in scored:
        detail = ledger.get_loop(loop.id)
        title = f"{detail.owner_name} ({detail.counterparty_org}) — {detail.promise}"
        subtitle = f"Due {detail.due_at:%b %d} · {detail.stakes} stakes · priority {total}"

        with st.expander(f"{title}  \n{subtitle}"):
            st.markdown(status_pill.render(detail.status), unsafe_allow_html=True)

            st.markdown("**Why this priority**")
            breakdown_df = pd.DataFrame(
                [{"Component": key.replace("_", " ").title(), "Points": value} for key, value in breakdown.items()]
            )
            st.dataframe(
                breakdown_df,
                hide_index=True,
                width="stretch",
                column_config={"Points": st.column_config.NumberColumn(format="%.1f")},
            )

            st.divider()
            loop_detail.render(detail)
