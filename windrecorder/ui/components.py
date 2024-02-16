import datetime
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
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


def record_search_history(search_content, search_type, search_datetime=datetime.datetime.now()):
    """记录搜索历史"""
    try:
        if config.enable_search_history_record:
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
