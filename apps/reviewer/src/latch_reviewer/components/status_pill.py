from latch_core.models import LoopStatus

_COLORS = {
    LoopStatus.OPEN: ("#3B4252", "#E5E9F0"),
    LoopStatus.AWAITING_REPLY: ("#5E81AC", "#FFFFFF"),
    LoopStatus.CLOSED_VERIFIED: ("#4C7A50", "#FFFFFF"),
    LoopStatus.CLOSED_CLAIMED: ("#B58900", "#FFFFFF"),
    LoopStatus.ESCALATED_TO_HUMAN: ("#B23A48", "#FFFFFF"),
    LoopStatus.ABANDONED: ("#6B6B6B", "#FFFFFF"),
}

_LABELS = {
    LoopStatus.OPEN: "Open",
    LoopStatus.AWAITING_REPLY: "Awaiting reply",
    LoopStatus.CLOSED_VERIFIED: "Closed · verified",
    LoopStatus.CLOSED_CLAIMED: "Closed · claimed",
    LoopStatus.ESCALATED_TO_HUMAN: "Escalated",
    LoopStatus.ABANDONED: "Abandoned",
}


def render(status: LoopStatus) -> str:
    """Return an inline-HTML status pill for use with st.markdown(unsafe_allow_html=True)."""
    bg, fg = _COLORS.get(status, ("#6B6B6B", "#FFFFFF"))
    label = _LABELS.get(status, status.value)
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 10px;border-radius:999px;'
        f'font-size:0.78rem;font-weight:600;white-space:nowrap;">{label}</span>'
    )
