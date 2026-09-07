import streamlit as st

from latch_core import ledger
from latch_core.models import Loop

from latch_reviewer.components import status_pill


def render(loop: Loop) -> None:
    """Render the deferral chain (root ancestor down through children) for a
    loop, with the current loop marked. Renders nothing if the loop is a
    standalone leaf with no history."""
    chain = [loop]
    current = loop
    while current.parent_id:
        parent = ledger.get_loop(current.parent_id)
        if parent is None:
            break
        chain.insert(0, parent)
        current = parent

    children = ledger.fetch_children(loop.id)

    if len(chain) == 1 and not children:
        return

    st.caption("Deferral chain")
    for i, node in enumerate(chain):
        indent = "&nbsp;" * (i * 4)
        marker = "➤" if node.id == loop.id else "・"
        st.markdown(f"{indent}{marker} {node.promise} — {status_pill.render(node.status)}", unsafe_allow_html=True)
    for child in children:
        indent = "&nbsp;" * (len(chain) * 4)
        st.markdown(f"{indent}・{child.promise} — {status_pill.render(child.status)}", unsafe_allow_html=True)
