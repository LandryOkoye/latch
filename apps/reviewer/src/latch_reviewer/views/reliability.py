import pandas as pd
import streamlit as st

from latch_core import ledger, reliability


def render() -> None:
    st.subheader("Reliability Board")
    st.caption("Which counterparties actually hold their dates — built automatically from every loop tracked so far.")

    all_loops = ledger.list_loops()
    stats = reliability.compute_reliability(all_loops)

    if not stats:
        st.info("No data yet.")
        return

    rows = []
    for org, s in sorted(stats.items(), key=lambda kv: kv[1]["unreliability_score"]):
        rows.append(
            {
                "Counterparty": org,
                "Loops opened": s["loops_opened"],
                "Closed on time": s["closed_on_time"],
                "Median touches to closure": s["median_touches_to_closure"] if s["closed_on_time"] else None,
                "Deferral rate": round(s["deferral_rate"] * 100),
                "Escalation rate": round(s["escalation_rate"] * 100),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "Deferral rate": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
            "Escalation rate": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
        },
    )
