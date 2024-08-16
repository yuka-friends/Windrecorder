import streamlit as st

from windrecorder.config import config
from windrecorder.llm import request_llm_one_shot
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

        st.markdown("#### LLM features")
        with st.expander("Config LLM API"):
            ai_api_endpoint_selected = st.selectbox(
                "API endpoint",
                options=config.ai_api_endpoint_type,
                index=[
                    index
                    for index, value in enumerate(config.ai_api_endpoint_type)
                    if value == config.ai_api_endpoint_selected
                ][0],
            )
            open_ai_base_url = st.text_input("open ai base_url", value=config.open_ai_base_url)
            open_ai_api_key = st.text_input("open ai api_key", type="password", value=config.open_ai_api_key)
            open_ai_modelname = st.text_input("open ai modelname", value=config.open_ai_modelname)
            if st.button("Test API connection"):
                with st.spinner("communicating..."):
                    success, resopond = request_llm_one_shot(
                        user_content="hello! i am a little raccoon.",
                        api_key=open_ai_api_key,
                        base_url=open_ai_base_url,
                        model=open_ai_modelname,
                    )
                    if success:
                        st.success("测试成功：" + resopond, icon="✅")
                    else:
                        st.success("测试失败：" + resopond, icon="❌")

        enable_ai_extract_tag = st.checkbox(
            "生成每日活动标签",
            value=config.enable_ai_extract_tag,
            help=f"使用AI总结每日活动的标签，只有屏幕时间内的标题内容会被发送到LLM。通过删除 {config.ai_extract_tag_result_dir_ud} 中的json内数据，可以重新生成。",
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
            st.toast(_t("utils_toast_setting_saved"), icon="🦝")

    with spacing_col:
        st.empty()

    with pic_col:
        st.empty()
