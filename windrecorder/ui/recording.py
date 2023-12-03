import time

import streamlit as st
from PIL import Image

from windrecorder import utils
from windrecorder.config import config
from windrecorder.utils import get_text as _t


def render():
    st.markdown(_t("rs_md_title"))

    settings_col, spacing_col, pic_col = st.columns([1, 0.5, 1.5])
    with settings_col:
        st.info(_t("rs_text_need_to_restart_after_save_setting"))

        st.markdown(_t("rs_md_record_setting_title"))

        # 录制选项
        col1_record, col2_record = st.columns([1, 1])
        with col1_record:
            if "is_create_startup_shortcut" not in st.session_state:
                st.session_state.is_create_startup_shortcut = utils.is_file_already_in_startup("start_app.bat.lnk")
            st.session_state.is_create_startup_shortcut = st.checkbox(
                _t("rs_checkbox_start_record_when_startup"),
                value=st.session_state.is_create_startup_shortcut,
                on_change=utils.change_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut),
                help=_t("rs_checkbox_start_record_when_startup_help"),
            )

        with col2_record:
            st.markdown(_t("rs_md_only_support_main_monitor"), unsafe_allow_html=True)

        record_screen_enable_half_res_while_hidpi = st.checkbox(
            _t("rs_checkbox_enable_half_res_while_hidpi"),
            help=_t("rs_text_enable_half_res_while_hidpi"),
            value=config.record_screen_enable_half_res_while_hidpi,
        )

        screentime_not_change_to_pause_record = st.number_input(
            _t("rs_input_stop_recording_when_screen_freeze"),
            value=config.screentime_not_change_to_pause_record,
            min_value=0,
        )

        st.divider()

        # 自动化维护选项
        st.markdown(_t("set_md_auto_maintain"))
        ocr_strategy_option_dict = {
            _t("rs_text_ocr_manual_update"): 0,
            _t("rs_text_ocr_auto_update"): 1,
        }
        ocr_strategy_option = st.selectbox(
            _t("rs_selectbox_ocr_strategy"),
            (list(ocr_strategy_option_dict.keys())),
            index=config.OCR_index_strategy,
        )

        col1d, col2d, col3d = st.columns([1, 1, 1])
        with col1d:
            vid_store_day = st.number_input(
                _t("set_input_video_hold_days"),
                min_value=0,
                value=config.vid_store_day,
                help=_t("rs_input_vid_store_time_help"),
            )
        with col2d:
            vid_compress_day = st.number_input(
                _t("rs_input_vid_compress_time"),
                value=config.vid_compress_day,
                min_value=0,
                help=_t("rs_input_vid_compress_time_help"),
            )
        with col3d:
            video_compress_selectbox_dict = {"0.75": 0, "0.5": 1, "0.25": 2}
            video_compress_rate_selectbox = st.selectbox(
                _t("rs_selectbox_compress_ratio"),
                list(video_compress_selectbox_dict.keys()),
                index=video_compress_selectbox_dict[config.video_compress_rate],
                help=_t("rs_selectbox_compress_ratio_help"),
            )

        st.divider()

        if st.button("Save and Apple All Change / 保存并应用所有更改", type="primary", key="SaveBtnRecord"):
            config.set_and_save_config("screentime_not_change_to_pause_record", screentime_not_change_to_pause_record)
            config.set_and_save_config("record_screen_enable_half_res_while_hidpi", record_screen_enable_half_res_while_hidpi)
            config.set_and_save_config("OCR_index_strategy", ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("vid_store_day", vid_store_day)
            config.set_and_save_config("vid_compress_day", vid_compress_day)
            config.set_and_save_config("video_compress_rate", video_compress_rate_selectbox)
            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(2)
            st.experimental_rerun()

    with spacing_col:
        st.empty()

    with pic_col:
        howitwork_img = Image.open("__assets__\\workflow-" + config.lang + ".png")
        st.image(howitwork_img)
