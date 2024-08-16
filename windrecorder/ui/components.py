import datetime
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from windrecorder import file_utils, flag_mark_note, record_wintitle
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.llm import component_day_tags
from windrecorder.logger import get_logger
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)


# 检测并渲染onboarding提示
def web_onboarding():
    # 状态懒加载
    if "is_onboarding" not in st.session_state:
        st.session_state["is_onboarding"] = db_manager.check_is_onboarding()

    if st.session_state.is_onboarding:
        # 数据库不存在，展示 Onboarding 提示
        st.success(_t("text_welcome_to_windrecorder"), icon="😺")
        intro_markdown = Path(f"{config.config_src_dir}\\onboarding_{config.lang}.md").read_text(encoding="utf-8")
        st.markdown(intro_markdown)
        st.divider()


# 规范化的打表渲染组件
def video_dataframe(df, heightIn=800):
    # ~~is_videofile_exist~~ videofile 渲染为可选框
    # ocr_text 更大的展示空间
    # thumbnail 渲染为图像
    st.dataframe(
        df,
        column_config={
            "videofile": st.column_config.CheckboxColumn(
                "videofile",
                default=False,
            ),
            "ocr_text": st.column_config.TextColumn("ocr_text", width="medium"),
            "win_title": st.column_config.TextColumn("title", width="medium"),
            "thumbnail": st.column_config.ImageColumn(
                "thumbnail",
            ),
        },
        height=heightIn,
    )


def record_search_history(search_content, search_type, search_datetime=None):
    """记录搜索历史"""
    skip_words = [""]
    if search_content in skip_words:
        return
    try:
        if config.enable_search_history_record:
            if search_datetime is None:
                search_datetime = datetime.datetime.now()

            CSV_TEMPLATE_HISTORY = pd.DataFrame(columns=["search_content", "search_type", "search_datetime"])
            if not os.path.exists(config.search_history_note_filepath):
                file_utils.ensure_dir(config.userdata_dir)
                file_utils.save_dataframe_to_path(CSV_TEMPLATE_HISTORY, file_path=config.search_history_note_filepath)

            df = file_utils.read_dataframe_from_path(file_path=config.search_history_note_filepath)

            new_data = {
                "search_content": search_content,
                "search_type": search_type,
                "search_datetime": datetime.datetime.strftime(search_datetime, "%Y-%m-%d %H:%M:%S"),
            }
            df.loc[len(df)] = new_data
            file_utils.save_dataframe_to_path(df, file_path=config.search_history_note_filepath)
    except Exception as e:
        logger.error(e)


# 一日之时工具栏
def oneday_side_toolbar():
    lefttab_wintitle, lefttab_flagnote = st.tabs([_t("oneday_ls_title_wintitle"), _t("oneday_ls_title_flag_note")])
    with lefttab_wintitle:
        if config.enable_ai_extract_tag:
            component_day_tags(st.session_state.day_date_input)
        record_wintitle.component_wintitle_stat(st.session_state.day_date_input)
    with lefttab_flagnote:
        flag_mark_note.component_flag_mark()


# 读取嵌入模型缓存
def load_emb_model_cache():
    if config.img_embed_module_install:
        try:
            from windrecorder import img_embed_manager

            try:
                if "emb_model_text" not in st.session_state or "emb_model_image" not in st.session_state:
                    with st.spinner(_t("gs_text_loading_embed_model")):
                        (
                            st.session_state["emb_model_text"],
                            st.session_state["emb_model_image"],
                            st.session_state["emb_processor_text"],
                            st.session_state["emb_processor_image"],
                        ) = img_embed_manager.get_model_and_processor()
            except ModuleNotFoundError:
                config.set_and_save_config("img_embed_module_install", False)
        except ModuleNotFoundError:
            config.set_and_save_config("img_embed_module_install", False)


# 显示 deep linking
def render_deep_linking(url):
    if isinstance(url, str):
        if "http" in url.lower():
            st.markdown(f"[{url}]({url})")
        else:
            st.markdown(f"{url}")
