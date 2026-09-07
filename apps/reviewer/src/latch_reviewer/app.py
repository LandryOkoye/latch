import streamlit as st

from latch_reviewer.views import reliability, worklist

st.set_page_config(page_title="Latch", page_icon="🔗", layout="wide")

st.title("🔗 Latch")
st.caption('An agent that owns the space between "I\'ll get back to you" and whether anyone ever did.')

tab_worklist, tab_reliability = st.tabs(["Worklist", "Reliability Board"])

with tab_worklist:
    worklist.render()

with tab_reliability:
    reliability.render()
