import time

import streamlit as st
from PIL import Image
from streamlit_tags import st_tags

from windrecorder import record, utils
from windrecorder.config import (
    CONFIG_RECORD_PRESET,
    CONFIG_VIDEO_COMPRESS_PRESET,
    config,
)
from windrecorder.utils import find_key_position_in_dict
from windrecorder.utils import get_text as _t


def render():
    # 初始化懒状态
    if "display_count" not in st.session_state:
        st.session_state["display_count"] = utils.get_display_count()
    if "display_info" not in st.session_state:
        st.session_state["display_info"] = utils.get_display_info()
    if "display_info_formatted" not in st.session_state:
        st.session_state["display_info_formatted"] = utils.get_display_info_formatted()
    record_encoder = config.record_encoder
    record_bitrate = config.record_bitrate
    video_compress_encoder = config.compress_accelerator
    video_compress_accelerator = config.compress_accelerator
    video_compress_crf = config.compress_quality
    screenshot_interval_second = config.screenshot_interval_second
    record_screenshot_method_capture_foreground_window_only = config.record_screenshot_method_capture_foreground_window_only
    is_record_system_sound = config.is_record_system_sound
    convert_screenshots_to_vid_while_only_when_idle_or_plugged_in = (
        config.convert_screenshots_to_vid_while_only_when_idle_or_plugged_in
    )

    st.markdown(_t("rs_md_title"))

    settings_col, spacing_col, pic_col = st.columns([1, 0.5, 1.5])
    with settings_col:
        st.info(_t("rs_text_need_to_restart_after_save_setting"))

        st.markdown(_t("rs_md_record_setting_title"))

        # 录制选项
        if "is_create_startup_shortcut" not in st.session_state:
            st.session_state.is_create_startup_shortcut = utils.is_file_already_in_startup("start_app.bat.lnk")
        st.session_state.is_create_startup_shortcut = st.checkbox(
            _t("rs_checkbox_start_record_when_startup"),
            value=st.session_state.is_create_startup_shortcut,
            help=_t("rs_checkbox_start_record_when_startup_help"),
        )
        is_start_recording_on_start_app = st.checkbox(
            _t("rs_checkbox_is_start_recording_on_start_app"), value=config.start_recording_on_startup
        )

        record_mode_option = [
            ("ffmpeg", _t("rs_text_record_mode_option_ffmpeg")),
            ("screenshot_array", _t("rs_text_record_mode_option_screenshot_array")),
        ]
        record_mode_col1, record_mode_col2 = st.columns([1.5, 1])
        with record_mode_col1:
            record_mode = st.selectbox(
                _t("rs_text_record_mode"),
                options=[i[1] for i in record_mode_option],
                index=[index for index, value in enumerate(record_mode_option) if value[0] == config.record_mode][0],
            )
        with record_mode_col2:
            st.empty()
            if record_mode == record_mode_option[1][1]:  # screenshot_array
                screenshot_interval_second = st.number_input(
                    _t("rs_input_screenshot_interval_second"),
                    value=config.screenshot_interval_second,
                    min_value=3,
                    max_value=15,
                    help=_t("rs_text_screenshot_interval_second_help"),
                )

        record_mode_col_tip1, record_mode_col_tip2 = st.columns([1, 3])
        if record_mode == record_mode_option[0][1]:  # ffmpeg
            with record_mode_col_tip1:
                st.image("__assets__\\record_method_ffmpeg.png")
            with record_mode_col_tip2:
                st.caption(_t("rs_text_ffmpeg_help"))
            is_record_system_sound = st.checkbox(
                _t("rs_checkbox_is_record_system_sound"),
                config.is_record_system_sound,
                disabled=True,
                help="Features still work in progress, please stay tuned.",
            )

        elif record_mode == record_mode_option[1][1]:  # screenshot_array
            record_screenshot_method_capture_foreground_window_only = st.checkbox(
                _t("rs_checkbox_record_screenshot_method_capture_foreground_window_only"),
                value=config.record_screenshot_method_capture_foreground_window_only,
            )
            convert_screenshots_to_vid_while_only_when_idle_or_plugged_in = st.checkbox(
                _t("rs_checkbox_convert_screenshots_to_vid_while_only_when_idle_or_plugged_in"),
                value=config.convert_screenshots_to_vid_while_only_when_idle_or_plugged_in,
            )
            with record_mode_col_tip1:
                if record_screenshot_method_capture_foreground_window_only:
                    st.image("__assets__\\record_method_screenshots_foreground_window.png")
                else:
                    st.image("__assets__\\record_method_screenshots.png")
            with record_mode_col_tip2:
                st.caption(_t("rs_text_screenshot_array_help"))

        # 检测到多显示器时，提供设置选项
        record_strategy_config = {
            _t("rs_text_record_strategy_option_all").format(num=len(st.session_state.display_info_formatted)): "all",
            _t("rs_text_record_strategy_option_single"): "single",
        }
        if st.session_state.display_count > 1 and (
            record_mode == record_mode_option[0][1] or record_screenshot_method_capture_foreground_window_only is False
        ):
            col1_ms, col2_ms = st.columns([1, 1])
            with col1_ms:
                display_record_strategy = st.selectbox(
                    _t("rs_text_record_range"),
                    index=1 if config.multi_display_record_strategy == "single" else 0,
                    options=[i for i in record_strategy_config.keys()],
                )
            with col2_ms:
                if display_record_strategy == _t("rs_text_record_strategy_option_single"):
                    display_record_selection = st.selectbox(
                        _t("rs_text_record_single_display_select"),
                        index=config.record_single_display_index - 1,
                        options=st.session_state.display_info_formatted,
                    )
                else:
                    display_record_selection = None
                    st.empty()
        else:
            display_record_strategy = None
            display_record_selection = None

        if record_mode == record_mode_option[0][1]:  # ffmpeg
            with st.expander(_t("rs_text_show_encode_option")):
                # if st.toggle(_t("rs_text_show_encode_option"), key="expand_encode_option_recording"):
                col_record_encoder, col_record_quality = st.columns([1, 1])
                with col_record_encoder:
                    RECORD_ENCODER_LST = list(CONFIG_RECORD_PRESET.keys())
                    record_encoder = st.selectbox(
                        _t("rs_text_record_encoder"),
                        index=RECORD_ENCODER_LST.index(config.record_encoder),
                        options=RECORD_ENCODER_LST,
                        help=_t("rs_text_record_help"),
                    )
                with col_record_quality:
                    record_bitrate = st.number_input(
                        _t("rs_text_record_bitrate"),
                        value=config.record_bitrate,
                        min_value=50,
                        max_value=10000,
                        help=_t("rs_text_bitrate_help"),
                    )
                if "265" in record_encoder:
                    st.warning(_t("rs_text_hevc_tips"), icon="🌚")

                estimate_display_cnt = (
                    1
                    if (display_record_strategy is None)
                    or (display_record_strategy == _t("rs_text_record_strategy_option_single"))
                    else len(st.session_state.display_info_formatted)
                )
                st.text(
                    _t("rs_text_estimate_hint").format(
                        min=round(0.025 * record_bitrate * estimate_display_cnt, 2),
                        max=round(0.125 * record_bitrate * estimate_display_cnt, 2),
                    )
                )

                if st.button(_t("rs_btn_encode_benchmark"), key="rs_btn_encode_benchmark_recording"):
                    with st.spinner(_t("rs_text_encode_benchmark_loading")):
                        result_df = record.record_encode_preset_benchmark_test()
                        st.dataframe(
                            result_df,
                            column_config={
                                "encoder preset": st.column_config.TextColumn(_t("rs_text_compress_encoder")),
                                "support": st.column_config.CheckboxColumn(_t("rs_text_support"), default=False),
                            },
                        )

        screentime_not_change_to_pause_record = st.number_input(
            _t("rs_input_stop_recording_when_screen_freeze"),
            value=config.screentime_not_change_to_pause_record,
            min_value=0,
        )

        exclude_words = st_tags(
            label=_t("rs_text_skip_recording_by_wintitle"), text=_t("rs_tag_input_tip"), value=config.exclude_words
        )

        st.divider()

        # 自动化维护选项
        st.markdown(_t("set_md_auto_maintain"))
        ocr_strategy_option_dict = {
            _t("rs_text_ocr_manual_update"): 0,
            _t("rs_text_ocr_auto_update"): 1,
        }
        if record_mode == record_mode_option[0][1]:  # ffmpeg
            ocr_strategy_option = st.selectbox(
                _t("rs_selectbox_ocr_strategy"),
                (list(ocr_strategy_option_dict.keys())),
                index=config.OCR_index_strategy,
            )
        else:
            ocr_strategy_option = _t("rs_text_ocr_auto_update")

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

        with st.expander(_t("rs_text_show_encode_option")):
            # if st.toggle(_t("rs_text_show_encode_option"), key="expand_encode_option_compress"):
            col1_encode, col2_encode, col3_encode = st.columns([1, 1, 1])
            with col1_encode:
                video_compress_encoder = st.selectbox(
                    _t("rs_text_compress_encoder"),
                    list(CONFIG_VIDEO_COMPRESS_PRESET.keys()),
                    index=find_key_position_in_dict(CONFIG_VIDEO_COMPRESS_PRESET, config.compress_encoder),
                )
            with col2_encode:
                video_compress_accelerator = st.selectbox(
                    _t("rs_text_compress_accelerator"),
                    list(CONFIG_VIDEO_COMPRESS_PRESET[video_compress_encoder].keys()),
                    index=find_key_position_in_dict(
                        CONFIG_VIDEO_COMPRESS_PRESET[video_compress_encoder], config.compress_accelerator
                    ),
                )
            with col3_encode:
                video_compress_crf = st.number_input(
                    _t("rs_text_compress_CRF"),
                    value=config.compress_quality,
                    min_value=0,
                    max_value=50,
                    help=_t("rs_text_compress_CRF_help"),
                )
            if "265" in video_compress_encoder:
                st.warning(_t("rs_text_hevc_tips"), icon="🌚")

            if st.button(_t("rs_btn_encode_benchmark")):
                with st.spinner(_t("rs_text_encode_benchmark_loading")):
                    result_df = record.encode_preset_benchmark_test(
                        scale_factor=video_compress_rate_selectbox, crf=video_compress_crf
                    )
                    if result_df is not None:
                        st.text(
                            f'{_t("rs_selectbox_compress_ratio")}: {video_compress_rate_selectbox}, {_t("rs_text_compress_CRF")}: {video_compress_crf}'
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
                    else:
                        st.error("test_video_filepath not found.")

        st.divider()

        if st.button(
            "Save and Apply All Changes / " + _t("text_apply_changes")
            if config.lang != "en"
            else "Save and Apply All Changes",
            type="primary",
            key="SaveBtnRecord",
        ):
            if display_record_strategy is not None:
                config.set_and_save_config("multi_display_record_strategy", record_strategy_config[display_record_strategy])
            if display_record_selection is None:
                config.set_and_save_config("record_single_display_index", 1)
            else:
                config.set_and_save_config(
                    "record_single_display_index", st.session_state.display_info_formatted.index(display_record_selection) + 1
                )

            utils.change_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut)

            config.set_and_save_config("record_mode", [value for value in record_mode_option if value[1] == record_mode][0][0])
            config.set_and_save_config("screenshot_interval_second", screenshot_interval_second)
            config.set_and_save_config(
                "record_screenshot_method_capture_foreground_window_only",
                record_screenshot_method_capture_foreground_window_only,
            )
            config.set_and_save_config(
                "convert_screenshots_to_vid_while_only_when_idle_or_plugged_in",
                convert_screenshots_to_vid_while_only_when_idle_or_plugged_in,
            )
            config.set_and_save_config("is_record_system_sound", is_record_system_sound)

            config.set_and_save_config("screentime_not_change_to_pause_record", screentime_not_change_to_pause_record)
            config.set_and_save_config("start_recording_on_startup", is_start_recording_on_start_app)
            config.set_and_save_config("OCR_index_strategy", ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("exclude_words", [item for item in exclude_words if len(item) >= 2])

            config.set_and_save_config("record_encoder", record_encoder)
            config.set_and_save_config("record_bitrate", record_bitrate)

            config.set_and_save_config("vid_store_day", vid_store_day)
            config.set_and_save_config("vid_compress_day", vid_compress_day)
            config.set_and_save_config("video_compress_rate", video_compress_rate_selectbox)

            config.set_and_save_config("compress_encoder", video_compress_encoder)
            config.set_and_save_config("compress_accelerator", video_compress_accelerator)
            config.set_and_save_config("compress_quality", video_compress_crf)

            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(2)
            st.rerun()

    with spacing_col:
        st.empty()

    with pic_col:
        howitwork_img = Image.open("__assets__\\workflow-" + config.lang + ".png")
        st.image(howitwork_img)
