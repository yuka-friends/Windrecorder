import os
import time

import streamlit as st
from PIL import Image

import windrecorder.record as record
from windrecorder.config import config
from windrecorder.utils import find_key_position_in_dict
from windrecorder.utils import get_text as _t


def render():
    st.markdown(_t("rs_md_title"))

    settings_col, spacing_col, pic_col = st.columns([1, 0.5, 1.5])
    with settings_col:
        st.info(_t("rs_text_need_to_restart_after_save_setting"))

        # 手动检查录屏服务有无进行中

        # 管理刷新服务的按钮状态：手动管理状态，cover fix streamlit只能读按钮是否被按下的问题（一旦有其他按钮按下，其他按钮就会回弹导致持续的逻辑重置、重新加载）
        def update_record_service_btn_clicked():
            st.session_state.update_btn_dis_record = True

        if "update_btn_refresh_press" not in st.session_state:
            st.session_state.update_btn_refresh_press = False

        def update_record_btn_state():
            if st.session_state.update_btn_refresh_press:
                st.session_state.update_btn_refresh_press = False
            else:
                st.session_state.update_btn_refresh_press = True
            st.session_state.update_btn_dis_record = False

        # 这个按钮利用 streamlit 的特性触发刷新，并不是无用的变量
        btn_refresh = st.button(_t("rs_btn_check_record_stat"), on_click=update_record_btn_state)  # noqa: F841

        if st.session_state.update_btn_refresh_press:
            if record.is_recording():
                st.success(_t("rs_text_recording_screen_now"), icon="🦚")

            else:
                st.error(_t("rs_text_not_recording_screen"), icon="🦫")
                start_record_btn = st.button(
                    _t("rs_btn_start_record"),
                    type="primary",
                    disabled=st.session_state.get("update_btn_dis_record", False),
                    on_click=update_record_service_btn_clicked,
                )
                if start_record_btn:
                    os.startfile("start_record.bat", "open")
                    st.toast(_t("rs_text_starting_record"))
                    st.session_state.update_btn_refresh_press = False

        # st.warning("录制服务已启用。当前暂停录制屏幕。",icon="🦫")
        st.divider()
        st.markdown(_t("rs_md_record_setting_title"))

        # 录制选项
        col1_record, col2_record = st.columns([1, 1])
        with col1_record:
            if "is_create_startup_shortcut" not in st.session_state:
                st.session_state.is_create_startup_shortcut = record.is_file_already_in_startup("start_record.bat.lnk")
            st.session_state.is_create_startup_shortcut = st.checkbox(
                _t("rs_checkbox_start_record_when_startup"),
                value=record.is_file_already_in_startup("start_record.bat.lnk"),
                on_change=record.create_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut),
                help=_t("rs_checkbox_start_record_when_startup_help"),
            )

        with col2_record:
            st.markdown(_t("rs_md_only_support_main_monitor"), unsafe_allow_html=True)

        record_screen_enable_half_res_while_hidpi = st.checkbox(
            _t("rs_checkbox_enable_half_res_while_hidpi"),
            help=_t("rs_text_enable_half_res_while_hidpi"),
            value=config.record_screen_enable_half_res_while_hidpi,
        )

        firefox_optimization = st.checkbox(
            _t("rs_checkbox_optimization_firefox"),
            help=_t("rs_text_optimization_firefox_help"),
            value=config.used_firefox,
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
            video_compress_selectbox_dict = {"1": 0, "0.75": 1, "0.5": 2, "0.25": 3}
            video_compress_rate_selectbox = st.selectbox(
                _t("rs_selectbox_compress_ratio"),
                list(video_compress_selectbox_dict.keys()),
                index=video_compress_selectbox_dict[config.video_compress_rate],
                help=_t("rs_selectbox_compress_ratio_help"),
            )

        col1_encode, col2_encode, col3_encode = st.columns([1, 1, 1])
        with col1_encode:
            video_compress_encoder = st.selectbox(
                _t("rs_text_compress_encoder"),
                list(config.compress_preset.keys()),
                index=find_key_position_in_dict(config.compress_preset, config.compress_encoder) - 1,
            )
        with col2_encode:
            video_compress_accelerator = st.selectbox(
                _t("rs_text_compress_accelerator"),
                list(config.compress_preset[video_compress_encoder].keys()),
                index=find_key_position_in_dict(config.compress_preset[video_compress_encoder], config.compress_accelerator)
                - 1,
            )
        with col3_encode:
            video_compress_crf = st.number_input(
                _t("rs_text_compress_CRF"),
                value=config.compress_quality,
                min_value=0,
                max_value=50,
                help=_t("rs_text_compress_CRF_help"),
            )

        if st.button(_t("rs_btn_encode_benchmark")):
            with st.spinner(_t("rs_text_encode_benchmark_loading")):
                result_df = record.encode_preset_benchmark_test(
                    scale_factor=video_compress_rate_selectbox, crf=video_compress_crf
                )
                st.dataframe(
                    result_df,
                    column_config={
                        "encoder": st.column_config.TextColumn(_t("rs_text_compress_encoder")),
                        "accelerator": st.column_config.TextColumn(_t("rs_text_compress_accelerator")),
                        "support": st.column_config.CheckboxColumn(_t("rs_text_support"), default=False),
                        "compress_ratio": st.column_config.TextColumn(
                            _t("rs_text_compress_ratio"), help=_t("rs_text_compress_ratio_help")
                        ),
                        "compress_time": st.column_config.TextColumn(_t("rs_text_compress_time")),
                    },
                )

        st.divider()

        if st.button("Save and Apple All Change / 保存并应用所有更改", type="primary", key="SaveBtnRecord"):
            config.set_and_save_config("screentime_not_change_to_pause_record", screentime_not_change_to_pause_record)
            config.set_and_save_config("record_screen_enable_half_res_while_hidpi", record_screen_enable_half_res_while_hidpi)
            config.set_and_save_config("OCR_index_strategy", ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("used_firefox", firefox_optimization)

            config.set_and_save_config("vid_store_day", vid_store_day)
            config.set_and_save_config("vid_compress_day", vid_compress_day)
            config.set_and_save_config("video_compress_rate", video_compress_rate_selectbox)

            config.set_and_save_config("compress_encoder", video_compress_encoder)
            config.set_and_save_config("compress_accelerator", video_compress_accelerator)
            config.set_and_save_config("compress_quality", video_compress_crf)

            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(2)
            st.experimental_rerun()

    with spacing_col:
        st.empty()

    with pic_col:
        howitwork_img = Image.open("__assets__\\workflow-" + config.lang + ".png")
        st.image(howitwork_img)
