import time
import os
import datetime

import streamlit as st
from PIL import Image
from streamlit_tags import st_tags

from windrecorder import record, utils
from windrecorder.config import (
    CONFIG_RECORD_PRESET,
    CONFIG_VIDEO_COMPRESS_PRESET,
    config,
)
from windrecorder.logger import get_logger
from windrecorder.utils import find_key_position_in_dict
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)


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
    energy_saving_mode_option = [
        (0, _t("rs_option_energy_saving_instantly")),
        (1, _t("rs_option_energy_saving_plug")),
        (2, _t("rs_option_energy_saving_idle")),
    ]
    convert_screenshots_to_vid_energy_saving_mode = [
        value
        for index, value in enumerate(energy_saving_mode_option)
        if value[0] == config.convert_screenshots_to_vid_energy_saving_mode
    ][0][1]

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

            convert_screenshots_to_vid_energy_saving_mode = st.radio(
                "🍃 " + _t("rs_text_energy_saving"),
                [i[1] for i in energy_saving_mode_option],
                index=[
                    index
                    for index, value in enumerate(energy_saving_mode_option)
                    if value[0] == config.convert_screenshots_to_vid_energy_saving_mode
                ][0],
                help=_t("rs_text_energy_saving_help"),
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

        record_deep_linking = st.checkbox(
            _t("rs_checkbox_record_deep_linking"), value=config.record_deep_linking, help=_t("rs_help_record_deep_linking")
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

            # Add CPU thread count selector if using CPU encoder
            if video_compress_accelerator == "cpu":
                import multiprocessing

                cpu_count = multiprocessing.cpu_count()
                default_threads = max(1, cpu_count // 4)  # Default to 1/4 of CPU cores

                current_threads = config.compress_cpu_threads if hasattr(config, "compress_cpu_threads") else default_threads

                video_compress_cpu_threads = st.slider(
                    _t("rs_text_compress_cpu_threads"),
                    value=current_threads,
                    min_value=1,
                    max_value=cpu_count,
                    help=_t("rs_text_compress_cpu_threads_help"),
                )

                # Save the CPU thread setting immediately when changed
                if video_compress_cpu_threads != current_threads:
                    config.set_and_save_config("compress_cpu_threads", video_compress_cpu_threads)
            else:
                video_compress_cpu_threads = None

            if st.button(_t("rs_btn_encode_benchmark")):
                with st.spinner(_t("rs_text_encode_benchmark_loading")):
                    # Pass the CPU thread count if using CPU encoder
                    cpu_threads = video_compress_cpu_threads if video_compress_accelerator == "cpu" else None
                    result_df = record.encode_preset_benchmark_test(
                        scale_factor=video_compress_rate_selectbox, crf=video_compress_crf, cpu_threads=cpu_threads
                    )
                    if result_df is not None:
                        st.text(
                            f'{_t("rs_selectbox_compress_ratio")}: {video_compress_rate_selectbox}, '
                            f'{_t("rs_text_compress_CRF")}: {video_compress_crf}, '
                            f'{_t("rs_text_compress_cpu_threads")}: {cpu_threads}'
                            if cpu_threads
                            else ""
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

        # ============================================================================
        # 音频录制与 ASR 设置
        # ============================================================================
        st.markdown("#### 🎤 Audio & ASR / 音频与语音识别")

        config_enable_audio_recording = st.checkbox(
            "Enable Audio / 启用音频",
            value=config.enable_audio_recording,
        )

        if config_enable_audio_recording:
            # 基本设置
            st.markdown("**Basic Settings / 基本设置**")

            config_record_system_audio = st.checkbox(
                "🔊 System Audio / 系统音频",
                value=config.record_system_audio,
            )

            config_record_mic_audio = st.checkbox(
                "🎤 Microphone / 麦克风",
                value=config.record_mic_audio,
            )

            config_enable_audio_asr = st.checkbox(
                "ASR (Speech-to-Text) / 语音识别",
                value=config.enable_audio_asr,
            )

            config_audio_store_day = st.number_input(
                "Retention Days / 保留天数",
                1, 365,
                value=config.audio_store_day,
            )

            # 设备设置
            st.markdown("**Audio Devices / 音频设备**")

            # 自动加载上次使用的设备（页面加载时）
            if "audio_devices_auto_loaded" not in st.session_state:
                try:
                    devs = utils.get_audio_devices()
                    st.session_state.audio_devices = devs
                    st.session_state.audio_devices_auto_loaded = True
                except Exception as e:
                    st.warning(f"⚠️ Failed to auto-detect devices / 自动检测设备失败: {e}")

            if st.button("🔍 Detect Devices / 检测设备"):
                devs = utils.get_audio_devices()
                st.session_state.audio_devices = devs

            if "audio_devices" in st.session_state:
                devs = st.session_state.audio_devices.get('all_devices', [])
                if devs:
                    st.success(f"✅ Found {len(devs)} devices / 找到 {len(devs)} 个设备")

                    # 显示当前配置的设备
                    current_sys = config.system_audio_device_name
                    current_mic = config.mic_audio_device_name

                    # 检查设备是否在列表中
                    sys_available = current_sys in devs
                    mic_available = current_mic in devs

                    if sys_available and mic_available:
                        st.caption(f"✅ Current devices are available / 当前设备可用")
                    else:
                        if not sys_available:
                            st.warning(f"⚠️ System audio device not found: {current_sys} / 系统音频设备未找到")
                        if not mic_available:
                            st.warning(f"⚠️ Microphone device not found: {current_mic} / 麦克风设备未找到")

                    with st.expander("View All Devices / 查看所有设备"):
                        for i, d in enumerate(devs, 1):
                            # 标记当前正在使用的设备
                            marker = ""
                            if d == current_sys:
                                marker = " 🔊 (System / 系统)"
                            elif d == current_mic:
                                marker = " 🎤 (Mic / 麦克风)"
                            st.caption(f"{i}. {d}{marker}")
                else:
                    st.warning("⚠️ No devices found / 未找到设备")

            # 设备选择
            devs = st.session_state.get("audio_devices", {}).get('all_devices', [config.system_audio_device_name])

            try:
                sys_idx = devs.index(config.system_audio_device_name)
            except:
                sys_idx = 0

            config_system_audio_device_name = st.selectbox(
                "System Audio Device / 系统音频设备",
                devs,
                sys_idx,
            )

            if st.button("🎵 Test System Audio / 测试系统音频"):
                ok, msg, _ = utils.test_audio_device(config_system_audio_device_name, 2)
                (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg}")

            try:
                mic_idx = devs.index(config.mic_audio_device_name)
            except:
                mic_idx = 0

            config_mic_audio_device_name = st.selectbox(
                "Microphone Device / 麦克风设备",
                devs,
                mic_idx,
            )

            if st.button("🎤 Test Microphone / 测试麦克风"):
                ok, msg, _ = utils.test_audio_device(config_mic_audio_device_name, 2)
                (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg}")

            # ASR 处理控制
            if config_enable_audio_asr:
                st.markdown(f"### {_t('recording_asr_control_title')}")

                # 显示当前状态
                if config.asr_processing_paused:
                    st.info(f"⏸️ {_t('recording_asr_status_paused')}")
                else:
                    st.success(f"▶️ {_t('recording_asr_status_running')}")

                # 控制按钮
                col_pause, col_resume = st.columns(2)
                with col_pause:
                    if st.button(_t("recording_asr_btn_pause"), disabled=config.asr_processing_paused):
                        config.set_and_save_config("asr_processing_paused", True)
                        st.success(_t("recording_asr_paused_success"))
                        st.rerun()

                with col_resume:
                    if st.button(_t("recording_asr_btn_resume"), disabled=not config.asr_processing_paused):
                        config.set_and_save_config("asr_processing_paused", False)
                        st.success(_t("recording_asr_resumed_success"))
                        st.rerun()

                # 手动转录功能
                st.markdown(f"### {_t('recording_asr_manual_title')}")

                col_batch, col_btn = st.columns([1, 1])
                with col_batch:
                    manual_batch_size = st.number_input(
                        _t("recording_asr_manual_batch_size"),
                        min_value=1,
                        max_value=50,
                        value=5,
                        help=_t("recording_asr_manual_help")
                    )

                with col_btn:
                    st.write("")  # 添加垂直间距
                    st.write("")
                    if st.button(_t("recording_asr_manual_btn_start"), type="primary"):
                        # 执行手动转录
                        try:
                            from windrecorder.asr_manager import asr_manager
                            from windrecorder.db_manager import db_manager

                            # 查询待处理的音频文件
                            pending_audios = db_manager.db_get_pending_asr_audiofiles(limit=manual_batch_size)

                            if not pending_audios:
                                st.info(_t("recording_asr_manual_no_pending"))
                            else:
                                # 创建进度条
                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                total = len(pending_audios)
                                success_count = 0

                                for idx, audio_info in enumerate(pending_audios, 1):
                                    # 更新进度
                                    progress_bar.progress(idx / total)
                                    status_text.text(_t("recording_asr_manual_processing").format(current=idx, total=total))

                                    audio_filename = audio_info["audiofile_name"]
                                    audio_type = audio_info["audio_type"]
                                    audio_path = audio_info["audio_path"]

                                    # 检查文件是否存在
                                    if not os.path.exists(audio_path):
                                        db_manager.db_mark_audio_asr_indexed(audio_filename, success=False)
                                        continue

                                    # 执行 ASR
                                    result = asr_manager.transcribe_audio(audio_path, audio_type)

                                    # 更新数据库
                                    if result["text"]:
                                        db_manager.db_update_asr_text(
                                            audiofile_name=audio_filename,
                                            asr_text=result["text"],
                                            asr_language=result["language"],
                                            audio_source=1 if audio_type == "system" else 2,
                                        )
                                        success_count += 1

                                    # 标记已处理
                                    db_manager.db_mark_audio_asr_indexed(audio_filename, success=True)

                                # 完成
                                progress_bar.progress(1.0)
                                status_text.empty()
                                st.success(_t("recording_asr_manual_success").format(count=success_count))

                        except Exception as e:
                            st.error(f"{_t('recording_asr_manual_error')}: {e}")
                            logger.error(f"Manual ASR processing error: {e}", exc_info=True)

            # ASR 高级设置
            if config_enable_audio_asr:
                with st.expander("⚙️ ASR Advanced Settings / ASR 高级设置"):
                    config_asr_use_gpu = st.checkbox(
                        "Use GPU / 使用GPU",
                        value=config.asr_use_gpu,
                        help="Enable GPU acceleration (requires NVIDIA GPU with CUDA) / 启用GPU加速（需要NVIDIA显卡和CUDA）"
                    )

                    config_asr_use_itn = st.checkbox(
                        "ITN (Inverse Text Normalization) / 逆文本正则化",
                        value=config.asr_use_itn,
                        help="Add punctuation marks to transcription (recommended) / 为转录文本添加标点符号（推荐开启）"
                    )

                    config_asr_ban_emo_unk = st.checkbox(
                        "Force Emotion Tags / 强制情感标签",
                        value=config.asr_ban_emo_unk,
                        help="Disable <|NEUTRAL|> tag, force all sentences to have emotion tags / 禁用<|NEUTRAL|>标签，强制所有句子都有情感标签"
                    )

                    config_batch_size_asr_in_idle = st.number_input(
                        "Batch Size / 批处理数量",
                        1, 20,
                        value=config.batch_size_asr_in_idle,
                        help="Number of audio files to process per idle maintenance cycle / 每次空闲维护处理的音频文件数量"
                    )

                    config_asr_min_text_length = st.number_input(
                        "Min Text Length / 最小文本长度",
                        1, 50,
                        value=config.asr_min_text_length,
                        help="Discard transcriptions shorter than this (filter out noise) / 丢弃短于此长度的转录（过滤噪音）"
                    )

                    config_asr_repetitive_threshold = st.slider(
                        "Repetitive Threshold / 重复阈值",
                        0.0, 1.0,
                        value=config.asr_repetitive_threshold,
                        step=0.05,
                        help="Filter music/repetitive content. Lower = more strict (e.g., 0.3 filters song lyrics) / 过滤音乐和重复内容。越低越严格（如0.3会过滤歌词）"
                    )

                    config_asr_music_filter_keywords = st.text_input(
                        "Music Filter Keywords / 音乐过滤关键词",
                        value=",".join(config.asr_music_filter_keywords),
                        help="Comma-separated keywords to filter system audio (e.g., 'lalala,nanana,music') / 用逗号分隔的关键词，用于过滤系统音频（如'lalala,nanana,music'）"
                    )

                # ASR 测试
                with st.expander("🧪 Test ASR Model / 测试 ASR 模型"):
                    # 使用windrecorder/config_src目录下的 example 文件夹
                    current_dir = os.path.dirname(__file__)
                    example_path = os.path.join(current_dir, "..", "config_src", "example")
                    example_path = os.path.normpath(example_path)

                    # 预定义的测试文件列表
                    test_files = {
                        "English": "en.mp3",
                        "Chinese / 中文": "zh.mp3",
                        "Japanese / 日语": "ja.mp3",
                        "Korean / 韩语": "ko.mp3",
                        "Cantonese / 粤语": "yue.mp3"
                    }

                    # 检查哪些文件存在
                    available_tests = {}
                    for lang, filename in test_files.items():
                        test_path = os.path.join(example_path, filename)
                        if os.path.exists(test_path):
                            available_tests[lang] = test_path

                    if available_tests:
                        test_lang = st.selectbox(
                            "Select Test Language / 选择测试语言",
                            options=list(available_tests.keys()),
                            help="These are example audio files from FunASR model / 这些是 FunASR 模型自带的示例音频"
                        )
                        test_path = available_tests[test_lang]

                        st.audio(open(test_path, "rb").read(), format="audio/mp3")

                        if st.button("🔬 Run ASR Test / 运行 ASR 测试"):
                            st.info("ℹ️ **First-time loading**: The SenseVoice model (~900MB) will be downloaded automatically. This may take 5-10 minutes depending on your network speed.\n\n**首次加载**：SenseVoice 模型（约900MB）将自动下载，根据网速可能需要5-10分钟。")

                            with st.spinner("Processing (downloading model if first time)... / 处理中（首次会下载模型）..."):
                                try:
                                    from windrecorder.asr_manager import asr_manager
                                    result = asr_manager.transcribe_audio(test_path, "test")

                                    if result and result.get('text'):
                                        st.success("✅ Success / 成功")
                                        st.text_area("Transcription / 转录文本:", value=result['text'], height=100)
                                        st.caption(f"Language / 语言: {result.get('language', 'unknown')}")
                                        if result.get('emotion'):
                                            st.caption(f"Emotion / 情感: {result.get('emotion')}")
                                    else:
                                        st.warning("⚠️ No text extracted (might be filtered as noise) / 未提取到文本（可能被过滤为噪音）")
                                        if result.get('raw_text'):
                                            st.caption(f"Raw text (before filtering) / 原始文本（过滤前）: {result['raw_text'][:100]}")
                                except Exception as e:
                                    st.error(f"❌ Error / 错误: {e}")
                                    st.caption("Check the logs for more details / 查看日志获取更多详细信息")
                    else:
                        st.info(f"No example files found / 未找到示例文件\n\nExpected path / 预期路径: `{example_path}/{{en,zh,ja,ko,yue}}.mp3`")
        else:
            # 禁用时使用当前配置
            config_record_system_audio = config.record_system_audio
            config_record_mic_audio = config.record_mic_audio
            config_enable_audio_asr = config.enable_audio_asr
            config_audio_store_day = config.audio_store_day
            config_system_audio_device_name = config.system_audio_device_name
            config_mic_audio_device_name = config.mic_audio_device_name
            config_asr_use_gpu = config.asr_use_gpu
            config_asr_use_itn = config.asr_use_itn
            config_asr_ban_emo_unk = config.asr_ban_emo_unk
            config_batch_size_asr_in_idle = config.batch_size_asr_in_idle
            config_asr_min_text_length = config.asr_min_text_length
            config_asr_repetitive_threshold = config.asr_repetitive_threshold
            config_asr_music_filter_keywords = ""

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
                "convert_screenshots_to_vid_energy_saving_mode",
                [value for value in energy_saving_mode_option if value[1] == convert_screenshots_to_vid_energy_saving_mode][0][
                    0
                ],
            )
            config.set_and_save_config("is_record_system_sound", is_record_system_sound)

            config.set_and_save_config("record_deep_linking", record_deep_linking)
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
            if video_compress_cpu_threads is not None:
                config.set_and_save_config("compress_cpu_threads", video_compress_cpu_threads)

            # 保存音频相关配置
            config.set_and_save_config("enable_audio_recording", config_enable_audio_recording)
            config.set_and_save_config("record_system_audio", config_record_system_audio)
            config.set_and_save_config("record_mic_audio", config_record_mic_audio)
            config.set_and_save_config("enable_audio_asr", config_enable_audio_asr)
            config.set_and_save_config("audio_store_day", config_audio_store_day)
            config.set_and_save_config("system_audio_device_name", config_system_audio_device_name)
            config.set_and_save_config("mic_audio_device_name", config_mic_audio_device_name)
            config.set_and_save_config("asr_use_gpu", config_asr_use_gpu)
            config.set_and_save_config("asr_use_itn", config_asr_use_itn)
            config.set_and_save_config("asr_ban_emo_unk", config_asr_ban_emo_unk)
            config.set_and_save_config("batch_size_asr_in_idle", config_batch_size_asr_in_idle)
            config.set_and_save_config("asr_min_text_length", config_asr_min_text_length)
            config.set_and_save_config("asr_repetitive_threshold", config_asr_repetitive_threshold)
            # 处理音乐过滤关键词
            music_keywords = [k.strip() for k in config_asr_music_filter_keywords.split(",") if k.strip()]
            config.set_and_save_config("asr_music_filter_keywords", music_keywords)

            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(2)
            st.rerun()

    with spacing_col:
        st.empty()

    with pic_col:
        howitwork_img = Image.open("__assets__\\workflow-" + config.lang + ".png")
        st.image(howitwork_img)
