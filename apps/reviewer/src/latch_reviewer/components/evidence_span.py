import html


def render(reply_text: str | None, evidence_span: str | None) -> str:
    """Return the reply text as inline HTML with evidence_span highlighted, for
    use with st.markdown(unsafe_allow_html=True). Falls back gracefully if
    either piece is missing."""
    if not reply_text:
        return ""
    escaped = html.escape(reply_text)
    if not evidence_span:
        return f'<div style="white-space:pre-wrap;">{escaped}</div>'

    escaped_span = html.escape(evidence_span)
    if escaped_span not in escaped:
        return f'<div style="white-space:pre-wrap;">{escaped}</div>'

    highlighted = escaped.replace(
        escaped_span,
        f'<mark style="background:#F5D67B;color:#1A1A1A;border-radius:3px;padding:0 2px;">{escaped_span}</mark>',
        1,
    )
    return f'<div style="white-space:pre-wrap;">{highlighted}</div>'
