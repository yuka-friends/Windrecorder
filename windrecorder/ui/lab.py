import os

import streamlit as st
from PIL import Image
from streamlit_tags import st_tags

from windrecorder.config import config
from windrecorder.llm import request_llm_one_shot
from windrecorder.utils import get_text as _t


def render():
    settings_col, spacing_col, pic_col = st.columns([1, 0.5, 1.5])
    # ensures variables exist
    ai_extract_tag_wintitle_limit = config.ai_extract_tag_wintitle_limit
    enable_ai_day_poem = False
    ai_extract_tag_filter_words = config.ai_extract_tag_filter_words

    with settings_col:
        st.markdown(_t("lab_title"))

        st.markdown(_t("lab_title_image_semantic_index"))
        st.image(Image.open("__assets__\\header_image_embedding_index.png"))
        if config.img_embed_module_install:
            st.session_state.option_enable_img_embed_search = st.checkbox(
                _t("set_checkbox_enable_img_emb"),
                help=_t("set_text_enable_img_emb_help"),
                value=config.enable_img_embed_search,
            )
        else:
            st.info(_t("lab_tip_image_semantic_index_not_install"))
            st.session_state.option_enable_img_embed_search = False

        st.divider()

        st.markdown(_t("lab_title_llm_features"))
        st.image(Image.open("__assets__\\header_llm.png"))
        st.caption(_t("lab_tip_llm_api_endpoint"))
        with st.expander("🦜 " + _t("lab_text_config_llm_api")):
            ai_api_endpoint_selected = st.selectbox(
                _t("lab_selectbox_api_endpoint"),
                options=config.ai_api_endpoint_type,
                index=[
                    index
                    for index, value in enumerate(config.ai_api_endpoint_type)
                    if value == config.ai_api_endpoint_selected
                ][0],
                help=_t("lab_help_api_endpoint"),
                disabled=True,
            )
            open_ai_base_url = st.text_input("open ai base_url", value=config.open_ai_base_url)
            open_ai_api_key = st.text_input("open ai api key", type="password", value=config.open_ai_api_key)
            open_ai_modelname = st.text_input("open ai modelname", value=config.open_ai_modelname)
            if st.button(_t("lab_btn_test")):
                with st.spinner(_t("lab_text_testing")):
                    success, resopond = request_llm_one_shot(
                        user_content=_t("lab_prompt_test"),
                        api_key=open_ai_api_key,
                        base_url=open_ai_base_url,
                        model=open_ai_modelname,
                    )
                    if success:
                        st.success(_t("lab_text_test_res_success") + resopond, icon="✅")
                    else:
                        st.success(_t("lab_text_test_res_fail") + resopond, icon="❌")

        col1_llm_feature, col2_llm_feature = st.columns([1, 1.5])
        with col1_llm_feature:
            enable_ai_extract_tag = st.checkbox(
                _t("lab_checkbox_extract_tag"),
                value=config.enable_ai_extract_tag,
                help=_t("lab_help_extract_tag").format(ai_extract_tag_result_dir_ud=config.ai_extract_tag_result_dir_ud),
            )
            if enable_ai_extract_tag:
                enable_ai_day_poem = st.checkbox(
                    _t("lab_checkbox_day_poem"),
                    value=config.enable_ai_day_poem,
                    help=_t("lab_help_day_poem").format(ai_day_poem_result_dir_ud=config.ai_day_poem_result_dir_ud),
                )
        with col2_llm_feature:
            st.empty()
            if enable_ai_extract_tag:
                ai_extract_tag_wintitle_limit = st.number_input(
                    label=_t("lab_input_wintitle_num"), value=config.ai_extract_tag_wintitle_limit
                )
        if enable_ai_extract_tag:
            st.caption(_t("lab_help_tag_filter_words"))
            ai_extract_tag_filter_words = st_tags(
                label=_t("lab_text_tag_filter_words"), text=_t("rs_tag_input_tip"), value=config.ai_extract_tag_filter_words
            )
        st.text("")
        st.button(
            _t("lab_btn_open_LLM_search_and_summary"),
            on_click=lambda: os.startfile(os.path.join("extension", "LLM_search_and_summary", "LLM_search_and_summary.bat")),
        )

        st.divider()

        if st.button(
            "Save and Apply All Changes / " + _t("text_apply_changes")
            if config.lang != "en"
            else "Save and Apply All Changes",
            type="primary",
            key="SaveBtnLab",
        ):
            config.set_and_save_config("enable_img_embed_search", st.session_state.option_enable_img_embed_search)
            config.set_and_save_config("ai_api_endpoint_selected", ai_api_endpoint_selected)
            config.set_and_save_config("open_ai_base_url", open_ai_base_url)
            config.set_and_save_config("open_ai_api_key", open_ai_api_key)
            config.set_and_save_config("open_ai_modelname", open_ai_modelname)
            config.set_and_save_config("enable_ai_extract_tag", enable_ai_extract_tag)
            config.set_and_save_config("enable_ai_day_poem", enable_ai_day_poem)
            config.set_and_save_config("ai_extract_tag_wintitle_limit", ai_extract_tag_wintitle_limit)
            config.set_and_save_config("ai_extract_tag_filter_words", ai_extract_tag_filter_words)
            st.toast(_t("utils_toast_setting_saved"), icon="🦝")

    with spacing_col:
        st.empty()

    with pic_col:
        st.empty()
