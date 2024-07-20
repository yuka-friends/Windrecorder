import streamlit as st

from windrecorder.config import config
from windrecorder.utils import get_text as _t

def render():
    settings_col, spacing_col, pic_col = st.columns([1, 0.5, 1.5])
    
    with settings_col:
        st.markdown("### ⚗️ Lab Features")

        st.markdown("### Image semantic index")
        if config.img_embed_module_install:
            st.session_state.option_enable_img_embed_search = st.checkbox(
                _t("set_checkbox_enable_img_emb"),
                help=_t("set_text_enable_img_emb_help"),
                value=config.enable_img_embed_search,
            )
        else:
            st.info("Image semantic index is not installed. You can install it under XXX")
            st.session_state.option_enable_img_embed_search = False
        
        st.divider()
        
        st.markdown("#### LLM API")
        st.selectbox("API endpoint", options=["OpenAI compatible"])
        st.text_input("open_ai_base_url")
        st.text_input("open_ai_api_key", type="password")
        st.text_input("open_ai_modelname")
        st.button("Test API connection")

        st.divider()

        st.markdown("#### LLM Features")
        st.checkbox("在电脑空闲时，自动总结每天活动")

        st.divider()

        if st.button(
            "Save and Apply All Changes / " + _t("text_apply_changes")
            if config.lang != "en"
            else "Save and Apply All Changes",
            type="primary",
            key="SaveBtnLab",
        ):
            config.set_and_save_config("enable_img_embed_search", st.session_state.option_enable_img_embed_search)
    
    with spacing_col:
        st.empty()
    
    with pic_col:
        st.empty()


