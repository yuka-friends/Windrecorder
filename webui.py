import os
import time
import json
import datetime
from datetime import timedelta
from collections import OrderedDict
import subprocess
import threading
from pathlib import Path
import builtins
import base64
from io import BytesIO

import cv2
import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd
from PIL import Image
import pyautogui

from windrecorder.dbManager import DBManager
from windrecorder.oneday import OneDay
from windrecorder.config import config
import windrecorder.maintainManager as maintainManager
import windrecorder.utils as utils
import windrecorder.files as files
import windrecorder.record as record
import windrecorder.wordcloud as wordcloud
import windrecorder.state as state

update_button_key = "update_button"
reset_button_key = "setting_reset"

# python -m streamlit run webui.py

# 获取i18n表，调用方式为 d_lang[config.lang]["key"].format(var=var, var=var)
with open("config\\src\\languages.json", encoding='utf-8') as f:
    d_lang = json.load(f)
lang_map = d_lang['lang_map']


# 获取配置中语言选项是第几位；使设置选择项能匹配
def get_language_index(lang, data):
    for i, l in enumerate(data):
        if l == lang:
            return i
    return 1


lang_index = get_language_index(config.lang, d_lang)

st.set_page_config(
    page_title="Windrecord - webui",
    page_icon="🦝",
    layout="wide"
)


# 通过表内搜索结果定位视频时间码，展示视频
def show_n_locate_video_timestamp_by_df(df, num):
    # 入参：df，滑杆选择到表中的第几项
    if is_df_result_exist:
        # todo 获取有多少行结果 对num进行合法性判断
        videofile_path_month_dir = files.convert_vid_filename_as_YYYY_MM(df.iloc[num]['videofile_name'])  # 获取对应的日期目录
        videofile_path = os.path.join(config.record_videos_dir, videofile_path_month_dir,
                                      files.add_OCRED_suffix(df.iloc[num]['videofile_name']))
        videofile_path_COMPRESS = os.path.join(config.record_videos_dir, videofile_path_month_dir,
                                               files.add_COMPRESS_OCRED_suffix(df.iloc[num]['videofile_name']))
        print("webui: videofile_path: " + videofile_path)
        vid_timestamp = utils.calc_vid_inside_time(df, num)
        print("webui: vid_timestamp: " + str(vid_timestamp))

        st.session_state.vid_vid_timestamp = 0
        st.session_state.vid_vid_timestamp = vid_timestamp
        # st.session_state.vid_vid_timestamp
        # 判断视频文件是否存在
        if os.path.isfile(videofile_path):  # 是否存在未压缩的
            video_file = open(videofile_path, 'rb')
            video_bytes = video_file.read()
            with st.empty():
                st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
            st.markdown(f"`{videofile_path}`")
        elif os.path.isfile(videofile_path_COMPRESS):  # 是否存在已压缩的
            video_file = open(videofile_path_COMPRESS, 'rb')
            video_bytes = video_file.read()
            with st.empty():
                st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
            st.markdown(f"`{videofile_path_COMPRESS}`")
        else:
            st.warning(f"Video File **{videofile_path}** not on disk.", icon="🦫")


# 直接定位视频时间码、展示视频
def show_n_locate_video_timestamp_by_filename_n_time(video_file_name, timestamp):
    st.session_state.day_timestamp = int(timestamp)
    # 合并视频文件路径
    videofile_path_month_dir = files.convert_vid_filename_as_YYYY_MM(video_file_name)  # 获取对应的日期目录
    videofile_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, video_file_name)
    print("webui: videofile_path: " + videofile_path)
    # 打开并展示定位视频文件
    video_file = open(videofile_path, 'rb')
    video_bytes = video_file.read()
    with st.empty():
        st.video(video_bytes, start_time=st.session_state.day_timestamp)


# 检测是否初次使用工具，如果不存在数据库/数据库中只有一条数据，则判定为是
def check_is_onboarding():
    is_db_existed = DBManager().db_main_initialize()
    db_file_count = len(files.get_db_file_path_dict())
    if not is_db_existed:
        return True
    latest_db_records = DBManager().db_num_records()
    if latest_db_records == 1 and db_file_count == 1:
        return True
    return False


# 检测并渲染onboarding提示
def web_onboarding():
    # 状态懒加载
    if 'is_onboarding' not in st.session_state:
        st.session_state['is_onboarding'] = check_is_onboarding()

    if st.session_state.is_onboarding:
        # 数据库不存在，展示 Onboarding 提示
        st.success(d_lang[config.lang]["text_welcome_to_windrecorder"], icon="😺")
        intro_markdown = Path("config\\src\\onboarding_" + config.lang + ".md").read_text(encoding='utf-8')
        st.markdown(intro_markdown)
        st.divider()


# 选择播放视频的行数 的滑杆组件
def choose_search_result_num(df, is_df_result_exist):
    if is_df_result_exist == 1:
        # 如果结果只有一个，直接显示结果而不显示滑杆
        return 0
    elif not is_df_result_exist == 0:
        # shape是一个元组,索引0对应行数,索引1对应列数。
        total_raw = df.shape[0]
        # print("webui: total_raw:" + str(total_raw))

        slider_min_num_display = df.index.min()
        slider_max_num_display = df.index.max()
        select_num = slider_min_num_display

        # 使用滑杆选择视频
        col1, col2 = st.columns([5, 1])
        with col1:
            select_num = st.slider(d_lang[config.lang]["gs_slider_to_rewind_result"], slider_min_num_display,
                                   slider_max_num_display, select_num)
        with col2:
            select_num = st.number_input(d_lang[config.lang]["gs_slider_to_rewind_result"], label_visibility="hidden",
                                         min_value=slider_min_num_display,
                                         max_value=slider_max_num_display, value=select_num)

        select_num_real = select_num - slider_min_num_display  # 将绝对范围转换到从0开始的相对范围

        return select_num_real
    else:
        return 0


# 数据库的前置更新索引状态提示
def draw_db_status():
    count, nocred_count = files.get_videos_and_ocred_videos_count(config.record_videos_dir)
    timeCostStr = utils.estimate_indexing_time()
    if config.OCR_index_strategy == 1:
        # 启用自动索引
        if nocred_count == 1 and record.is_recording():
            st.success(
                d_lang[config.lang]["set_text_one_video_to_index"].format(nocred_count=nocred_count, count=count),
                icon='✅')
        elif nocred_count == 0:
            st.success(
                d_lang[config.lang]["set_text_no_video_need_index"].format(nocred_count=nocred_count, count=count),
                icon='✅')
        else:
            st.success(
                d_lang[config.lang]["set_text_some_video_will_be_index"].format(nocred_count=nocred_count, count=count),
                icon='✅')
    elif config.OCR_index_strategy == 2:
        if nocred_count == 1 and record.is_recording():
            st.success(
                d_lang[config.lang]["set_text_one_video_to_index"].format(nocred_count=nocred_count, count=count),
                icon='✅')
        elif nocred_count >= 1:
            st.warning(d_lang[config.lang]["set_text_video_not_index"].format(nocred_count=nocred_count, count=count,
                                                                              timeCostStr=timeCostStr), icon='🧭')
        else:
            st.success(
                d_lang[config.lang]["set_text_no_video_need_index"].format(nocred_count=nocred_count, count=count),
                icon='✅')


# 规范化的打表渲染组件
def draw_dataframe(df, heightIn=800):
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
            "ocr_text": st.column_config.TextColumn(
                "ocr_text",
                width="large"
            ),
            "thumbnail": st.column_config.ImageColumn(
                "thumbnail",
            )
        },
        height=heightIn
    )


# 显示时间轴
def render_daily_timeline_html(image_b64):
    st.markdown(
        f"<img style='max-width: 97%;max-height: 100%;margin: 0 0px 5px 50px' src='data:image/png;base64, {image_b64}'/>",
        unsafe_allow_html=True)


# 生成并显示每月数据量概览
def get_show_month_data_state(stat_select_month_datetime: datetime.datetime):
    if 'df_month_stat' not in st.session_state:  # 初始化显示的表状态
        st.session_state.df_month_stat = pd.DataFrame()
    if 'df_month_stat_dt' not in st.session_state:  # 初始化当前显示表的日期
        st.session_state.df_month_stat_dt = stat_select_month_datetime

    df_file_name = stat_select_month_datetime.strftime("%Y-%m") + "_month_data_state.csv"
    df_catch_dir = "catch"
    df_filepath = os.path.join(df_catch_dir, df_file_name)

    update_condition = False
    if not st.session_state.df_month_stat.empty and utils.set_full_datetime_to_YYYY_MM(
            st.session_state.df_month_stat_dt) <= utils.set_full_datetime_to_YYYY_MM(
        st.session_state.stat_select_month_datetime):
        update_condition = True

    if st.session_state.df_month_stat.empty or update_condition or utils.set_full_datetime_to_YYYY_MM(
            st.session_state.df_month_stat_dt) != utils.set_full_datetime_to_YYYY_MM(
        st.session_state.stat_select_month_datetime):  # 页面内无缓存，或不是当月日期

        # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):  # 存在
            if df_file_name[:7] == datetime.datetime.today().strftime("%Y-%m"):  # 如果是需要时效性的当下月数据
                if not files.is_file_modified_recently(df_filepath, time_gap=120):  # 超过120分钟未更新，过时 重新生成
                    # 更新操作
                    with st.spinner(d_lang[config.lang]["text_updating_month_stat"]):
                        st.session_state.df_month_stat = state.get_month_day_overview_scatter(
                            stat_select_month_datetime)
                        files.save_dataframe_to_path(st.session_state.df_month_stat, file_path=df_filepath)
            # 进行读取操作
            st.session_state.df_month_stat = files.read_dataframe_from_path(file_path=df_filepath)

        else:  # 磁盘上不存在缓存
            with st.spinner(d_lang[config.lang]["text_updating_month_stat"]):
                st.session_state.df_month_stat = state.get_month_day_overview_scatter(stat_select_month_datetime)
                files.save_dataframe_to_path(st.session_state.df_month_stat, file_path=df_filepath)

    st.scatter_chart(st.session_state.df_month_stat, x="day", y="hours", size="data_count", color="#AC79D5")


# 生成并显示每年数据量概览
def get_show_year_data_state(stat_select_year_datetime: datetime.datetime):
    if 'df_year_stat' not in st.session_state:  # 初始化显示的表状态
        st.session_state.df_year_stat = pd.DataFrame()

    df_file_name = stat_select_year_datetime.strftime("%Y") + "_year_data_state.csv"
    df_catch_dir = "catch"
    df_filepath = os.path.join(df_catch_dir, df_file_name)

    if st.session_state.df_year_stat.empty:  # 页面内无缓存

        # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):  # 存在
            if not files.is_file_modified_recently(df_filepath, time_gap=3000):  # 超过3000分钟未更新，过时 重新生成
                # 更新操作
                with st.spinner(d_lang[config.lang]["text_updating_yearly_stat"]):
                    st.session_state.df_year_stat = state.get_year_data_overview_scatter(stat_select_year_datetime)
                    files.save_dataframe_to_path(st.session_state.df_year_stat, file_path=df_filepath)
            else:
                # 未过时，进行读取操作
                st.session_state.df_year_stat = files.read_dataframe_from_path(file_path=df_filepath)

        else:  # 磁盘上不存在缓存
            with st.spinner(d_lang[config.lang]["text_updating_yearly_stat"]):
                st.session_state.df_year_stat = state.get_year_data_overview_scatter(stat_select_year_datetime)
                files.save_dataframe_to_path(st.session_state.df_year_stat, file_path=df_filepath)

    st.scatter_chart(st.session_state.df_year_stat, x="month", y="day", size="data_count", color="#C873A6", height=350)


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
        image_padding_refer_fade = Image.new('RGBA', (350, 200), (255, 233, 216, 100))  # 添加背景色蒙层
        image_padding_refer.paste(image_padding_refer_fade, (0, 0), image_padding_refer_fade)

    image_padding_refer_width, image_padding_refer_height = image_padding_refer.size
    topP_height = round(image_padding_refer_height * topP * 0.01)
    bottomP_height = round(image_padding_refer_height * bottomP * 0.01)
    leftP_width = round(image_padding_refer_width * leftP * 0.01)
    rightP_width = round(image_padding_refer_width * rightP * 0.01)

    image_color_area = Image.new('RGBA', (image_padding_refer_width, topP_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0), image_color_area)
    image_color_area = Image.new('RGBA', (image_padding_refer_width, bottomP_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, image_padding_refer_height - bottomP_height), image_color_area)
    image_color_area = Image.new('RGBA', (leftP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0), image_color_area)
    image_color_area = Image.new('RGBA', (rightP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (image_padding_refer_width - rightP_width, 0), image_color_area)

    return image_padding_refer


# 更改语言
def config_set_lang(lang_name):
    INVERTED_LANG_MAP = {v: k for k, v in lang_map.items()}
    lang_code = INVERTED_LANG_MAP.get(lang_name)

    if not lang_code:
        print(f"webui: Invalid language name: {lang_name}")
        return

    config.set_and_save_config('lang', lang_code)


# footer状态信息
def web_footer_state():
    # 懒加载，只在刷新时第一次获取
    if 'footer_first_record_time_int' not in st.session_state:
        st.session_state['footer_first_record_time_str'] = utils.seconds_to_date_goodlook_formart(
            DBManager().db_first_earliest_record_time())

    if 'footer_latest_record_time_str' not in st.session_state:
        st.session_state['footer_latest_record_time_str'] = utils.seconds_to_date_goodlook_formart(
            DBManager().db_latest_record_time())

    if 'footer_latest_db_records' not in st.session_state:
        st.session_state['footer_latest_db_records'] = DBManager().db_num_records()

    if 'footer_videos_file_size' not in st.session_state:
        st.session_state['footer_videos_file_size'] = round(
            files.get_dir_size(config.record_videos_dir) / (1024 * 1024 * 1024), 3)

    if 'footer_videos_files_count' not in st.session_state:
        st.session_state['footer_videos_files_count'], _ = files.get_videos_and_ocred_videos_count(
            config.record_videos_dir)

    # webUI draw
    st.divider()
    col1, col2 = st.columns([1, .3])
    with col1:
        st.markdown(d_lang[config.lang]["footer_info"].format(
            first_record_time_str=st.session_state.footer_first_record_time_str,
            latest_record_time_str=st.session_state.footer_latest_record_time_str,
            latest_db_records=st.session_state.footer_latest_db_records,
            videos_file_size=st.session_state.footer_videos_file_size,
            videos_files_count=st.session_state.footer_videos_files_count))
    with col2:
        st.markdown(f"<h2 align='right' style='color:rgba(0,0,0,.3)'> Windrecorder 🦝</h2>", unsafe_allow_html=True)


# 主界面_________________________________________________________
st.markdown(d_lang[config.lang]["main_title"])

tab1, tab2, tab3, tab4, tab5 = st.tabs([d_lang[config.lang]["tab_name_oneday"],
                                        d_lang[config.lang]["tab_name_search"],
                                        d_lang[config.lang]["tab_name_stat"],
                                        d_lang[config.lang]["tab_name_recording"],
                                        d_lang[config.lang]["tab_name_setting"]])

# TAB：今天也是一天
with tab1:
    # onboarding checking
    if check_is_onboarding():
        col1, col2 = st.columns([1, 2])
        with col1:
            web_onboarding()
        with col2:
            st.empty()

    # 标题 # todo:添加今天是星期几以增强时间观念

    # 日期选择器
    if 'day_date_input' not in st.session_state:
        st.session_state['day_date_input'] = datetime.date.today()
    # if 'day_time_select_slider' not in st.session_state:
    #     temp_dt_now = time = datetime.datetime.now() - datetime.timedelta(seconds=5)
    #     st.session_state.day_time_select_slider =temp_dt_now.time()

    col1, col2, col3, col4, col5, col6, col7 = st.columns([.4, .25, .25, .15, .25, .2, 1])
    with col1:
        st.markdown(d_lang[config.lang]["oneday_title"])
    with col2:
        if st.button(d_lang[config.lang]["oneday_btn_yesterday"], use_container_width=True):
            st.session_state.day_date_input -= datetime.timedelta(days=1)
    with col3:
        if st.button(d_lang[config.lang]["oneday_btn_tomorrow"], use_container_width=True):
            st.session_state.day_date_input += datetime.timedelta(days=1)
    with col4:
        if st.button(d_lang[config.lang]["oneday_btn_today"], use_container_width=True):
            st.session_state.day_date_input = datetime.date.today()
    with col5:
        st.session_state.day_date_input = st.date_input("Today Date", label_visibility="collapsed",
                                                        value=st.session_state.day_date_input)

        # 获取输入的日期
        # 清理格式到HMS
        dt_in = datetime.datetime(st.session_state.day_date_input.year, st.session_state.day_date_input.month,
                                  st.session_state.day_date_input.day, 0, 0, 0)
        # 检查数据库中关于今天的数据
        day_has_data, day_noocred_count, day_search_result_num, day_min_timestamp_dt, day_max_timestamp_dt, day_df = OneDay().checkout(
            dt_in)
    with col6:
        st.empty()
    with col7:
        # 初始化时间线滑杆启用状态，这个状态同时用来判断是否启用搜索功能，如果True则启用
        if 'day_time_slider_disable' not in st.session_state:
            st.session_state['day_time_slider_disable'] = False

        # 关键词搜索组件
        if 'day_search_query_page_index' not in st.session_state:
            st.session_state['day_search_query_page_index'] = 0

        col1c, col2c, col3c, col4c, col5c = st.columns([1, 1.5, 1, 1, .5])
        with col1c:
            if st.toggle(d_lang[config.lang]["oneday_toggle_search"],
                         help=d_lang[config.lang]["oneday_toggle_search_help"]):
                st.session_state.day_time_slider_disable = True
                st.session_state.day_is_search_data = True
            else:
                st.session_state.day_time_slider_disable = False
                st.session_state.day_is_search_data = False
        with col2c:
            # 搜索框

            # 懒加载，输入不变时节省性能
            if 'df_day_search_result' not in st.session_state:
                st.session_state.df_day_search_result = pd.DataFrame()
            if 'day_search_keyword' not in st.session_state:
                st.session_state.day_search_keyword = None
            if 'day_search_keyword_lazy' not in st.session_state:
                st.session_state.day_search_keyword_lazy = None


            def do_day_keyword_search():
                # 搜索前清除状态
                st.session_state.day_search_result_index_num = 0  # 条目检索

                if st.session_state.day_search_keyword_lazy != st.session_state.day_search_keyword:
                    st.session_state.day_search_keyword_lazy = st.session_state.day_search_keyword
                    st.session_state.df_day_search_result = OneDay().search_day_data(
                        utils.complete_datetime(st.session_state.day_date_input),
                        search_content=st.session_state.day_search_keyword)


            st.session_state.day_search_keyword = st.text_input(d_lang[config.lang]["text_search_keyword"], 'Keyword',
                                                                key=2, label_visibility="collapsed",
                                                                on_change=do_day_keyword_search(),
                                                                disabled=not st.session_state.day_time_slider_disable)
            # 执行搜索，搜索结果
            # df_day_search_result = OneDay().search_day_data(utils.complete_datetime(st.session_state.day_date_input),search_content=st.session_state.day_search_keyword)
        with col3c:
            # 结果条目数
            if st.session_state.day_is_search_data:
                # 启用了搜索功能
                if st.session_state.df_day_search_result.empty:
                    st.markdown(d_lang[config.lang]["oneday_search_md_none"], unsafe_allow_html=True)
                else:
                    result_num = st.session_state.df_day_search_result.shape[0]
                    st.markdown(d_lang[config.lang]["oneday_search_md_result"].format(result_num=result_num),
                                unsafe_allow_html=True)
            else:
                st.empty()
        with col4c:
            # 翻页器
            if st.session_state.df_day_search_result.empty:
                st.empty()
            else:
                def update_slider(dt):
                    # 翻页结果时刷新控制时间滑杆的定位；入参：需要被定位的datetime.time
                    if st.session_state.day_is_search_data:
                        st.session_state.day_time_select_slider = dt


                # 初始化值
                if 'day_search_result_index_num' not in st.session_state:
                    st.session_state['day_search_result_index_num'] = 0
                # 翻页控件
                st.session_state.day_search_result_index_num = st.number_input(
                    "PageIndex",
                    value=0,
                    min_value=0,
                    max_value=st.session_state.df_day_search_result.shape[0] - 1,
                    label_visibility="collapsed",
                    disabled=not st.session_state.day_time_slider_disable,
                    on_change=update_slider(utils.set_full_datetime_to_day_time(utils.seconds_to_datetime(
                        st.session_state.df_day_search_result.loc[
                            st.session_state.day_search_result_index_num, 'videofile_time'])))
                )
        with col5c:
            st.button(label="⟳",
                      use_container_width=True
                      )

    # 判断数据库中有无今天的数据，有则启用功能：
    if day_has_data:

        # 准备词云与时间轴（timeline）所需要的文件命名规范与变量，文件名用同一种命名方式，但放到不同的路径下
        real_today_day_cloud_n_TL_img_name = str(datetime.datetime.today().strftime("%Y-%m-%d")) + "-today-.png"
        # real_today_day_cloud_n_TL_img_name = str(datetime.datetime.today().date().year) + "-" + str(datetime.datetime.today().date().month) + "-" + str(datetime.datetime.today().date().day) + "-today-.png"
        if st.session_state.day_date_input == datetime.datetime.today().date():
            # 如果是今天的结果，以-today结尾，以使次日回溯时词云能被自动更新
            # current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + "-today-" + ".png"
            current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + "-today-.png"
            # 太邪门了，.png前不能是alphabet/数字字符，否则词云的.to_file会莫名其妙自己多添加一个.png
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_day_cloud_n_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir, current_day_cloud_n_TL_img_name)
        else:
            # current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + ".png"
            current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + ".png"
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_day_cloud_n_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir, current_day_cloud_n_TL_img_name)

        # 时间滑动控制杆
        start_time = datetime.time(day_min_timestamp_dt.hour, day_min_timestamp_dt.minute)
        end_time = datetime.time(day_max_timestamp_dt.hour, day_max_timestamp_dt.minute)
        st.session_state.day_time_select_24h = st.slider("Time Rewind", label_visibility="collapsed",
                                                         min_value=start_time, max_value=end_time, value=end_time,
                                                         step=timedelta(seconds=30),
                                                         disabled=st.session_state.day_time_slider_disable,
                                                         key="day_time_select_slider")


        # 展示时间轴缩略图
        def update_day_timeline_thumbnail():
            with st.spinner(d_lang[config.lang]["oneday_text_generate_timeline_thumbnail"]):
                if OneDay().generate_preview_timeline_img(st.session_state.day_date_input,
                                                          img_saved_name=current_day_cloud_n_TL_img_name):
                    return True
                else:
                    return False


        get_generate_result = True
        if not os.path.exists(current_day_TL_img_path):
            # 如果时间轴缩略图不存在，创建之
            get_generate_result = update_day_timeline_thumbnail()
            # 移除非今日的-today.png
            for filename in os.listdir(config.timeline_result_dir):
                if filename.endswith("-today-.png") and filename != real_today_day_cloud_n_TL_img_name:
                    file_path = os.path.join(config.timeline_result_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"webui: Deleted file: {file_path}")
                    except Exception as e:
                        print(f"webui: {e}")
        elif current_day_TL_img_path.endswith("-today-.png"):
            # 如果已存在今日的，重新生成覆盖更新
            if not files.is_file_modified_recently(current_day_TL_img_path):
                # 如果修改日期超过30分钟则更新
                get_generate_result = update_day_timeline_thumbnail()

        # 展示时间轴缩略图
        if get_generate_result:
            image_thumbnail = Image.open(current_day_TL_img_path)
            render_daily_timeline_html(utils.image_to_base64(current_day_TL_img_path))
            # st.image(image_thumbnail,use_column_width="always")
        else:
            st.markdown(d_lang[config.lang]["oneday_md_no_enough_thunmbnail_for_timeline"], unsafe_allow_html=True)

        # 可视化数据时间轴
        # day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df = day_df, start = day_min_timestamp_dt.hour, end = day_max_timestamp_dt.hour+1)
        day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df=day_df, start_dt=day_min_timestamp_dt,
                                                                            end_dt=day_max_timestamp_dt)
        st.area_chart(day_chart_data_overview, x="hour", y="data", use_container_width=True, height=100,
                      color="#AC79D5")

        # 初始化懒加载状态
        if 'catch_videofile_ondisk_list_oneday' not in st.session_state:  # 减少io查询，预拿视频文件列表供比对是否存在
            st.session_state.catch_videofile_ondisk_list_oneday = files.get_file_path_list(config.record_videos_dir)

        # 视频展示区域
        col1a, col2a, col3a = st.columns([1, 3, 1])
        with col1a:
            # 居左部分
            if st.session_state.day_is_search_data and not st.session_state.df_day_search_result.empty:
                # 如果是搜索视图，这里展示全部的搜索结果
                df_day_search_result_refine = DBManager().db_refine_search_data_day(
                    st.session_state.df_day_search_result,
                    catch_videofile_ondisk_list=st.session_state.catch_videofile_ondisk_list_oneday)  # 优化下数据展示
                draw_dataframe(df_day_search_result_refine)
            else:
                # # 时间轴拖动视图 - 切换前后视频片段
                # # 初始化状态
                # if 'btn_last_vid_disable' not in st.session_state:
                #     st.session_state['btn_last_vid_disable'] = False
                # if 'btn_next_vid_disable' not in st.session_state:
                #     st.session_state['btn_next_vid_disable'] = False
                # if 'all_video_filepath_dict' not in st.session_state:   # 获取所有视频的文件-dt词典
                #     st.session_state['all_video_filepath_dict'] = files.get_videofile_path_dict_datetime(files.get_videofile_path_list_by_time_range(files.get_file_path_list(config.record_videos_dir)))
                # if 'timeline_select_dt' not in st.session_state:   # 当前选择的时间
                #     st.session_state['timeline_select_dt'] = utils.merge_date_day_datetime_together(st.session_state.day_date_input,st.session_state.day_time_select_24h) #合并时间为datetime

                # # 找到最近的上一项/下一项时间
                # def find_closest_dict_key(sorted_dict, target_datetime, return_mode = 'last'):
                #     closest_datetime = None

                #     for key, value in sorted_dict.items():
                #         if return_mode == 'last':
                #             if value < target_datetime:
                #                 closest_datetime = value
                #         elif return_mode == 'next':
                #             if value > target_datetime:
                #                 closest_datetime = value
                #         else:
                #             break

                #     if closest_datetime is not None:
                #         closest_datetime = closest_datetime + datetime.timedelta(seconds=1)
                #     return closest_datetime

                # # 切换到上个视频片段
                # def switch_to_last_vid():
                #     new_datetime_select = find_closest_dict_key(st.session_state.all_video_filepath_dict, st.session_state.timeline_select_dt, return_mode='last')
                #     if new_datetime_select is None:
                #         st.session_state.btn_last_vid_disable = True
                #         st.session_state.btn_next_vid_disable = False
                #     else:
                #         st.session_state.day_time_slider_disable = True
                #         st.session_state.day_date_input = utils.set_full_datetime_to_YYYY_MM_DD(new_datetime_select)
                #         st.session_state.day_time_select_24h = utils.set_full_datetime_to_day_time(new_datetime_select)
                #         st.session_state.timeline_select_dt = utils.merge_date_day_datetime_together(st.session_state.day_date_input,st.session_state.day_time_select_24h) # 更新时间
                #     return

                # # 切换到下个视频片段
                # def switch_to_next_vid():
                #     new_datetime_select = find_closest_dict_key(st.session_state.all_video_filepath_dict, st.session_state.timeline_select_dt, return_mode='next')
                #     if new_datetime_select is None:
                #         st.session_state.btn_last_vid_disable = False
                #         st.session_state.btn_next_vid_disable = True
                #     else:
                #         st.session_state.day_time_slider_disable = True
                #         st.session_state.day_date_input = utils.set_full_datetime_to_YYYY_MM_DD(new_datetime_select)
                #         st.session_state.day_time_select_24h = utils.set_full_datetime_to_day_time(new_datetime_select)
                #         st.session_state.timeline_select_dt = utils.merge_date_day_datetime_together(st.session_state.day_date_input,st.session_state.day_time_select_24h) # 更新时间
                #     return

                # col1_switchvid, col2_switchvid = st.columns([1,1])
                # with col1_switchvid:
                #     st.button("← 上个视频片段", use_container_width=True, disabled=st.session_state.btn_last_vid_disable, on_click=switch_to_last_vid)
                # with col2_switchvid:
                #     st.button("下个视频片段 →", use_container_width=True, disabled=st.session_state.btn_next_vid_disable, on_click=switch_to_next_vid)

                # st.session_state.day_date_input
                # st.session_state.day_time_select_24h
                # st.session_state.timeline_select_dt
                st.empty()

        with col2a:
            # 居中部分：视频结果显示区域
            if st.session_state.day_is_search_data and not st.session_state.df_day_search_result.empty:
                # 【搜索功能】
                # 获取关键词，搜索出所有结果的dt，然后使用上下翻页来定位，定位后展示对应的视频
                day_is_video_ondisk, day_video_file_name, shown_timestamp = OneDay().get_result_df_video_time(
                    st.session_state.df_day_search_result, st.session_state.day_search_result_index_num)
                if day_is_video_ondisk:
                    show_n_locate_video_timestamp_by_filename_n_time(day_video_file_name, shown_timestamp)
                    st.markdown(d_lang[config.lang]["oneday_md_rewinding_video_name"].format(
                        day_video_file_name=day_video_file_name))
                else:
                    st.info(d_lang[config.lang]["oneday_text_not_found_vid_but_has_data"], icon="🎐")
                    found_row = st.session_state.df_day_search_result.loc[
                        st.session_state.day_search_result_index_num].to_frame().T
                    found_row = DBManager().db_refine_search_data_day(found_row,
                                                                      catch_videofile_ondisk_list=st.session_state.catch_videofile_ondisk_list_oneday)  # 优化下数据展示
                    draw_dataframe(found_row, heightIn=0)

            else:
                # 【时间线速查功能】
                # 获取选择的时间，查询对应时间下有无视频，有则换算与定位
                day_full_select_datetime = utils.merge_date_day_datetime_together(st.session_state.day_date_input,
                                                                                  st.session_state.day_time_select_24h)  # 合并时间为datetime
                day_is_result_exist, day_video_file_name = OneDay().find_closest_video_by_filesys(
                    day_full_select_datetime)  # 通过文件查询
                # 计算换算用于播放视频的时间

                if day_is_result_exist:
                    # 换算时间、定位播放视频
                    vidfile_timestamp = utils.calc_vid_name_to_timestamp(day_video_file_name)
                    select_timestamp = utils.datetime_to_seconds(day_full_select_datetime)
                    shown_timestamp = select_timestamp - vidfile_timestamp
                    show_n_locate_video_timestamp_by_filename_n_time(day_video_file_name, shown_timestamp)
                    st.markdown(d_lang[config.lang]["oneday_md_rewinding_video_name"].format(
                        day_video_file_name=day_video_file_name))
                else:
                    # 没有对应的视频，查一下有无索引了的数据
                    is_data_found, found_row = OneDay().find_closest_video_by_database(day_df,
                                                                                       utils.datetime_to_seconds(
                                                                                           day_full_select_datetime))
                    if is_data_found:
                        st.info(d_lang[config.lang]["oneday_text_not_found_vid_but_has_data"], icon="🎐")
                        found_row = DBManager().db_refine_search_data_day(found_row,
                                                                          catch_videofile_ondisk_list=st.session_state.catch_videofile_ondisk_list_oneday)  # 优化下数据展示
                        draw_dataframe(found_row, heightIn=0)
                    else:
                        # 如果是当天第一次打开但数据库正在索引因而无法访问
                        if st.session_state.day_date_input == utils.set_full_datetime_to_YYYY_MM_DD(
                                datetime.datetime.today()) and utils.is_maintain_lock_file_valid():
                            st.warning(d_lang[config.lang]["oneday_text_data_indexing_wait_and_refresh"], icon="🦫")
                        else:
                            st.warning(d_lang[config.lang]["oneday_text_no_found_record_and_vid_on_disk"], icon="🦫")

        with col3a:
            if config.show_oneday_wordcloud:
                # 是否展示当天词云
                def update_day_word_cloud():
                    with st.spinner(d_lang[config.lang]["oneday_text_generate_word_cloud"]):
                        day_input_datetime_finetune = datetime.datetime(st.session_state.day_date_input.year,
                                                                        st.session_state.day_date_input.month,
                                                                        st.session_state.day_date_input.day, 0, 0, 2)
                        wordcloud.generate_word_cloud_in_day(utils.datetime_to_seconds(day_input_datetime_finetune),
                                                             img_save_name=current_day_cloud_n_TL_img_name)


                if not os.path.exists(current_day_cloud_img_path):
                    # 如果词云不存在，创建之
                    update_day_word_cloud()
                    # 移除非今日的-today.png
                    for filename in os.listdir(config.wordcloud_result_dir):
                        if filename.endswith("-today-.png") and filename != real_today_day_cloud_n_TL_img_name:
                            file_path = os.path.join(config.wordcloud_result_dir, filename)
                            os.remove(file_path)
                            print(f"webui: Deleted file: {file_path}")

                # 展示词云
                try:
                    image = Image.open(current_day_cloud_img_path)
                    st.image(image)
                except Exception as e:
                    st.exception(d_lang[config.lang]["text_cannot_open_img"] + e)


                def update_wordcloud_btn_clicked():
                    st.session_state.update_wordcloud_button_disabled = True


                if st.button(d_lang[config.lang]["oneday_btn_update_word_cloud"], key="refresh_day_cloud",
                             use_container_width=True,
                             disabled=st.session_state.get("update_wordcloud_button_disabled", False),
                             on_click=update_wordcloud_btn_clicked):
                    try:
                        update_day_word_cloud()
                    except Exception as ex:
                        st.exception(ex)
                    finally:
                        st.session_state.update_wordcloud_button_disabled = False
                        st.experimental_rerun()
            else:
                st.markdown(d_lang[config.lang]["oneday_md_word_cloud_turn_off"], unsafe_allow_html=True)


    else:
        # 数据库中没有今天的记录
        # 判断videos下有无今天的视频文件
        if files.find_filename_in_dir("videos", utils.datetime_to_dateDayStr(dt_in)):
            st.info(d_lang[config.lang]["oneday_text_has_vid_but_not_index"], icon="📎")
        else:
            st.info(d_lang[config.lang]["oneday_text_vid_and_data_not_found"], icon="🎐")

# tab：全局关键词搜索
if 'db_global_search_result' not in st.session_state:
    st.session_state['db_global_search_result'] = pd.DataFrame()
# db_global_search_result = pd.DataFrame()
with tab2:
    col1, col2 = st.columns([1, 2])
    with col1:
        # 初始化一些全局状态
        if 'max_page_count' not in st.session_state:
            st.session_state.max_page_count = 1
        if 'all_result_counts' not in st.session_state:
            st.session_state.all_result_counts = 1
        if 'search_content' not in st.session_state:
            st.session_state.search_content = ""
        if 'search_content_exclude' not in st.session_state:
            st.session_state.search_content_exclude = ""
        if 'search_date_range_in' not in st.session_state:
            st.session_state.search_date_range_in = datetime.datetime.today() - datetime.timedelta(seconds=86400)
        if 'search_date_range_out' not in st.session_state:
            st.session_state.search_date_range_out = datetime.datetime.today()
        if 'catch_videofile_ondisk_list' not in st.session_state:  # 减少io查询，预拿视频文件列表供比对是否存在
            st.session_state.catch_videofile_ondisk_list = files.get_file_path_list(config.record_videos_dir)

        col1_gstype, col2_gstype = st.columns([10, 1])
        with col1_gstype:
            st.markdown(d_lang[config.lang]["gs_md_search_title"])
        with col2_gstype:
            # st.selectbox("搜索方式", ('关键词匹配','模糊语义搜索 [不可用]','画面内容搜索 [不可用]'),label_visibility="collapsed")
            if not wordcloud.check_if_word_lexicon_empty():
                if st.button("🎲", use_container_width=True, help=d_lang[config.lang]["gs_text_randomwalk"]):
                    try:
                        st.session_state.search_content = utils.get_random_word_from_lexicon()
                    except Exception as e:
                        print(e)
                        st.session_state.search_content = ""
            st.empty()

        web_onboarding()

        # 时间搜索范围组件（懒加载）
        if 'search_latest_record_time_int' not in st.session_state:
            st.session_state['search_latest_record_time_int'] = DBManager().db_latest_record_time()
        if 'search_earlist_record_time_int' not in st.session_state:
            st.session_state['search_earlist_record_time_int'] = DBManager().db_first_earliest_record_time()

        # 优化streamlit强加载机制导致的索引时间：改变了再重新搜索，而不是每次提交了更改都进行搜索
        if 'search_content_lazy' not in st.session_state:
            st.session_state.search_content_lazy = ""
        if 'search_content_exclude_lazy' not in st.session_state:
            st.session_state.search_content_exclude_lazy = None
        if 'search_date_range_in_lazy' not in st.session_state:
            st.session_state.search_date_range_in_lazy = datetime.datetime(1970, 1, 2) + datetime.timedelta(
                seconds=st.session_state.search_earlist_record_time_int) - datetime.timedelta(seconds=86400)
        if 'search_date_range_out_lazy' not in st.session_state:
            st.session_state.search_date_range_out_lazy = datetime.datetime(1970, 1, 2) + datetime.timedelta(
                seconds=st.session_state.search_latest_record_time_int) - datetime.timedelta(seconds=86400)


        # 获得全局搜索结果
        def do_global_keyword_search():
            # 如果搜索所需入参状态改变了，进行搜索
            if (
                    st.session_state.search_content_lazy == st.session_state.search_content
                    and st.session_state.search_content_exclude_lazy == st.session_state.search_content_exclude
                    and st.session_state.search_date_range_in_lazy == st.session_state.search_date_range_in
                    and st.session_state.search_date_range_out_lazy == st.session_state.search_date_range_out
            ):
                return

            st.session_state.search_content_lazy = st.session_state.search_content
            st.session_state.search_content_exclude_lazy = st.session_state.search_content_exclude
            st.session_state.search_date_range_in_lazy = st.session_state.search_date_range_in
            st.session_state.search_date_range_out_lazy = st.session_state.search_date_range_out

            # 清理状态
            st.session_state.page_index = 1

            st.session_state.db_global_search_result, st.session_state.all_result_counts, st.session_state.max_page_count = DBManager().db_search_data(
                st.session_state.search_content,
                st.session_state.search_date_range_in,
                st.session_state.search_date_range_out,
                keyword_input_exclude=st.session_state.search_content_exclude)


        col1a, col2a, col3a, col4a = st.columns([2, 1, 2, 1])
        with col1a:
            st.session_state.search_content = st.text_input(d_lang[config.lang]["text_search_keyword"],
                                                            help="可使用空格分隔多个关键词。")

            do_global_keyword_search()
        with col2a:
            st.session_state.search_content_exclude = st.text_input(d_lang[config.lang]["gs_input_exclude"], "",
                                                                    help=d_lang[config.lang]["gs_input_exclude_help"])
            do_global_keyword_search()
        with col3a:

            try:
                st.session_state.search_date_range_in, st.session_state.search_date_range_out = st.date_input(
                    d_lang[config.lang]["text_search_daterange"],
                    (datetime.datetime(1970, 1, 2)
                     + datetime.timedelta(seconds=st.session_state.search_earlist_record_time_int)
                     - datetime.timedelta(seconds=86400),
                     datetime.datetime(1970, 1, 2)
                     + datetime.timedelta(seconds=st.session_state.search_latest_record_time_int)
                     - datetime.timedelta(seconds=86400)
                     ),
                    format="YYYY-MM-DD"
                )
                do_global_keyword_search()
            except:
                st.warning(d_lang[config.lang]["gs_text_pls_choose_full_date_range"])

        with col4a:
            # 结果翻页器
            st.session_state.page_index = st.number_input(d_lang[config.lang]["gs_input_result_page"], min_value=1,
                                                          step=1, max_value=st.session_state.max_page_count + 1)

        # 进行搜索
        if not len(st.session_state.search_content) == 0:
            timeCost_globalSearch = time.time()  # 预埋计算实际时长

            df = DBManager().db_search_data_page_turner(st.session_state.db_global_search_result,
                                                        st.session_state.page_index)

            is_df_result_exist = len(df)

            st.markdown(d_lang[config.lang]["gs_md_search_result_stat"].format(
                all_result_counts=st.session_state.all_result_counts, max_page_count=st.session_state.max_page_count,
                search_content=st.session_state.search_content, timeCost=timeCost_globalSearch))

            # 滑杆选择
            result_choose_num = choose_search_result_num(df, is_df_result_exist)

            if len(df) == 0:
                st.info(
                    d_lang[config.lang]["text_search_not_found"].format(search_content=st.session_state.search_content),
                    icon="🎐")
            else:
                # 打表
                df = DBManager().db_refine_search_data_global(df,
                                                              catch_videofile_ondisk_list=st.session_state.catch_videofile_ondisk_list)  # 优化数据显示
                draw_dataframe(df, heightIn=800)

            timeCost_globalSearch = round(time.time() - timeCost_globalSearch, 5)
            st.markdown(d_lang[config.lang]["gs_md_search_result_below"].format(timecost=timeCost_globalSearch))

        else:
            st.info(d_lang[config.lang]["gs_text_intro"])

    with col2:
        # 选择视频
        if not len(st.session_state.search_content) == 0:
            show_n_locate_video_timestamp_by_df(df, result_choose_num)
        else:
            st.empty()

# tab: 记忆摘要
with tab3:
    col1, col2 = st.columns([1, 2])
    with col1:
        # 懒加载
        if 'stat_db_earliest_datetime' not in st.session_state:
            st.session_state['stat_db_earliest_datetime'] = utils.seconds_to_datetime(
                DBManager().db_first_earliest_record_time())
        if 'stat_db_latest_datetime' not in st.session_state:
            st.session_state['stat_db_latest_datetime'] = utils.seconds_to_datetime(DBManager().db_latest_record_time())

        if st.session_state.stat_db_latest_datetime.year > st.session_state.stat_db_earliest_datetime.year:
            # 当记录时间超过一年
            selector_month_min = 1
            selector_month_max = 12
        else:
            selector_month_min = st.session_state.stat_db_earliest_datetime.month
            selector_month_max = st.session_state.stat_db_latest_datetime.month

        st.markdown(d_lang[config.lang]["stat_md_month_title"])
        col1a, col2a, col3a = st.columns([.5, .5, 1])
        with col1a:
            st.session_state.Stat_query_Year = st.number_input(label="Stat_query_Year",
                                                               min_value=st.session_state.stat_db_earliest_datetime.year,
                                                               max_value=st.session_state.stat_db_latest_datetime.year,
                                                               value=st.session_state.stat_db_latest_datetime.year,
                                                               label_visibility="collapsed")
        with col2a:
            st.session_state.Stat_query_Month = st.number_input(label="Stat_query_Month", min_value=selector_month_min,
                                                                max_value=selector_month_max,
                                                                value=st.session_state.stat_db_latest_datetime.month,
                                                                label_visibility="collapsed")
        with col3a:
            st.empty()

        st.session_state.stat_select_month_datetime = datetime.datetime(st.session_state.Stat_query_Year,
                                                                        st.session_state.Stat_query_Month, 1, 10, 0, 0)
        get_show_month_data_state(st.session_state.stat_select_month_datetime)  # 显示当月概览

        stat_year_title = st.session_state.stat_select_month_datetime.year
        st.markdown(d_lang[config.lang]["stat_md_year_title"].format(stat_year_title=stat_year_title))
        get_show_year_data_state(st.session_state.stat_select_month_datetime)  # 显示当年概览

    with col2:
        st.markdown(d_lang[config.lang]["stat_md_memory_title"])

        col1_mem, col2_mem = st.columns([1, 1])
        with col1_mem:
            current_month_cloud_img_name = str(st.session_state.Stat_query_Year) + "-" + str(
                st.session_state.Stat_query_Month) + ".png"
            current_month_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_month_cloud_img_name)

            if st.button(d_lang[config.lang]["stat_btn_generate_update_word_cloud"]):
                with st.spinner(d_lang[config.lang]["stat_text_generating_word_cloud"]):
                    wordcloud.generate_word_cloud_in_month(
                        utils.datetime_to_seconds(st.session_state.stat_select_month_datetime),
                        current_month_cloud_img_name)

            if os.path.exists(current_month_cloud_img_path):
                image = Image.open(current_month_cloud_img_path)
                st.image(image, caption=current_month_cloud_img_path)
            else:
                st.info(d_lang[config.lang]["stat_text_no_month_word_cloud_pic"])

        with col2_mem:
            current_month_lightbox_img_name = str(st.session_state.Stat_query_Year) + "-" + str(
                st.session_state.Stat_query_Month) + ".png"
            current_month_lightbox_img_path = os.path.join(config.lightbox_result_dir, current_month_lightbox_img_name)

            if st.button(d_lang[config.lang]["stat_btn_generate_lightbox"]):
                with st.spinner(d_lang[config.lang]["stat_text_generating_lightbox"]):
                    state.generate_month_lightbox(st.session_state.stat_select_month_datetime,
                                                  img_saved_name=current_month_lightbox_img_name)

            if os.path.exists(current_month_lightbox_img_path):
                image = Image.open(current_month_lightbox_img_path)
                st.image(image, caption=current_month_lightbox_img_path)
            else:
                st.info(d_lang[config.lang]["stat_text_no_month_lightbox"])

with tab4:
    st.markdown(d_lang[config.lang]["rs_md_title"])

    col1c, col2c, col3c = st.columns([1, .5, 1.5])
    with col1c:
        st.info(d_lang[config.lang]["rs_text_need_to_restart_after_save_setting"])


        # 手动检查录屏服务有无进行中

        # 管理刷新服务的按钮状态：手动管理状态，cover fix streamlit只能读按钮是否被按下的问题（一旦有其他按钮按下，其他按钮就会回弹导致持续的逻辑重置、重新加载）
        def update_record_service_btn_clicked():
            st.session_state.update_btn_dis_record = True


        if 'update_btn_refresh_press' not in st.session_state:
            st.session_state.update_btn_refresh_press = False


        def update_record_btn_state():
            if st.session_state.update_btn_refresh_press:
                st.session_state.update_btn_refresh_press = False
            else:
                st.session_state.update_btn_refresh_press = True
            st.session_state.update_btn_dis_record = False


        btn_refresh = st.button(d_lang[config.lang]["rs_btn_check_record_stat"], on_click=update_record_btn_state)

        if st.session_state.update_btn_refresh_press:

            if record.is_recording():
                st.success(d_lang[config.lang]["rs_text_recording_screen_now"], icon="🦚")
                # stop_record_btn = st.button('停止录制屏幕', type="secondary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                # if stop_record_btn:
                #     st.toast("正在结束录屏进程……")
                #     utils.kill_recording()

            else:
                st.error(d_lang[config.lang]["rs_text_not_recording_screen"], icon="🦫")
                start_record_btn = st.button(d_lang[config.lang]["rs_btn_start_record"], type="primary",
                                             disabled=st.session_state.get("update_btn_dis_record", False),
                                             on_click=update_record_service_btn_clicked)
                if start_record_btn:
                    os.startfile('start_record.bat', 'open')
                    st.toast(d_lang[config.lang]["rs_text_starting_record"])
                    st.session_state.update_btn_refresh_press = False

        # st.warning("录制服务已启用。当前暂停录制屏幕。",icon="🦫")
        st.divider()
        st.markdown(d_lang[config.lang]["rs_md_record_setting_title"])

        col1_record, col2_record = st.columns([1, 1])
        with col1_record:
            if 'is_create_startup_shortcut' not in st.session_state:
                st.session_state.is_create_startup_shortcut = record.is_file_already_in_startup('start_record.bat.lnk')
            st.session_state.is_create_startup_shortcut = st.checkbox(
                d_lang[config.lang]["rs_checkbox_start_record_when_startup"],
                value=record.is_file_already_in_startup('start_record.bat.lnk'),
                on_change=record.create_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut),
                help=d_lang[config.lang]["rs_checkbox_start_record_when_startup_help"])

        with col2_record:
            st.markdown(d_lang[config.lang]["rs_md_only_support_main_monitor"], unsafe_allow_html=True)

        screentime_not_change_to_pause_record = st.number_input(
            d_lang[config.lang]["rs_input_stop_recording_when_screen_freeze"],
            value=config.screentime_not_change_to_pause_record, min_value=0)

        st.divider()

        # 自动化维护选项 WIP
        st.markdown(d_lang[config.lang]["set_md_auto_maintain"])
        ocr_strategy_option_dict = {
            d_lang[config.lang]["rs_text_ocr_manual_update"]: 0,
            d_lang[config.lang]["rs_text_ocr_auto_update"]: 1
        }
        ocr_strategy_option = st.selectbox(d_lang[config.lang]["rs_selectbox_ocr_strategy"],
                                           (list(ocr_strategy_option_dict.keys())),
                                           index=config.OCR_index_strategy
                                           )

        col1d, col2d, col3d = st.columns([1, 1, 1])
        with col1d:
            vid_store_day = st.number_input(d_lang[config.lang]["set_input_video_hold_days"], min_value=0,
                                            value=config.vid_store_day,
                                            help=d_lang[config.lang]["rs_input_vid_store_time_help"])
        with col2d:
            vid_compress_day = st.number_input(d_lang[config.lang]["rs_input_vid_compress_time"],
                                               value=config.vid_compress_day, min_value=0,
                                               help=d_lang[config.lang]["rs_input_vid_compress_time_help"])
        with col3d:
            video_compress_selectbox_dict = {'0.75': 0, '0.5': 1, '0.25': 2}
            video_compress_rate_selectbox = st.selectbox(d_lang[config.lang]["rs_selectbox_compress_ratio"],
                                                         list(video_compress_selectbox_dict.keys()),
                                                         index=video_compress_selectbox_dict[
                                                             config.video_compress_rate],
                                                         help=d_lang[config.lang]["rs_selectbox_compress_ratio_help"])

        st.divider()

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary", key="SaveBtnRecord"):
            config.set_and_save_config("screentime_not_change_to_pause_record", screentime_not_change_to_pause_record)
            config.set_and_save_config("OCR_index_strategy", ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("vid_store_day", vid_store_day)
            config.set_and_save_config("vid_compress_day", vid_compress_day)
            config.set_and_save_config("video_compress_rate", video_compress_rate_selectbox)
            st.toast(d_lang[config.lang]["utils_toast_setting_saved"], icon="🦝")
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
with tab5:
    st.markdown(d_lang[config.lang]["set_md_title"])

    col1b, col2b, col3b = st.columns([1, .5, 1.5])
    with col1b:
        # 更新数据库
        st.markdown(d_lang[config.lang]["set_md_index_db"])

        # 绘制数据库提示横幅
        draw_db_status()

        col1, col2 = st.columns([1, 1])
        with col1:
            update_db_btn = st.button(d_lang[config.lang]["set_btn_update_db_manual"], type="secondary",
                                      key='update_button_key',
                                      disabled=st.session_state.get("update_button_disabled", False),
                                      on_click=update_database_clicked)
            is_shutdown_pasocon_after_updatedDB = st.checkbox(
                d_lang[config.lang]["set_checkbox_shutdown_after_updated"], value=False,
                disabled=st.session_state.get("update_button_disabled", False))

        with col2:
            # 设置ocr引擎
            if config.enable_ocr_chineseocr_lite_onnx:
                check_ocr_engine()
                config_ocr_engine = st.selectbox(d_lang[config.lang]["set_selectbox_local_ocr_engine"],
                                                 ('Windows.Media.Ocr.Cli', 'ChineseOCR_lite_onnx'),
                                                 index=config_ocr_engine_choice_index,
                                                 help=d_lang[config.lang]["set_selectbox_local_ocr_engine_help"]
                                                 )

            # 设定ocr引擎语言
            check_ocr_lang()
            config_ocr_lang = st.selectbox(d_lang[config.lang]["set_selectbox_ocr_lang"], os_support_lang_list,
                                           index=config_ocr_lang_choice_index,
                                           )

            # 设置排除词
            exclude_words = st.text_area(d_lang[config.lang]["set_input_exclude_word"],
                                         value=utils.list_to_string(config.exclude_words),
                                         help=d_lang[config.lang]["set_input_exclude_word_help"])

        # 更新数据库按钮
        if update_db_btn:
            try:
                st.divider()
                estimate_time_str = utils.estimate_indexing_time()  # 预估剩余时间
                with st.spinner(
                        d_lang[config.lang]["set_text_updating_db"].format(estimate_time_str=estimate_time_str)):
                    timeCost = time.time()  # 预埋计算实际时长
                    maintainManager.maintain_manager_main()  # 更新数据库

                    timeCost = time.time() - timeCost
            except Exception as ex:
                st.exception(ex)
            else:
                timeCostStr = utils.convert_seconds_to_hhmmss(timeCost)
                st.success(d_lang[config.lang]["set_text_db_updated_successful"].format(timeCostStr=timeCostStr),
                           icon="🧃")
            finally:
                if is_shutdown_pasocon_after_updatedDB:
                    subprocess.run(["shutdown", "-s", "-t", "60"], shell=True)
                st.snow()
                st.session_state.update_button_disabled = False
                st.button(d_lang[config.lang]["set_btn_got_it"], key=reset_button_key)

        st.divider()
        col1pb, col2pb = st.columns([1, 1])
        with col1pb:
            st.markdown(d_lang[config.lang]["set_md_ocr_ignore_area"],
                        help=d_lang[config.lang]["set_md_ocr_ignore_area_help"])
        with col2pb:
            st.session_state.ocr_screenshot_refer_used = st.toggle(
                d_lang[config.lang]["set_toggle_use_screenshot_as_refer"], False)

        if 'ocr_padding_top' not in st.session_state:
            st.session_state.ocr_padding_top = config.ocr_image_crop_URBL[0]
        if 'ocr_padding_right' not in st.session_state:
            st.session_state.ocr_padding_right = config.ocr_image_crop_URBL[1]
        if 'ocr_padding_bottom' not in st.session_state:
            st.session_state.ocr_padding_bottom = config.ocr_image_crop_URBL[2]
        if 'ocr_padding_left' not in st.session_state:
            st.session_state.ocr_padding_left = config.ocr_image_crop_URBL[3]

        col1pa, col2pa, col3pa = st.columns([.5, .5, 1])
        with col1pa:
            st.session_state.ocr_padding_top = st.number_input(d_lang[config.lang]["set_text_top_padding"],
                                                               value=st.session_state.ocr_padding_top, min_value=0,
                                                               max_value=40)
            st.session_state.ocr_padding_bottom = st.number_input(d_lang[config.lang]["set_text_bottom_padding"],
                                                                  value=st.session_state.ocr_padding_bottom,
                                                                  min_value=0, max_value=40)

        with col2pa:
            st.session_state.ocr_padding_left = st.number_input(d_lang[config.lang]["set_text_left_padding"],
                                                                value=st.session_state.ocr_padding_left, min_value=0,
                                                                max_value=40)
            st.session_state.ocr_padding_right = st.number_input(d_lang[config.lang]["set_text_right_padding"],
                                                                 value=st.session_state.ocr_padding_right, min_value=0,
                                                                 max_value=40)
        with col3pa:
            image_setting_crop_refer = screen_ignore_padding(
                st.session_state.ocr_padding_top,
                st.session_state.ocr_padding_right,
                st.session_state.ocr_padding_bottom,
                st.session_state.ocr_padding_left,
                use_screenshot=st.session_state.ocr_screenshot_refer_used)
            st.image(image_setting_crop_refer)

        st.divider()

        # 界面设置组
        col1_ui, col2_ui = st.columns([1, 1])
        with col1_ui:
            st.markdown(d_lang[config.lang]["set_md_gui"])
            option_show_oneday_wordcloud = st.checkbox(d_lang[config.lang]["set_checkbox_show_wordcloud_under_oneday"],
                                                       value=config.show_oneday_wordcloud)
            # 使用中文形近字进行搜索
            config_use_similar_ch_char_to_search = st.checkbox(
                d_lang[config.lang]["set_checkbox_use_similar_zh_char_to_search"],
                value=config.use_similar_ch_char_to_search,
                help=d_lang[config.lang]["set_checkbox_use_similar_zh_char_to_search_help"])
        with col2_ui:
            config_wordcloud_user_stop_words = st.text_area(d_lang[config.lang]["set_input_wordcloud_filter"],
                                                            help=d_lang[config.lang]["set_input_wordcloud_filter_help"],
                                                            value=utils.list_to_string(
                                                                config.wordcloud_user_stop_words))

        # 每页结果最大数量
        col1_ui2, col2_ui2 = st.columns([1, 1])
        with col1_ui2:
            config_max_search_result_num = st.number_input(d_lang[config.lang]["set_input_max_num_search_page"],
                                                           min_value=1,
                                                           max_value=500, value=config.max_page_result)
        with col2_ui2:
            config_oneday_timeline_num = st.number_input(d_lang[config.lang]["set_input_oneday_timeline_thumbnail_num"],
                                                         min_value=50, max_value=100,
                                                         value=config.oneday_timeline_pic_num, help=d_lang[config.lang][
                    "set_input_oneday_timeline_thumbnail_num_help"])

        # 选择语言
        lang_choice = OrderedDict((k, '' + v) for k, v in lang_map.items())  # 根据读入列表排下序
        language_option = st.selectbox(
            '🌎 Interface Language / 更改显示语言 / 表示言語を変更する',
            (list(lang_choice.values())),
            index=lang_index)

        st.divider()

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary", key="SaveBtnGeneral"):
            config_set_lang(language_option)
            config.set_and_save_config("max_page_result", config_max_search_result_num)
            # config.set_and_save_config("ocr_engine", config_ocr_engine)
            config.set_and_save_config("ocr_lang", config_ocr_lang)
            config.set_and_save_config("exclude_words", utils.string_to_list(exclude_words))
            config.set_and_save_config("show_oneday_wordcloud", option_show_oneday_wordcloud)
            config.set_and_save_config("use_similar_ch_char_to_search", config_use_similar_ch_char_to_search)
            config.set_and_save_config("ocr_image_crop_URBL",
                                       [st.session_state.ocr_padding_top, st.session_state.ocr_padding_right,
                                        st.session_state.ocr_padding_bottom, st.session_state.ocr_padding_left])
            config.set_and_save_config("wordcloud_user_stop_words",
                                       utils.string_to_list(config_wordcloud_user_stop_words))
            config.set_and_save_config("oneday_timeline_pic_num", config_oneday_timeline_num)
            st.toast(d_lang[config.lang]["utils_toast_setting_saved"], icon="🦝")
            time.sleep(1)
            st.experimental_rerun()

    with col2b:
        st.empty()

    with col3b:
        # 关于

        # 更新提醒
        if 'update_info' not in st.session_state:
            st.session_state['update_info'] = d_lang[config.lang]["set_update_checking"]

        if 'update_check' not in st.session_state:
            try:
                with st.spinner(d_lang[config.lang]["set_update_checking"]):
                    tool_version, tool_update_date = utils.get_github_version_and_date()
                    tool_local_version, tool_local_update_date = utils.get_current_version_and_update()
                if tool_update_date > tool_local_update_date:
                    st.session_state.update_info = d_lang[config.lang]["set_update_new"].format(
                        tool_version=tool_version)
                else:
                    st.session_state.update_info = d_lang[config.lang]["set_update_latest"]
            except Exception as e:
                st.session_state.update_info = d_lang[config.lang]["set_update_fail"].format(e=e)

            st.session_state['update_check'] = True

        about_image_b64 = utils.image_to_base64("__assets__\\readme_racoonNagase.png")
        st.markdown(
            f"<img align='right' style='max-width: 100%;max-height: 100%;' src='data:image/png;base64, {about_image_b64}'/>",
            unsafe_allow_html=True)

        about_path = "config\\src\\meta.json"
        with open(about_path, 'r', encoding='utf-8') as f:
            about_json = json.load(f)
        about_markdown = Path("config\\src\\about_" + config.lang + ".md").read_text(encoding='utf-8').format(
            version=about_json["version"], update_date=about_json["update_date"],
            update_info=st.session_state.update_info)
        st.markdown(about_markdown, unsafe_allow_html=True)

web_footer_state()
