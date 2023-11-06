import streamlit as st

import ui.oneday
import ui.recording
import ui.search
import ui.setting
import ui.state
import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.dbManager import DBManager
from windrecorder.utils import get_text as _t

update_button_key = "update_button"

st.set_page_config(page_title="Windrecord - webui", page_icon="🦝", layout="wide")

# 从GitHub检查更新、添加提醒 - 初始化状态
if "update_info" not in st.session_state:
    st.session_state["update_info"] = _t("set_update_checking")
if "update_need" not in st.session_state:
    st.session_state["update_need"] = False
if "update_badge_emoji" not in st.session_state:
    st.session_state["update_badge_emoji"] = ""


# footer状态信息
def web_footer_state():
    # 懒加载，只在刷新时第一次获取
    if "footer_first_record_time_str" not in st.session_state:
        st.session_state["footer_first_record_time_str"] = utils.seconds_to_date_goodlook_formart(
            DBManager().db_first_earliest_record_time()
        )

    if "footer_latest_record_time_str" not in st.session_state:
        st.session_state["footer_latest_record_time_str"] = utils.seconds_to_date_goodlook_formart(
            DBManager().db_latest_record_time()
        )

    if "footer_latest_db_records" not in st.session_state:
        st.session_state["footer_latest_db_records"] = DBManager().db_num_records()

    if "footer_videos_file_size" not in st.session_state:
        st.session_state["footer_videos_file_size"] = round(
            file_utils.get_dir_size(config.record_videos_dir) / (1024 * 1024 * 1024), 3
        )

    if "footer_videos_files_count" not in st.session_state:
        (
            st.session_state["footer_videos_files_count"],
            _,
        ) = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir)

    # webUI draw
    st.divider()
    col1, col2 = st.columns([1, 0.3])
    with col1:
        st.markdown(
            _t("footer_info").format(
                first_record_time_str=st.session_state.footer_first_record_time_str,
                latest_record_time_str=st.session_state.footer_latest_record_time_str,
                latest_db_records=st.session_state.footer_latest_db_records,
                videos_file_size=st.session_state.footer_videos_file_size,
                videos_files_count=st.session_state.footer_videos_files_count,
            )
        )
    with col2:
        st.markdown(
            "<h2 align='right' style='color:rgba(0,0,0,.3)'> Windrecorder 🦝</h2>",
            unsafe_allow_html=True,
        )


# 主界面_________________________________________________________
st.markdown(_t("main_title"))

oneday_tab, search_tab, state_tab, recording_tab, setting_tab = st.tabs(
    [
        _t("tab_name_oneday"),
        _t("tab_name_search"),
        _t("tab_name_stat"),
        _t("tab_name_recording"),
        _t("tab_name_setting") + st.session_state.update_badge_emoji,
    ]
)

with oneday_tab:
    ui.oneday.render()

with search_tab:
    ui.search.render()

with state_tab:
    ui.state.render()

with recording_tab:
    ui.recording.render()

with setting_tab:
    ui.setting.render()

web_footer_state()
