import hashlib
import subprocess
import time
from pathlib import Path

import pyautogui
import streamlit as st
from PIL import Image

import windrecorder.record as record
import windrecorder.utils as utils
from windrecorder import __version__, file_utils, ocr_manager
from windrecorder.config import config
from windrecorder.logger import get_logger
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)

if config.img_embed_module_install:
    try:
        from windrecorder import img_embed_manager
    except ModuleNotFoundError:
        config.set_and_save_config("img_embed_module_install", False)

lang_map = utils.d_lang["lang_map"]


def set_config_lang(lang_name):
    inverted_lang_map = {v: k for k, v in lang_map.items()}
    lang_code = inverted_lang_map.get(lang_name)

    if not lang_code:
        logger.error(f"Invalid language name: {lang_name}")
        return

    config.set_and_save_config("lang", lang_code)


def render():
    # 初始化全局状态
    if "is_cuda_available" not in st.session_state:
        if config.img_embed_module_install:
            st.session_state.is_cuda_available = img_embed_manager.is_cuda_available
        else:
            st.session_state.is_cuda_available = False

    st.markdown(_t("set_md_title"))

    col1b, col2b, col3b = st.columns([1, 0.5, 1.5])
    with col1b:
        # 更新数据库
        st.markdown(_t("set_md_index_db"))

        # 绘制数据库提示横幅
        draw_db_status()

        def update_database_clicked():
            st.session_state.update_button_disabled = True

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
            # if config.enable_ocr_chineseocr_lite_onnx:
            #     check_ocr_engine()
            #     config_ocr_engine = st.selectbox(
            #         _t("set_selectbox_local_ocr_engine"),
            #         ("Windows.Media.Ocr.Cli", "ChineseOCR_lite_onnx"),
            #         index=config_ocr_engine_choice_index,
            #         help=_t("set_selectbox_local_ocr_engine_help"),
            #     )

            # 设定ocr引擎语言
            if "os_support_lang" not in st.session_state:  # 获取系统支持的OCR语言
                st.session_state.os_support_lang = utils.get_os_support_lang()

            ocr_lang_index = legal_ocr_lang_index()
            config_ocr_lang = st.selectbox(
                _t("set_selectbox_ocr_lang"),
                st.session_state.os_support_lang,
                index=ocr_lang_index,
            )

            if config.img_embed_module_install:
                option_enable_img_embed_search = st.checkbox(
                    _t("set_checkbox_enable_img_emb"),
                    help=_t("set_text_enable_img_emb_help"),
                    value=config.enable_img_embed_search,
                )
            else:
                option_enable_img_embed_search = False

        if not st.session_state.is_cuda_available and option_enable_img_embed_search:
            st.warning(_t("set_text_img_emb_not_suppport_cuda"))

        # 更新数据库按钮
        if update_db_btn:
            try:
                st.divider()
                estimate_time_str = utils.estimate_indexing_time()  # 预估剩余时间
                with st.spinner(_t("set_text_updating_db").format(estimate_time_str=estimate_time_str)):
                    timeCost = time.time()  # 预埋计算实际时长
                    ocr_manager.ocr_manager_main()  # 更新数据库

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
                st.button(_t("set_btn_got_it"), key="setting_reset")

        st.divider()

        # OCR 时忽略屏幕四边的区域范围
        # FIXME 添加多屏幕设置支持
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
            # 一日之时启用三栏布局
            config_enable_3_columns_in_oneday = st.checkbox(
                _t("set_checkbox_enable_3_columns_in_oneday"),
                value=config.enable_3_columns_in_oneday,
                help=_t("set_help_enable_3_columns_in_oneday"),
            )
            # 使用中文形近字进行搜索
            config_use_similar_ch_char_to_search = st.checkbox(
                _t("set_checkbox_use_similar_zh_char_to_search"),
                value=config.use_similar_ch_char_to_search,
                help=_t("set_checkbox_use_similar_zh_char_to_search_help"),
            )
            # 搜索中推荐近似词
            if config.img_embed_module_install:
                config_enable_synonyms_recommend = st.checkbox(
                    _t("set_checkbox_synonyms_recommand"),
                    value=config.enable_synonyms_recommend,
                    help=_t("set_help_synonyms_recommand"),
                )
            else:
                config_enable_synonyms_recommend = False

        with col2_ui:
            config_wordcloud_user_stop_words = st.text_area(
                _t("set_input_wordcloud_filter"),
                help=_t("set_input_wordcloud_filter_help"),
                value=utils.list_to_string(config.wordcloud_user_stop_words),
            )

        # 每页结果最大数量
        col1_ui2, col2_ui2 = st.columns([1, 1])
        with col1_ui2:
            day_begin_time_list = [
                ("00:00", 0),
                ("01:00", 60),
                ("02:00", 120),
                ("03:00", 180),
                ("04:00", 240),
                ("05:00", 300),
                ("06:00", 360),
            ]

            option_day_begin_time_oneday = st.selectbox(
                _t("set_input_day_begin_minutes"),
                index=find_index_in_tuple_timelist(list=day_begin_time_list, target=config.day_begin_minutes),
                options=[item[0] for item in day_begin_time_list],
                help=_t("set_help_day_begin_minutes"),
            )

            config_max_search_result_num = st.number_input(
                _t("set_input_max_num_search_page"),
                min_value=5,
                max_value=500,
                value=config.max_page_result,
            )

        with col2_ui2:
            # 「一天之时」时间轴的横向缩略图数量
            config_oneday_timeline_num = st.number_input(
                _t("set_input_oneday_timeline_thumbnail_num"),
                min_value=50,
                max_value=100,
                value=config.oneday_timeline_pic_num,
                help=_t("set_input_oneday_timeline_thumbnail_num_help"),
            )

            # imgemb 选项
            if config.img_embed_module_install and option_enable_img_embed_search:
                config_img_embed_search_recall_result_per_db = st.number_input(
                    _t("set_input_img_emb_max_recall_count"),
                    min_value=5,
                    max_value=100,
                    value=config.img_embed_search_recall_result_per_db,
                    help=_t("set_text_help_img_emb_max_recall_count"),
                )
            else:
                config_img_embed_search_recall_result_per_db = 30

        config_webui_access_password = st.text_input(
            f'🔒 {_t("set_pwd_text")}', value=config.webui_access_password_md5, help=_t("set_pwd_help"), type="password"
        )

        # 选择语言
        lang_selection = list(lang_map.values())
        lang_index = lang_selection.index(lang_map[config.lang])

        language_option = st.selectbox(
            "🌎 Interface Language / 更改显示语言 / 表示言語を変更する",
            lang_selection,
            index=lang_index,
        )

        st.divider()

        if st.button(
            "Save and Apple All Change / 保存并应用所有更改",
            type="primary",
            key="SaveBtnGeneral",
        ):
            set_config_lang(language_option)
            config.set_and_save_config("enable_3_columns_in_oneday", config_enable_3_columns_in_oneday)
            config.set_and_save_config("max_page_result", config_max_search_result_num)
            # config.set_and_save_config("ocr_engine", config_ocr_engine)
            config.set_and_save_config("ocr_lang", config_ocr_lang)
            config.set_and_save_config("enable_img_embed_search", option_enable_img_embed_search)
            config.set_and_save_config("use_similar_ch_char_to_search", config_use_similar_ch_char_to_search)
            config.set_and_save_config("enable_synonyms_recommend", config_enable_synonyms_recommend)
            config.set_and_save_config("img_embed_search_recall_result_per_db", config_img_embed_search_recall_result_per_db)

            # 更改了一天之时缩略图相关选项时，清空缓存时间轴缩略图
            day_begin_minutes = find_value_in_tuple_timelist_by_str(
                list=day_begin_time_list, target=option_day_begin_time_oneday
            )
            if day_begin_minutes != config.day_begin_minutes or config_oneday_timeline_num != config.oneday_timeline_pic_num:
                file_utils.empty_directory(config.timeline_result_dir_ud)
            config.set_and_save_config("day_begin_minutes", day_begin_minutes)
            config.set_and_save_config("oneday_timeline_pic_num", config_oneday_timeline_num)

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

            # 如果有新密码输入，更改；如果留空，关闭功能
            if config_webui_access_password and config_webui_access_password != config.webui_access_password_md5:
                config.set_and_save_config(
                    "webui_access_password_md5", hashlib.md5(config_webui_access_password.encode("utf-8")).hexdigest()
                )
            elif len(config_webui_access_password) == 0:
                config.set_and_save_config("webui_access_password_md5", "")
            st.toast(_t("utils_toast_setting_saved"), icon="🦝")
            time.sleep(1)
            st.rerun()

    with col2b:
        st.empty()

    with col3b:
        # 关于
        # 从GitHub检查更新、添加提醒 - 位于设置页靠后的流程，以不打扰用户
        if "update_check" not in st.session_state:
            try:
                with st.spinner(_t("set_update_checking")):
                    new_version = utils.get_new_version_if_available()
                if new_version is not None:
                    st.session_state.update_info = _t("set_update_new").format(tool_version=new_version) + _t(
                        "set_update_changelog"
                    )
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

        about_markdown = (
            Path(f"{config.config_src_dir}\\about_{config.lang}.md")
            .read_text(encoding="utf-8")
            .format(
                version=__version__,
                update_info=st.session_state.update_info,
            )
        )
        st.markdown(about_markdown, unsafe_allow_html=True)


# 数据库的前置更新索引状态提示
def draw_db_status():
    count, nocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir_ud)
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
    elif config.OCR_index_strategy == 0:
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


# 检查配置使用的ocr语言，如果不在则设为可用的第一个
def legal_ocr_lang_index():
    os_support_lang_list = st.session_state.os_support_lang  # 获取系统支持的语言

    if config.ocr_lang in os_support_lang_list:  # 如果配置项在支持的列表中，返回索引值
        return os_support_lang_list.index(config.ocr_lang)
    else:  # 如果配置项不在支持的列表中，返回默认值，config设定为支持的第一项
        config.set_and_save_config("ocr_lang", os_support_lang_list[0])
        return 0


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


# 寻找配置项分钟数在 timelist 对应时间表达的 index
def find_index_in_tuple_timelist(list, target):
    for i in range(len(list)):
        if list[i][1] == target:
            return i
    return 0


# 根据输入 str，寻找 timelist 对应的分钟数
def find_value_in_tuple_timelist_by_str(list, target):
    for i in range(len(list)):
        if list[i][0] == target:
            return list[i][1]
    return 1
