import streamlit as st

from latch_core.models import Loop

from latch_agent.agents.pursuer import draft_followup, pursue

from latch_reviewer.components import evidence_span, loop_tree

_EVENT_ICONS = {
    "created": "🆕",
    "touched": "✉️",
    "reply_received": "↩️",
    "deferred": "⏳",
    "transferred": "🔀",
    "disputed": "⚠️",
    "escalated": "🚩",
    "closed_verified": "✅",
    "closed_claimed": "🟡",
    "abandoned": "🗑️",
}


def render(loop: Loop) -> None:
    st.markdown(f'**Source quote:** "{loop.source_quote}"')
    st.caption(f"Closure criterion: {loop.closure_criterion}")

    loop_tree.render(loop)

    st.markdown("**Timeline**")
    if not loop.events:
        st.caption("No events yet.")
    for event in loop.events:
        icon = _EVENT_ICONS.get(event.event_type.value, "•")
        line = f"{icon} **{event.occurred_at:%b %d, %H:%M}** — {event.event_type.value.replace('_', ' ')}"
        if event.channel:
            line += f" via {event.channel}"
        if event.detail:
            line += f": {event.detail}"
        st.markdown(line)
        if event.reply_text and event.evidence_span:
            # a plain toggle, not st.expander: this view is itself nested inside
            # the worklist's per-loop expander, and Streamlit expanders can't nest.
            if st.toggle("Show reply with evidence highlighted", key=f"evidence_{event.id}"):
                st.markdown(evidence_span.render(event.reply_text, event.evidence_span), unsafe_allow_html=True)

    st.divider()
    st.markdown("**Drafted intervention**")
    draft = draft_followup(loop.id)
    st.text_area("Message", value=draft, height=160, key=f"draft_{loop.id}", label_visibility="collapsed")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Approve & Send", key=f"send_{loop.id}", type="primary", width="stretch"):
            with st.spinner("Pursuer agent is deciding..."):
                result = pursue(loop.id)
            st.success(result)
            st.rerun()
    with col2:
        st.button(
            "Edit above, then Approve & Send", key=f"edit_{loop.id}", disabled=True, width="stretch",
        )
