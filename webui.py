import datetime
import json
import os
import subprocess
import time
from collections import OrderedDict
from pathlib import Path

import pandas as pd
import pyautogui
import streamlit as st
from PIL import Image

import ui.oneday
import ui.search
import ui.state
import windrecorder.maintainManager as maintainManager
import windrecorder.record as record
import windrecorder.state as state
import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.dbManager import DBManager
from windrecorder.utils import get_text as _t

update_button_key = "update_button"
reset_button_key = "setting_reset"

# python -m streamlit run webui.py

lang_map = utils.d_lang["lang_map"]


# 获取配置中语言选项是第几位；使设置选择项能匹配
def get_language_index(lang, data):
    for i, l in enumerate(data):
        if l == lang:
            return i
    return 1


lang_index = get_language_index(config.lang, utils.d_lang)

st.set_page_config(page_title="Windrecord - webui", page_icon="🦝", layout="wide")


# 从GitHub检查更新、添加提醒 - 初始化状态
if "update_info" not in st.session_state:
    st.session_state["update_info"] = _t("set_update_checking")
if "update_need" not in st.session_state:
    st.session_state["update_need"] = False
if "update_badge_emoji" not in st.session_state:
    st.session_state["update_badge_emoji"] = ""


# 数据库的前置更新索引状态提示
def draw_db_status():
    count, nocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir)
    timeCostStr = utils.estimate_indexing_time()
    if config.OCR_index_strategy == 1:
        # 启用自动索引
        if nocred_count == 1 and record.is_recording():
            st.success(
                _t("set_text_one_video_to_index").format(nocred_count=nocred_count, count=count),
                icon="✅",
            )
        elif nocred_count == 0:
            st.success(
                _t("set_text_no_video_need_index").format(nocred_count=nocred_count, count=count),
                icon="✅",
            )
        else:
            st.success(
                _t("set_text_some_video_will_be_index").format(nocred_count=nocred_count, count=count),
                icon="✅",
            )
    elif config.OCR_index_strategy == 2:
        if nocred_count == 1 and record.is_recording():
            st.success(
                _t("set_text_one_video_to_index").format(nocred_count=nocred_count, count=count),
                icon="✅",
            )
        elif nocred_count >= 1:
            st.warning(
                _t("set_text_video_not_index").format(nocred_count=nocred_count, count=count, timeCostStr=timeCostStr),
                icon="🧭",
            )
        else:
            st.success(
                _t("set_text_no_video_need_index").format(nocred_count=nocred_count, count=count),
                icon="✅",
            )


# 检查配置使用的ocr引擎
def check_ocr_engine():
    global config_ocr_engine_choice_index
    if config.ocr_engine == "Windows.Media.Ocr.Cli":
        config_ocr_engine_choice_index = 0
    elif config.ocr_engine == "ChineseOCR_lite_onnx":
        config_ocr_engine_choice_index = 1


# 检查配置使用的ocr语言
def check_ocr_lang():
    global config_ocr_lang_choice_index
    global os_support_lang_list

    os_support_lang_list = utils.get_os_support_lang()  # 获取系统支持的语言

    if config.ocr_lang in os_support_lang_list:  # 如果配置项在支持的列表中，返回索引值
        config_ocr_lang_choice_index = os_support_lang_list.index(config.ocr_lang)
    else:  # 如果配置项不在支持的列表中，返回默认值，config设定为支持的第一项
        config_ocr_lang_choice_index = 0
        config.set_and_save_config("ocr_lang", os_support_lang_list[0])


# 调整屏幕忽略范围的设置可视化
def screen_ignore_padding(topP, rightP, bottomP, leftP, use_screenshot=False):
    image_padding_refer = Image.open("__assets__\\setting-crop-refer-pure.png")

    if use_screenshot:
        image_padding_refer = pyautogui.screenshot()
        image_padding_refer_width, image_padding_refer_height = image_padding_refer.size
        image_padding_refer_height = int(350 * image_padding_refer_height / image_padding_refer_width)
        image_padding_refer = image_padding_refer.resize((350, image_padding_refer_height))
        image_padding_refer_fade = Image.new("RGBA", (350, 200), (255, 233, 216, 100))  # 添加背景色蒙层
        image_padding_refer.paste(image_padding_refer_fade, (0, 0), image_padding_refer_fade)

    image_padding_refer_width, image_padding_refer_height = image_padding_refer.size
    topP_height = round(image_padding_refer_height * topP * 0.01)
    bottomP_height = round(image_padding_refer_height * bottomP * 0.01)
    leftP_width = round(image_padding_refer_width * leftP * 0.01)
    rightP_width = round(image_padding_refer_width * rightP * 0.01)

    image_color_area = Image.new("RGBA", (image_padding_refer_width, topP_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0), image_color_area)
    image_color_area = Image.new("RGBA", (image_padding_refer_width, bottomP_height), (100, 0, 255, 80))
    image_padding_refer.paste(
        image_color_area,
        (0, image_padding_refer_height - bottomP_height),
        image_color_area,
    )
    image_color_area = Image.new("RGBA", (leftP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0), image_color_area)
    image_color_area = Image.new("RGBA", (rightP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(
        image_color_area,
        (image_padding_refer_width - rightP_width, 0),
        image_color_area,
    )

    return image_padding_refer


# 更改语言
def config_set_lang(lang_name):
    INVERTED_LANG_MAP = {v: k for k, v in lang_map.items()}
    lang_code = INVERTED_LANG_MAP.get(lang_name)

    if not lang_code:
        print(f"webui: Invalid language name: {lang_name}")
        return

    config.set_and_save_config("lang", lang_code)


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
    st.markdown(_t("rs_md_title"))

    col1c, col2c, col3c = st.columns([1, 0.5, 1.5])
    with col1c:
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

        btn_refresh = st.button(_t("rs_btn_check_record_stat"), on_click=update_record_btn_state)

        if st.session_state.update_btn_refresh_press:
            if record.is_recording():
                st.success(_t("rs_text_recording_screen_now"), icon="🦚")
                # stop_record_btn = st.button('停止录制屏幕', type="secondary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                # if stop_record_btn:
                #     st.toast("正在结束录屏进程……")
                #     utils.kill_recording()

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

    with col2c:
        st.empty()

    with col3c:
        howitwork_img = Image.open("__assets__\\workflow-" + config.lang + ".png")
        st.image(howitwork_img)


def update_database_clicked():
    st.session_state.update_button_disabled = True


# 设置页
with setting_tab:
    st.markdown(_t("set_md_title"))

    col1b, col2b, col3b = st.columns([1, 0.5, 1.5])
    with col1b:
        # 更新数据库
        st.markdown(_t("set_md_index_db"))

        # 绘制数据库提示横幅
        draw_db_status()

        col1, col2 = st.columns([1, 1])
        with col1:
            update_db_btn = st.button(
                _t("set_btn_update_db_manual"),
                type="secondary",
                key="update_button_key",
                disabled=st.session_state.get("update_button_disabled", False),
                on_click=update_database_clicked,
            )
            is_shutdown_pasocon_after_updatedDB = st.checkbox(
                _t("set_checkbox_shutdown_after_updated"),
                value=False,
                disabled=st.session_state.get("update_button_disabled", False),
            )

        with col2:
            # 设置ocr引擎
            if config.enable_ocr_chineseocr_lite_onnx:
                check_ocr_engine()
                config_ocr_engine = st.selectbox(
                    _t("set_selectbox_local_ocr_engine"),
                    ("Windows.Media.Ocr.Cli", "ChineseOCR_lite_onnx"),
                    index=config_ocr_engine_choice_index,
                    help=_t("set_selectbox_local_ocr_engine_help"),
                )

            # 设定ocr引擎语言
            check_ocr_lang()
            config_ocr_lang = st.selectbox(
                _t("set_selectbox_ocr_lang"),
                os_support_lang_list,
                index=config_ocr_lang_choice_index,
            )

            # 设置排除词
            exclude_words = st.text_area(
                _t("set_input_exclude_word"),
                value=utils.list_to_string(config.exclude_words),
                help=_t("set_input_exclude_word_help"),
            )

        # 更新数据库按钮
        if update_db_btn:
            try:
                st.divider()
                estimate_time_str = utils.estimate_indexing_time()  # 预估剩余时间
                with st.spinner(_t("set_text_updating_db").format(estimate_time_str=estimate_time_str)):
                    timeCost = time.time()  # 预埋计算实际时长
                    maintainManager.maintain_manager_main()  # 更新数据库

                    timeCost = time.time() - timeCost
            except Exception as ex:
                st.exception(ex)
            else:
                timeCostStr = utils.convert_seconds_to_hhmmss(timeCost)
                st.success(
                    _t("set_text_db_updated_successful").format(timeCostStr=timeCostStr),
                    icon="🧃",
                )
            finally:
                if is_shutdown_pasocon_after_updatedDB:
                    subprocess.run(["shutdown", "-s", "-t", "60"], shell=True)
                st.snow()
                st.session_state.update_button_disabled = False
                st.button(_t("set_btn_got_it"), key=reset_button_key)

        st.divider()
        col1pb, col2pb = st.columns([1, 1])
        with col1pb:
            st.markdown(_t("set_md_ocr_ignore_area"), help=_t("set_md_ocr_ignore_area_help"))
        with col2pb:
            st.session_state.ocr_screenshot_refer_used = st.toggle(_t("set_toggle_use_screenshot_as_refer"), False)

        if "ocr_padding_top" not in st.session_state:
            st.session_state.ocr_padding_top = config.ocr_image_crop_URBL[0]
        if "ocr_padding_right" not in st.session_state:
            st.session_state.ocr_padding_right = config.ocr_image_crop_URBL[1]
        if "ocr_padding_bottom" not in st.session_state:
            st.session_state.ocr_padding_bottom = config.ocr_image_crop_URBL[2]
        if "ocr_padding_left" not in st.session_state:
            st.session_state.ocr_padding_left = config.ocr_image_crop_URBL[3]

        col1pa, col2pa, col3pa = st.columns([0.5, 0.5, 1])
        with col1pa:
            st.session_state.ocr_padding_top = st.number_input(
                _t("set_text_top_padding"),
                value=st.session_state.ocr_padding_top,
                min_value=0,
                max_value=40,
            )
            st.session_state.ocr_padding_bottom = st.number_input(
                _t("set_text_bottom_padding"),
                value=st.session_state.ocr_padding_bottom,
                min_value=0,
                max_value=40,
            )

        with col2pa:
            st.session_state.ocr_padding_left = st.number_input(
                _t("set_text_left_padding"),
                value=st.session_state.ocr_padding_left,
                min_value=0,
                max_value=40,
            )
            st.session_state.ocr_padding_right = st.number_input(
                _t("set_text_right_padding"),
                value=st.session_state.ocr_padding_right,
                min_value=0,
                max_value=40,
            )
        with col3pa:
            image_setting_crop_refer = screen_ignore_padding(
                st.session_state.ocr_padding_top,
                st.session_state.ocr_padding_right,
                st.session_state.ocr_padding_bottom,
                st.session_state.ocr_padding_left,
                use_screenshot=st.session_state.ocr_screenshot_refer_used,
            )
            st.image(image_setting_crop_refer)

        st.divider()

        # 界面设置组
        col1_ui, col2_ui = st.columns([1, 1])
        with col1_ui:
            st.markdown(_t("set_md_gui"))
            option_show_oneday_wordcloud = st.checkbox(
                _t("set_checkbox_show_wordcloud_under_oneday"),
                value=config.show_oneday_wordcloud,
            )
            # 使用中文形近字进行搜索
            config_use_similar_ch_char_to_search = st.checkbox(
                _t("set_checkbox_use_similar_zh_char_to_search"),
                value=config.use_similar_ch_char_to_search,
                help=_t("set_checkbox_use_similar_zh_char_to_search_help"),
            )
        with col2_ui:
            config_wordcloud_user_stop_words = st.text_area(
                _t("set_input_wordcloud_filter"),
                help=_t("set_input_wordcloud_filter_help"),
                value=utils.list_to_string(config.wordcloud_user_stop_words),
            )

        # 每页结果最大数量
        col1_ui2, col2_ui2 = st.columns([1, 1])
        with col1_ui2:
            config_max_search_result_num = st.number_input(
                _t("set_input_max_num_search_page"),
                min_value=1,
                max_value=500,
                value=config.max_page_result,
            )
        with col2_ui2:
            config_oneday_timeline_num = st.number_input(
                _t("set_input_oneday_timeline_thumbnail_num"),
                min_value=50,
                max_value=100,
                value=config.oneday_timeline_pic_num,
                help=_t("set_input_oneday_timeline_thumbnail_num_help"),
            )

        # 选择语言
        lang_choice = OrderedDict((k, "" + v) for k, v in lang_map.items())  # 根据读入列表排下序
        language_option = st.selectbox(
            "🌎 Interface Language / 更改显示语言 / 表示言語を変更する",
            (list(lang_choice.values())),
            index=lang_index,
        )

        st.divider()

        if st.button(
            "Save and Apple All Change / 保存并应用所有更改",
            type="primary",
            key="SaveBtnGeneral",
        ):
            config_set_lang(language_option)
            config.set_and_save_config("max_page_result", config_max_search_result_num)
            # config.set_and_save_config("ocr_engine", config_ocr_engine)
            config.set_and_save_config("ocr_lang", config_ocr_lang)
            config.set_and_save_config("exclude_words", utils.string_to_list(exclude_words))
            config.set_and_save_config("show_oneday_wordcloud", option_show_oneday_wordcloud)
            config.set_and_save_config("use_similar_ch_char_to_search", config_use_similar_ch_char_to_search)
            config.set_and_save_config(
                "ocr_image_crop_URBL",
                [
                    st.session_state.ocr_padding_top,
                    st.session_state.ocr_padding_right,
                    st.session_state.ocr_padding_bottom,
                    st.session_state.ocr_padding_left,
                ],
            )
            config.set_and_save_config(
                "wordcloud_user_stop_words",
                utils.string_to_list(config_wordcloud_user_stop_words),
            )
            config.set_and_save_config("oneday_timeline_pic_num", config_oneday_timeline_num)
            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(1)
            st.experimental_rerun()

    with col2b:
        st.empty()

    with col3b:
        # 关于
        # 从GitHub检查更新、添加提醒 - 位于设置页靠后的流程，以不打扰用户
        if "update_check" not in st.session_state:
            try:
                with st.spinner(_t("set_update_checking")):
                    tool_version, tool_update_date = utils.get_github_version_and_date()
                    (
                        tool_local_version,
                        tool_local_update_date,
                    ) = utils.get_current_version_and_update()
                if tool_update_date > tool_local_update_date:
                    st.session_state.update_info = _t("set_update_new").format(tool_version=tool_version)
                    st.session_state.update_need = True
                    st.session_state.update_badge_emoji = "✨"
                else:
                    st.session_state.update_info = _t("set_update_latest")
            except Exception as e:
                st.session_state.update_info = _t("set_update_fail").format(e=e)
            st.session_state["update_check"] = True

        about_image_b64 = utils.image_to_base64("__assets__\\readme_racoonNagase.png")
        st.markdown(
            f"<img align='right' style='max-width: 100%;max-height: 100%;' src='data:image/png;base64, {about_image_b64}'/>",
            unsafe_allow_html=True,
        )

        about_path = "config\\src\\meta.json"
        with open(about_path, "r", encoding="utf-8") as f:
            about_json = json.load(f)
        about_markdown = (
            Path(f"config\\src\\about_{config.lang}.md")
            .read_text(encoding="utf-8")
            .format(
                version=about_json["version"],
                update_date=about_json["update_date"],
                update_info=st.session_state.update_info,
            )
        )
        st.markdown(about_markdown, unsafe_allow_html=True)

web_footer_state()
