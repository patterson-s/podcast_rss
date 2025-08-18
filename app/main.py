# app/main.py
from __future__ import annotations
import json
import streamlit as st

from app.resolvers.orchestrator import find_feed   # <-- absolute import

st.set_page_config(page_title="Get RSS Feed (Open Source)", page_icon="📻")

st.title("Get RSS Feed (Open Source)")
st.caption("Paste a podcast page URL or type a show title. Returns the canonical RSS feed if it exists.")

with st.form("resolver"):
    user_input = st.text_input(
        "Apple/Spotify/Publisher URL — or a show title",
        placeholder="https://podcasts.apple.com/gb/podcast/ukraine-the-latest/id1612424182",
    )
    submitted = st.form_submit_button("Find RSS Feed")

if submitted:
    res = find_feed(user_input)
    if res.status == "found":
        st.success("Feed found")
        st.write("**RSS feed URL:**")
        st.code(res.feed_url, language=None)
        st.link_button("Open feed", res.feed_url)
    elif res.status == "exclusive_or_unsupported":
        st.warning(res.notes or "Exclusive or unsupported")
    elif res.status == "not_found":
        st.error(res.notes or "No feed discovered")
    else:
        st.error(res.notes or "Error")

    st.divider()
    st.subheader("Debug JSON")
    st.code(json.dumps(res.__dict__, ensure_ascii=False, indent=2), language="json")

st.markdown(
    """
    ---  
    **Notes**  
    - Apple resolution uses the public Lookup/Search APIs.  
    - Spotify resolution uses public oEmbed → title match via Apple.  
    - Generic pages use HTML autodiscovery with validation.  
    """
)
