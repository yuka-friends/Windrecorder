import hashlib

import streamlit as st

import windrecorder.ui.components
import windrecorder.ui.lab
import windrecorder.ui.oneday
import windrecorder.ui.recording
import windrecorder.ui.search
import windrecorder.ui.setting
import windrecorder.ui.state
from windrecorder import state
from windrecorder.config import config
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
    if "footer_state_dict" not in st.session_state:
        st.session_state["footer_state_dict"] = state.make_webui_footer_state_data_cache(ask_from="webui")

    # webUI draw
    st.divider()
    col1, col2 = st.columns([1, 0.3])
    with col1:
        st.markdown(
            _t("footer_info").format(
                first_record_time_str=st.session_state.footer_state_dict["first_record_time_str"],
                latest_record_time_str=st.session_state.footer_state_dict["latest_record_time_str"],
                latest_db_records=st.session_state.footer_state_dict["latest_db_records_num"],
                videos_file_size=st.session_state.footer_state_dict["videos_file_size"],
                videos_files_count=st.session_state.footer_state_dict["videos_files_count"],
            ),
            help=_t("footer_info_help"),
        )
    with col2:
        st.markdown(
            "<h2 align='right' style='color:rgba(0,0,0,.3)'> Windrecorder 🦝</h2>",
            unsafe_allow_html=True,
        )


# 主界面_________________________________________________________
def main_webui():
    st.markdown(_t("main_title"))

    oneday_tab, search_tab, state_tab, lab_tab, recording_tab, setting_tab = st.tabs(
        [
            _t("tab_name_oneday"),
            _t("tab_name_search"),
            _t("tab_name_stat"),
            _t("tab_name_lab"),
            _t("tab_name_recording"),
            _t("tab_name_setting") + st.session_state.update_badge_emoji,
        ]
    )

    with oneday_tab:
        windrecorder.ui.oneday.render()

    with search_tab:
        windrecorder.ui.search.render()

    with state_tab:
        windrecorder.ui.state.render()

    with lab_tab:
        windrecorder.ui.lab.render()

    with recording_tab:
        windrecorder.ui.recording.render()

    with setting_tab:
        windrecorder.ui.setting.render()

    web_footer_state()

    # 尝试预加载嵌入模型
    if config.img_embed_module_install and config.enable_synonyms_recommend:
        windrecorder.ui.components.load_emb_model_cache()


# 检查 webui 是否启用密码保护
if "webui_password_accessed" not in st.session_state:
    st.session_state["webui_password_accessed"] = False

if config.webui_access_password_md5 and st.session_state.webui_password_accessed is False:
    col_pwd1, col_pwd2 = st.columns([1, 2])
    with col_pwd1:
        password = st.text_input("🔒 Password:", type="password", help=_t("set_pwd_forget_help"))
    with col_pwd2:
        st.empty()
    if hashlib.md5(password.encode("utf-8")).hexdigest() == config.webui_access_password_md5:
        st.session_state.webui_password_accessed = True

if not config.webui_access_password_md5 or st.session_state.webui_password_accessed is True:
    main_webui()
