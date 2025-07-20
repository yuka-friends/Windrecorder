import _natural_search
import streamlit as st

st.set_page_config(page_title="Windrecord - LLM search and summary - AI-based natural language search", page_icon="🦝")


def init_st_state():
    pass


def main_webui():
    _natural_search.render_natural_search_page()


init_st_state()
main_webui()
