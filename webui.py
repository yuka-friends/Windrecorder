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
        videofile_path_month_dir = files.convert_vid_filename_as_YYYY_MM(df.iloc[num]['videofile_name']) # 获取对应的日期目录
        videofile_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, files.add_OCRED_suffix(df.iloc[num]['videofile_name']))
        videofile_path_COMPRESS = os.path.join(config.record_videos_dir, videofile_path_month_dir, files.add_COMPRESS_OCRED_suffix(df.iloc[num]['videofile_name']))
        print("videofile_path: " + videofile_path)
        vid_timestamp = utils.calc_vid_inside_time(df, num)
        print("vid_timestamp: " + str(vid_timestamp))

        st.session_state.vid_vid_timestamp = 0
        st.session_state.vid_vid_timestamp = vid_timestamp
        # st.session_state.vid_vid_timestamp
        # 判断视频文件是否存在
        if os.path.isfile(videofile_path):   # 是否存在未压缩的
            video_file = open(videofile_path, 'rb')
            video_bytes = video_file.read()
            with st.empty():
                st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
            st.markdown(f"`{videofile_path}`")
        elif os.path.isfile(videofile_path_COMPRESS):   # 是否存在已压缩的
            video_file = open(videofile_path_COMPRESS, 'rb')
            video_bytes = video_file.read()
            with st.empty():
                st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
            st.markdown(f"`{videofile_path_COMPRESS}`")
        else:
            st.warning(f"Video File **{videofile_path}** not on disk.", icon="🦫")


# 直接定位视频时间码、展示视频
def show_n_locate_video_timestamp_by_filename_n_time(video_file_name,timestamp):
    st.session_state.day_timestamp = int(timestamp)
    # 合并视频文件路径
    videofile_path_month_dir = files.convert_vid_filename_as_YYYY_MM(video_file_name) # 获取对应的日期目录
    videofile_path = os.path.join(config.record_videos_dir,videofile_path_month_dir, video_file_name)
    print("videofile_path: " + videofile_path)
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
        st.success("欢迎使用 Windrecorder！", icon="😺")
        intro_markdown = Path("onboarding.md").read_text(encoding='utf-8')
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
        print("total_raw:" + str(total_raw))

        slider_min_num_display = df.index.min()
        slider_max_num_display = df.index.max()
        select_num = slider_min_num_display

        # 使用滑杆选择视频
        col1, col2 = st.columns([5, 1])
        with col1:
            select_num = st.slider(d_lang[config.lang]["def_search_slider"], slider_min_num_display, slider_max_num_display, select_num)
        with col2:
            select_num = st.number_input(d_lang[config.lang]["def_search_slider"], label_visibility="hidden", min_value=slider_min_num_display,
                                         max_value=slider_max_num_display, value=select_num)

        select_num_real = select_num - slider_min_num_display   # 将绝对范围转换到从0开始的相对范围

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
            st.success(d_lang[config.lang]["tab_setting_db_state3"].format(nocred_count=nocred_count, count=count), icon='✅')
        elif nocred_count == 0:
            st.success(d_lang[config.lang]["tab_setting_db_state2"].format(nocred_count=nocred_count, count=count), icon='✅')
        else:
            st.success(d_lang[config.lang]["tab_setting_db_state4"].format(nocred_count=nocred_count, count=count), icon='✅')
    elif config.OCR_index_strategy == 2:
        if nocred_count == 1 and record.is_recording():
            st.success(d_lang[config.lang]["tab_setting_db_state3"].format(nocred_count=nocred_count, count=count), icon='✅')
        elif nocred_count >= 1:
            st.warning(d_lang[config.lang]["tab_setting_db_state1"].format(nocred_count=nocred_count, count=count, timeCostStr=timeCostStr), icon='🧭')
        else:
            st.success(d_lang[config.lang]["tab_setting_db_state2"].format(nocred_count=nocred_count, count=count), icon='✅')


# 规范化的打表渲染组件
def draw_dataframe(df,heightIn=800):
    # is_videofile_exist 渲染为可选框
    # ocr_text 更大的展示空间
    # thumbnail 渲染为图像
    st.dataframe(
        df,
        column_config={
            "videofile": st.column_config.CheckboxColumn(
                "videofile",
                help=d_lang[config.lang]["tab_search_table_help1"],
                default=False,
            ),
            "ocr_text": st.column_config.TextColumn(
                "ocr_text",
                help=d_lang[config.lang]["tab_search_table_help2"],
                width="large"
            ),
            "thumbnail": st.column_config.ImageColumn(
                "thumbnail",
                help=d_lang[config.lang]["tab_search_table_help3"]
            )
        },
        height=heightIn
    )


# 显示时间轴
def render_daily_timeline_html(image_b64):
    st.markdown(f"<img style='max-width: 97%;max-height: 100%;margin: 0 0px 5px 50px' src='data:image/png;base64, {image_b64}'/>", unsafe_allow_html=True)



# 生成并显示每月数据量概览
def get_show_month_data_state(stat_select_month_datetime:datetime.datetime):
    if 'df_month_stat' not in st.session_state:   # 初始化显示的表状态
        st.session_state.df_month_stat = pd.DataFrame()
    if 'df_month_stat_dt' not in st.session_state:   # 初始化当前显示表的日期
        st.session_state.df_month_stat_dt = stat_select_month_datetime
    
    df_file_name = stat_select_month_datetime.strftime("%Y-%m") + "_month_data_state.csv"
    df_catch_dir = "catch"
    df_filepath = os.path.join(df_catch_dir, df_file_name)

    update_condition = False
    if not st.session_state.df_month_stat.empty and utils.set_full_datetime_to_YYYY_MM(st.session_state.df_month_stat_dt) <= utils.set_full_datetime_to_YYYY_MM(st.session_state.stat_select_month_datetime):
        update_condition = True

    if st.session_state.df_month_stat.empty or update_condition or utils.set_full_datetime_to_YYYY_MM(st.session_state.df_month_stat_dt) != utils.set_full_datetime_to_YYYY_MM(st.session_state.stat_select_month_datetime):   # 页面内无缓存，或不是当月日期

    # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):   # 存在
            if df_file_name[:7] == datetime.datetime.today().strftime("%Y-%m"):   # 如果是需要时效性的当下月数据
                if not files.is_file_modified_recently(df_filepath, time_gap=120):   # 超过120分钟未更新，过时 重新生成
                    # 更新操作
                    with st.spinner("更新本月统计中……"):
                        st.session_state.df_month_stat = state.get_month_data_overview(stat_select_month_datetime)
                        files.save_dataframe_to_path(st.session_state.df_month_stat,file_path=df_filepath)
            # 进行读取操作
            st.session_state.df_month_stat = files.read_dataframe_from_path(file_path=df_filepath)

        else:   # 磁盘上不存在缓存
            with st.spinner("生成本月统计中……"):
                st.session_state.df_month_stat = state.get_month_data_overview(stat_select_month_datetime)
                files.save_dataframe_to_path(st.session_state.df_month_stat,file_path=df_filepath)    

    st.bar_chart(st.session_state.df_month_stat,x="day",y="data_count",color="#AC79D5")


# 生成并显示每年数据量概览
def get_show_year_data_state(stat_select_year_datetime:datetime.datetime):
    if 'df_year_stat' not in st.session_state:   # 初始化显示的表状态
        st.session_state.df_year_stat = pd.DataFrame()

    df_file_name = stat_select_year_datetime.strftime("%Y") + "_year_data_state.csv"
    df_catch_dir = "catch"
    df_filepath = os.path.join(df_catch_dir, df_file_name)

    if st.session_state.df_year_stat.empty:   # 页面内无缓存

    # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):   # 存在
            if not files.is_file_modified_recently(df_filepath, time_gap=3000):   # 超过3000分钟未更新，过时 重新生成
                # 更新操作
                with st.spinner("更新本年统计中……"):
                    st.session_state.df_year_stat = state.get_year_data_overview(stat_select_year_datetime)
                    files.save_dataframe_to_path(st.session_state.df_year_stat,file_path=df_filepath)
            else:
                # 未过时，进行读取操作
                st.session_state.df_year_stat = files.read_dataframe_from_path(file_path=df_filepath)

        else:   # 磁盘上不存在缓存
            with st.spinner("生成本月统计中……"):
                st.session_state.df_year_stat = state.get_year_data_overview(stat_select_year_datetime)
                files.save_dataframe_to_path(st.session_state.df_year_stat,file_path=df_filepath)
    
    st.bar_chart(st.session_state.df_year_stat,x="month",y="data_count",color="#C873A6",height=200)




# 检查配置使用的ocr引擎
def check_ocr_engine():
    global config_ocr_engine_choice_index
    if config.ocr_engine == "Windows.Media.Ocr.Cli":
        config_ocr_engine_choice_index = 0
    elif config.ocr_engine == "ChineseOCR_lite_onnx":
        config_ocr_engine_choice_index = 1


# 调整屏幕忽略范围的设置可视化
def screen_ignore_padding(topP,rightP,bottomP,leftP,use_screenshot = False):
    image_padding_refer = Image.open("__assets__\\setting-crop-refer-pure.png")

    if use_screenshot:
        image_padding_refer = pyautogui.screenshot()
        image_padding_refer_width, image_padding_refer_height = image_padding_refer.size
        image_padding_refer_height = int(350 * image_padding_refer_height / image_padding_refer_width)
        image_padding_refer = image_padding_refer.resize((350,image_padding_refer_height))
        image_padding_refer_fade = Image.new('RGBA', (350, 200), (235, 235, 235, 150))
        image_padding_refer.paste(image_padding_refer_fade, (0,0), image_padding_refer_fade)

    image_padding_refer_width, image_padding_refer_height = image_padding_refer.size
    topP_height = round(image_padding_refer_height * topP * 0.01)
    bottomP_height = round(image_padding_refer_height * bottomP * 0.01)
    leftP_width = round(image_padding_refer_width * leftP * 0.01)
    rightP_width = round(image_padding_refer_width * rightP * 0.01)

    image_color_area = Image.new('RGBA', (image_padding_refer_width, topP_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0),image_color_area)
    image_color_area = Image.new('RGBA', (image_padding_refer_width, bottomP_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, image_padding_refer_height-bottomP_height),image_color_area)
    image_color_area = Image.new('RGBA', (leftP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (0, 0),image_color_area)
    image_color_area = Image.new('RGBA', (rightP_width, image_padding_refer_height), (100, 0, 255, 80))
    image_padding_refer.paste(image_color_area, (image_padding_refer_width-rightP_width, 0),image_color_area)

    return image_padding_refer



# 更改语言
def config_set_lang(lang_name):
    INVERTED_LANG_MAP = {v: k for k, v in lang_map.items()}
    lang_code = INVERTED_LANG_MAP.get(lang_name)

    if not lang_code:
        print(f"Invalid language name: {lang_name}")
        return

    config.set_and_save_config('lang', lang_code)



# footer状态信息
def web_footer_state():
    # 懒加载，只在刷新时第一次获取
    if 'footer_first_record_time_int' not in st.session_state:
        st.session_state['footer_first_record_time_str'] = utils.seconds_to_date_goodlook_formart(DBManager().db_first_earliest_record_time())

    if 'footer_latest_record_time_str' not in st.session_state:
        st.session_state['footer_latest_record_time_str'] = utils.seconds_to_date_goodlook_formart(DBManager().db_latest_record_time())

    if 'footer_latest_db_records' not in st.session_state:
        st.session_state['footer_latest_db_records'] = DBManager().db_num_records()

    if 'footer_videos_file_size' not in st.session_state:
        st.session_state['footer_videos_file_size'] = round(files.get_dir_size(config.record_videos_dir) / (1024 * 1024 * 1024), 3)

    if 'footer_videos_files_count' not in st.session_state:
        st.session_state['footer_videos_files_count'],_ = files.get_videos_and_ocred_videos_count(config.record_videos_dir)

    # webUI draw
    st.divider()
    col1, col2 = st.columns([1,.3])
    with col1:
        st.markdown(d_lang[config.lang]["footer_info"].format(first_record_time_str = st.session_state.footer_first_record_time_str,
                                                          latest_record_time_str = st.session_state.footer_latest_record_time_str,
                                                        latest_db_records = st.session_state.footer_latest_db_records,
                                                        videos_file_size = st.session_state.footer_videos_file_size,
                                                        videos_files_count = st.session_state.footer_videos_files_count))
    with col2:
        st.markdown(f"<h2 align='right' style='color:rgba(0,0,0,.3)'> Windrecorder 🦝</h2>", unsafe_allow_html=True)

















# 主界面_________________________________________________________
st.markdown(d_lang[config.lang]["main_title"])


tab1, tab2, tab3, tab4, tab5 = st.tabs(["一天之时", d_lang[config.lang]["tab_name_search"], "记忆摘要", d_lang[config.lang]["tab_name_recording"],
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

    col1, col2, col3,col4,col5,col6,col7 = st.columns([.4,.25,.25,.15,.25,.2,1])
    with col1:
        st.markdown("### 一天之时")
    with col2:
        if st.button("← 前一天",use_container_width=True):
            st.session_state.day_date_input -= datetime.timedelta(days=1)
    with col3:
        if st.button("后一天 →",use_container_width=True):
            st.session_state.day_date_input += datetime.timedelta(days=1)
    with col4:
        if st.button("Today",use_container_width=True):
            st.session_state.day_date_input = datetime.date.today()
    with col5:
        st.session_state.day_date_input = st.date_input("当天日期",label_visibility="collapsed",value=st.session_state.day_date_input)
        
        # 获取输入的日期
        # 清理格式到HMS
        dt_in = datetime.datetime(st.session_state.day_date_input.year,st.session_state.day_date_input.month,st.session_state.day_date_input.day,0,0,0)
        # 检查数据库中关于今天的数据
        day_has_data, day_noocred_count, day_search_result_num, day_min_timestamp_dt, day_max_timestamp_dt, day_df = OneDay().checkout(dt_in)
    with col6:
        st.empty()
    with col7:
        # 初始化时间线滑杆启用状态，这个状态同时用来判断是否启用搜索功能，如果True则启用
        if 'day_time_slider_disable' not in st.session_state:
            st.session_state['day_time_slider_disable'] = False

        # 关键词搜索组件
        if 'day_search_query_page_index' not in st.session_state:
            st.session_state['day_search_query_page_index'] = 0

        col1c,col2c,col3c,col4c,col5c = st.columns([1,1.5,1,1,.5])
        with col1c:
            if st.toggle("搜索",help="支持通过空格分开多个关键词进行检索。不输入任何内容直接回车搜索，可列出当日所有数据。"):
                st.session_state.day_time_slider_disable = True
                st.session_state.day_is_search_data = True
            else:
                st.session_state.day_time_slider_disable = False
                st.session_state.day_is_search_data = False
        with col2c:
            # 搜索框
            def search_result():
                # 搜索前清除状态
                st.session_state.day_search_result_index_num = 0

            day_search_keyword = st.text_input(d_lang[config.lang]["tab_search_compname"], 'Keyword',
                                               key=2,label_visibility="collapsed",on_change=search_result(),
                                               disabled=not st.session_state.day_time_slider_disable)
            # 执行搜索，搜索结果
            df_day_search_result = OneDay().search_day_data(utils.complete_datetime(st.session_state.day_date_input),search_content=day_search_keyword)
        with col3c:
            # 结果条目数
            if st.session_state.day_is_search_data:
                # 启用了搜索功能
                if df_day_search_result.empty:
                    st.markdown(f"<p align='center' style='line-height:2.3;'> ⚠ 没有找到结果 </p>", unsafe_allow_html=True)
                else:
                    result_num = df_day_search_result.shape[0]
                    st.markdown(f"<p align='center' style='line-height:2.3;'> → 共 {result_num} 条结果：</p>", unsafe_allow_html=True)
            else:
                st.empty()
        with col4c:
            # 翻页器
            if df_day_search_result.empty:
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
                    max_value=df_day_search_result.shape[0]-1,
                    label_visibility="collapsed",
                    disabled=not st.session_state.day_time_slider_disable,
                    on_change=update_slider(utils.set_full_datetime_to_day_time(utils.seconds_to_datetime(df_day_search_result.loc[st.session_state.day_search_result_index_num, 'videofile_time'])))
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
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir,current_day_cloud_n_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir,current_day_cloud_n_TL_img_name)
        else:
            # current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + ".png"
            current_day_cloud_n_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + ".png"
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir,current_day_cloud_n_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir,current_day_cloud_n_TL_img_name)


        # 时间滑动控制杆
        start_time = datetime.time(day_min_timestamp_dt.hour, day_min_timestamp_dt.minute)
        end_time = datetime.time(day_max_timestamp_dt.hour, day_max_timestamp_dt.minute)
        st.session_state.day_time_select_24h = st.slider("Time Rewind",label_visibility="collapsed",min_value=start_time,max_value=end_time,value=end_time,step=timedelta(seconds=30),disabled=st.session_state.day_time_slider_disable,key="day_time_select_slider")


        # 展示时间轴缩略图
        def update_day_timeline_thumbnail():
            with st.spinner("生成当日时间轴缩略图中，请稍后……"):
                if OneDay().generate_preview_timeline_img(st.session_state.day_date_input,img_saved_name=current_day_cloud_n_TL_img_name):
                    return True
                else:
                    return False

        get_generate_result = True
        if not os.path.exists(current_day_TL_img_path):
            # 如果时间轴缩略图不存在，创建之
            get_generate_result = update_day_timeline_thumbnail()
            # 移除非今日的-today.png
            for filename in os.listdir(config.timeline_result_dir):
                # print(f"-----------------filename：{filename}，real_today_day_cloud_img_name:{real_today_day_cloud_img_name}")
                if filename.endswith("-today-.png") and filename != real_today_day_cloud_n_TL_img_name:
                    file_path = os.path.join(config.timeline_result_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                    except Exception as e:
                        print(e)
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
            st.markdown(f"<p align='center' style='color:rgba(0,0,0,.3)'> 当日缩略图数量不足以生成时间轴。 </p>", unsafe_allow_html=True)



        # 可视化数据时间轴
        # day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df = day_df, start = day_min_timestamp_dt.hour, end = day_max_timestamp_dt.hour+1)
        day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df = day_df, start_dt = day_min_timestamp_dt, end_dt = day_max_timestamp_dt)
        st.area_chart(day_chart_data_overview,x="hour",y="data",use_container_width=True,height=100,color="#AC79D5")



        # 视频展示区域
        col1a, col2a, col3a = st.columns([1,3,1])
        with col1a:
            # 居左部分
            if st.session_state.day_is_search_data and not df_day_search_result.empty:
                # 如果是搜索视图，这里展示全部的搜索结果
                df_day_search_result_refine = DBManager().db_refine_search_data_day(df_day_search_result) # 优化下数据展示
                draw_dataframe(df_day_search_result_refine)
            else:
                st.empty()

        with col2a:
            # 居中部分：视频结果显示区域
            if st.session_state.day_is_search_data and not df_day_search_result.empty:
                # 【搜索功能】
                # 获取关键词，搜索出所有结果的dt，然后使用上下翻页来定位，定位后展示对应的视频
                day_is_video_ondisk,day_video_file_name,shown_timestamp = OneDay().get_result_df_video_time(df_day_search_result,st.session_state.day_search_result_index_num)
                if day_is_video_ondisk:
                    show_n_locate_video_timestamp_by_filename_n_time(day_video_file_name,shown_timestamp)
                    st.markdown(f"`正在回溯 {day_video_file_name}`")
                else:
                    st.info("磁盘上没有找到这个时间的视频文件，不过有文本数据可被检索。", icon="🎐")
                    found_row = df_day_search_result.loc[st.session_state.day_search_result_index_num].to_frame().T
                    found_row = DBManager().db_refine_search_data_day(found_row) # 优化下数据展示
                    draw_dataframe(found_row,heightIn=0)

            else:
                # 【时间线速查功能】
                # 获取选择的时间，查询对应时间下有无视频，有则换算与定位
                day_full_select_datetime = utils.merge_date_day_datetime_together(st.session_state.day_date_input,st.session_state.day_time_select_24h) #合并时间为datetime
                day_is_result_exist, day_video_file_name = OneDay().find_closest_video_by_filesys(day_full_select_datetime) #通过文件查询
                # 计算换算用于播放视频的时间

                if day_is_result_exist:
                    # 换算时间、定位播放视频
                    vidfile_timestamp = utils.calc_vid_name_to_timestamp(day_video_file_name)
                    select_timestamp = utils.datetime_to_seconds(day_full_select_datetime)
                    shown_timestamp = select_timestamp - vidfile_timestamp
                    show_n_locate_video_timestamp_by_filename_n_time(day_video_file_name,shown_timestamp)
                    st.markdown(f"`正在回溯 {day_video_file_name}`")
                else:
                    # 没有对应的视频，查一下有无索引了的数据
                    is_data_found,found_row =OneDay().find_closest_video_by_database(day_df,utils.datetime_to_seconds(day_full_select_datetime))
                    if is_data_found:
                        st.info("磁盘上没有找到这个时间的视频文件，不过这个时间附近有以下数据可以检索。", icon="🎐")
                        found_row = DBManager().db_refine_search_data_day(found_row) # 优化下数据展示
                        draw_dataframe(found_row,heightIn=0)
                    else:
                        # 如果是当天第一次打开但数据库正在索引因而无法访问
                        if utils.set_full_datetime_to_YYYY_MM_DD(st.session_state.day_date_input) == utils.set_full_datetime_to_YYYY_MM_DD(datetime.datetime.today()) and utils.is_maintain_lock_file_valid():
                            st.warning("有数据正在被索引中，请稍等几分钟后刷新查看。", icon="🦫")
                        else:
                            st.warning("磁盘上没有找到这个时间的视频文件和索引记录。", icon="🦫")
        
        with col3a:
            if config.show_oneday_wordcloud:
                # 是否展示当天词云
                def update_day_word_cloud():
                    with st.spinner("生成当日词云中，请稍后……"):
                        day_input_datetime_finetune = datetime.datetime(st.session_state.day_date_input.year,st.session_state.day_date_input.month,st.session_state.day_date_input.day,0,0,2)
                        wordcloud.generate_word_cloud_in_day(utils.datetime_to_seconds(day_input_datetime_finetune),img_save_name=current_day_cloud_n_TL_img_name)

                if not os.path.exists(current_day_cloud_img_path):
                    # 如果词云不存在，创建之
                    update_day_word_cloud()
                    # 移除非今日的-today.png
                    for filename in os.listdir(config.wordcloud_result_dir):
                        # print(f"-----------------filename：{filename}，real_today_day_cloud_img_name:{real_today_day_cloud_img_name}")
                        if filename.endswith("-today-.png") and filename != real_today_day_cloud_n_TL_img_name:
                            file_path = os.path.join(config.wordcloud_result_dir, filename)
                            os.remove(file_path)
                            print(f"Deleted file: {file_path}")

                # 展示词云
                image = Image.open(current_day_cloud_img_path)
                st.image(image)

                def update_wordcloud_btn_clicked():
                    st.session_state.update_wordcloud_button_disabled = True

                if st.button("更新词云 ⟳",key="refresh_day_cloud",use_container_width=True,disabled=st.session_state.get("update_wordcloud_button_disabled", False),on_click=update_wordcloud_btn_clicked):
                    try:
                        update_day_word_cloud()
                    except Exception as ex:
                        st.exception(ex)
                    finally:
                        st.session_state.update_wordcloud_button_disabled = False
                        st.experimental_rerun()
            else:
                st.markdown(f"<p align='center' style='color:rgba(0,0,0,.3)'> 每日词云已关闭，可前往设置页开启。 </p>", unsafe_allow_html=True)


    else:
        # 数据库中没有今天的记录
        # 判断videos下有无今天的视频文件
        if files.find_filename_in_dir("videos",utils.datetime_to_dateDayStr(dt_in)):
            st.info("数据库中没有这一天的数据索引。不过，磁盘上有这一天的视频还未索引，请前往「设置」进行索引。→", icon="📎")
        else:
            st.info("没有找到这一天的数据索引和视频文件。", icon="🎐")






# tab：全局关键词搜索
if 'db_global_search_result' not in st.session_state:
    st.session_state['db_global_search_result'] = pd.DataFrame()
# db_global_search_result = pd.DataFrame()
with tab2:

    col1, col2 = st.columns([1, 2])
    with col1:
        col1_gstype, col2_gstype = st.columns([2,1])
        with col1_gstype:
            st.markdown(d_lang[config.lang]["tab_search_title"])
        with col2_gstype:
            # st.selectbox("搜索方式", ('关键词匹配','模糊语义搜索 [不可用]','画面内容搜索 [不可用]'),label_visibility="collapsed")
            st.empty()

        web_onboarding()

        # 初始化一些全局状态
        if 'max_page_count' not in st.session_state:
            st.session_state.max_page_count = 1
        if 'all_result_counts' not in st.session_state:
            st.session_state.all_result_counts = 1
        if 'search_content' not in st.session_state:
            st.session_state.search_content = "hello"
        if 'search_content_exclude' not in st.session_state:
            st.session_state.search_content_exclude = ""
        if 'search_date_range_in' not in st.session_state:
            st.session_state.search_date_range_in = datetime.datetime.today() - datetime.timedelta(seconds=86400)
        if 'search_date_range_out' not in st.session_state:
            st.session_state.search_date_range_out = datetime.datetime.today()
        if 'catch_videofile_ondisk_list' not in st.session_state:   # 减少io读取，预拿视频文件列表供比对是否存在
            st.session_state.catch_videofile_ondisk_list = files.get_file_path_list(config.record_videos_dir)

        # 时间搜索范围组件（懒加载）
        if 'search_latest_record_time_int' not in st.session_state:
            st.session_state['search_latest_record_time_int'] = DBManager().db_latest_record_time()
        if 'search_earlist_record_time_int' not in st.session_state:
            st.session_state['search_earlist_record_time_int'] = DBManager().db_first_earliest_record_time()

        # 优化streamlit强加载机制导致的索引时间：改变了再重新搜索，而不是每次提交了更改都进行搜索
        if 'search_content_lazy' not in st.session_state:
            st.session_state.search_content_lazy = None
        if 'search_content_exclude_lazy' not in st.session_state:
            st.session_state.search_content_lazy = None
        if 'search_date_range_in_lazy' not in st.session_state:
            st.session_state.search_date_range_in_lazy = datetime.datetime(1970, 1, 2) + datetime.timedelta(seconds=st.session_state.search_earlist_record_time_int) - datetime.timedelta(seconds=86400)
        if 'search_date_range_out_lazy' not in st.session_state:
            st.session_state.search_date_range_out = datetime.datetime(1970, 1, 2) + datetime.timedelta(seconds=st.session_state.search_latest_record_time_int) - datetime.timedelta(seconds=86400)

        # 获得全局搜索结果
        def do_global_keyword_search():
            # 如果搜索所需入参状态改变了，进行搜索
            if st.session_state.search_content_lazy != st.session_state.search_content or st.session_state.search_content_exclude_lazy != st.session_state.search_content_exclude or st.session_state.search_date_range_in_lazy != st.session_state.search_date_range_in or st.session_state.search_date_range_out_lazy != st.session_state.search_date_range_out:
                st.session_state.search_content_lazy = st.session_state.search_content
                st.session_state.search_content_exclude_lazy = st.session_state.search_content_exclude
                st.session_state.search_date_range_in_lazy = st.session_state.search_date_range_in
                st.session_state.search_date_range_out_lazy = st.session_state.search_date_range_out

                st.session_state.db_global_search_result, st.session_state.all_result_counts, st.session_state.max_page_count = DBManager().db_search_data(st.session_state.search_content, 
                                                                                                                                          st.session_state.search_date_range_in, 
                                                                                                                                          st.session_state.search_date_range_out,
                                                                                                                                          keyword_input_exclude = st.session_state.search_content_exclude)
                        

        col1a, col2a, col3a, col4a = st.columns([2, 1, 2, 1])
        with col1a:
            st.session_state.search_content = st.text_input(d_lang[config.lang]["tab_search_compname"], value="", on_change=do_global_keyword_search(),help="可使用空格分隔多个关键词。")
        with col2a:
            st.session_state.search_content_exclude = st.text_input("排除", "",help="排除哪些关键词的内容，留空为不排除。可使用空格分隔多个关键词。", on_change=do_global_keyword_search())
        with col3a:

            try:
                st.session_state.search_date_range_in, st.session_state.search_date_range_out = st.date_input(
                    d_lang[config.lang]["tab_search_daterange"],
                    (datetime.datetime(1970, 1, 2)
                        + datetime.timedelta(seconds=st.session_state.search_earlist_record_time_int)
                        - datetime.timedelta(seconds=86400),
                    datetime.datetime(1970, 1, 2)
                        + datetime.timedelta(seconds=st.session_state.search_latest_record_time_int)
                        - datetime.timedelta(seconds=86400)
                    ),
                    format="YYYY-MM-DD",
                    on_change=do_global_keyword_search()
                )
            except:
                st.warning("请选择完整的时间范围")

        with col4a:
            # 结果翻页器
            st.session_state.page_index = st.number_input("结果页数", min_value=1, step=1, max_value=st.session_state.max_page_count+1)

        # 进行搜索
        if not len(st.session_state.search_content) == 0:
            timeCost = time.time() # 预埋计算实际时长

            df = DBManager().db_search_data_page_turner(st.session_state.db_global_search_result, st.session_state.page_index)
            
            is_df_result_exist = len(df)

            timeCost = round(time.time() - timeCost, 5)
            st.markdown(f"`搜索到 {st.session_state.all_result_counts} 条、共 {st.session_state.max_page_count} 页关于 \"{st.session_state.search_content}\" 的结果。用时：{timeCost}s`")

            # 滑杆选择
            result_choose_num = choose_search_result_num(df, is_df_result_exist)

            if len(df) == 0:
                st.info(d_lang[config.lang]["tab_search_word_no"].format(search_content=st.session_state.search_content), icon="🎐")
            else:
                # 打表
                df = DBManager().db_refine_search_data_global(df, catch_videofile_ondisk_list=st.session_state.catch_videofile_ondisk_list) # 优化数据显示
                draw_dataframe(df, heightIn=800)
        
        else:
            st.info("这里是全局搜索页，可以搜索到迄今记录的所有内容。输入关键词后回车即可搜索。",icon="🔎")

    with col2:
        # 选择视频
        if not len(st.session_state.search_content) == 0:
            show_n_locate_video_timestamp_by_df(df, result_choose_num)
        else:
            st.empty()



# tab: 记忆摘要
with tab3:
    
    col1, col2 = st.columns([1,2])
    with col1:
        # 懒加载
        if 'stat_db_earliest_datetime' not in st.session_state:
            st.session_state['stat_db_earliest_datetime'] = utils.seconds_to_datetime(DBManager().db_first_earliest_record_time())
        if 'stat_db_latest_datetime' not in st.session_state:
            st.session_state['stat_db_latest_datetime'] = utils.seconds_to_datetime(DBManager().db_latest_record_time())

        if st.session_state.stat_db_latest_datetime.year > st.session_state.stat_db_earliest_datetime.year:
            # 当记录时间超过一年
            selector_month_min = 1
            selector_month_max = 12
        else:
            selector_month_min = st.session_state.stat_db_earliest_datetime.month
            selector_month_max = st.session_state.stat_db_latest_datetime.month

        st.markdown("### 当月数据统计")
        col1a, col2a, col3a = st.columns([.5,.5,1])
        with col1a:
            st.session_state.Stat_query_Year = st.number_input(label="Stat_query_Year",min_value=st.session_state.stat_db_earliest_datetime.year,max_value=st.session_state.stat_db_latest_datetime.year,value=st.session_state.stat_db_latest_datetime.year,label_visibility="collapsed")
        with col2a:
            st.session_state.Stat_query_Month = st.number_input(label="Stat_query_Month",min_value=selector_month_min,max_value=selector_month_max,value=st.session_state.stat_db_latest_datetime.month,label_visibility="collapsed")
        with col3a:
            st.empty()
        
        st.session_state.stat_select_month_datetime = datetime.datetime(st.session_state.Stat_query_Year,st.session_state.Stat_query_Month,1,10,0,0)
        get_show_month_data_state(st.session_state.stat_select_month_datetime) # 显示当月概览

        stat_year_title = st.session_state.stat_select_month_datetime.year
        st.markdown(f"### {stat_year_title} 记录")
        get_show_year_data_state(st.session_state.stat_select_month_datetime) # 显示当年概览


    with col2:
        st.markdown("### 记忆摘要")

        col1_mem, col2_mem = st.columns([1,1])
        with col1_mem:
            current_month_cloud_img_name = str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            current_month_cloud_img_path = os.path.join(config.wordcloud_result_dir,current_month_cloud_img_name)

            if st.button("生成/更新本月词云"):
                with st.spinner("生成中，大概需要 30s……"):
                    print("生成词云")
                    wordcloud.generate_word_cloud_in_month(utils.datetime_to_seconds(st.session_state.stat_select_month_datetime),current_month_cloud_img_name)

            if os.path.exists(current_month_cloud_img_path):
                image = Image.open(current_month_cloud_img_path)
                st.image(image,caption=current_month_cloud_img_path)
            else:
                st.info("当月未有词云图片。")

        with col2_mem:
            current_month_lightbox_img_name = str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            current_month_lightbox_img_path = os.path.join(config.lightbox_result_dir,current_month_lightbox_img_name)

            if st.button("生成/更新本月的光箱"):
                with st.spinner("生成中，大概需要 5s……"):
                    print("生成光箱")
                    state.generate_month_lightbox(st.session_state.stat_select_month_datetime,img_saved_name=current_month_lightbox_img_name)
            
            if os.path.exists(current_month_lightbox_img_path):
                image = Image.open(current_month_lightbox_img_path)
                st.image(image,caption=current_month_lightbox_img_path)
            else:
                st.info("当月未有光箱图片。")
                

    



with tab4:
    st.markdown(d_lang[config.lang]["tab_record_title"])

    col1c, col2c, col3c = st.columns([1, .5, 1.5])
    with col1c:
        st.info("本页的设置在保存后，需重启 start_record.bat 才能生效。")

        # 手动检查录屏服务有无进行中

        # 管理刷新服务的按钮状态：手动管理状态，polyfill streamlit只能读按钮是否被按下的问题（一旦有其他按钮按下，其他按钮就会回弹导致持续的逻辑重置、重新加载）
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

        
        btn_refresh = st.button("查询录制状态 ⟳",on_click=update_record_btn_state)

        if st.session_state.update_btn_refresh_press:

            if record.is_recording():
                st.success("正在持续录制屏幕，刷新以查询最新运行状态。若想停止录制屏幕，请手动关闭后台的 “Windrecorder - Recording Screening” 终端窗口。", icon="🦚")
                # stop_record_btn = st.button('停止录制屏幕', type="secondary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                # if stop_record_btn:
                #     st.toast("正在结束录屏进程……")
                #     utils.kill_recording()
                    
            else:
                st.error("当前未在录制屏幕。  请刷新查看最新运行状态。", icon="🦫")
                start_record_btn = st.button('开始持续录制', type="primary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                if start_record_btn:
                    os.startfile('start_record.bat', 'open')
                    st.toast("启动录屏中……")
                    st.session_state.update_btn_refresh_press = False


        # st.warning("录制服务已启用。当前暂停录制屏幕。",icon="🦫")
        st.divider()
        st.markdown("#### 录制选项")

        col1_record, col2_record = st.columns([1,1])
        with col1_record:
            if 'is_create_startup_shortcut' not in st.session_state:
                st.session_state.is_create_startup_shortcut = record.is_file_already_in_startup('start_record.bat.lnk')
            st.session_state.is_create_startup_shortcut = st.checkbox(
                '开机后自动开始录制', value=record.is_file_already_in_startup('start_record.bat.lnk'), 
                on_change=record.create_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut),
                help="此项勾选后会为'start_record.bat'创建快捷方式，并放到系统开机自启动的目录下。此项行为可能会被部分安全软件误判为病毒行为，导致'start_webui.bat'被移除，如有拦截，请将其移出隔离区并标记为可信任软件。或手动为'start_record.bat'创建快捷方式、并放到系统的开机启动目录下。")

        with col2_record:
            st.markdown("<p align='right' style='color:rgba(0,0,0,.5)'>当前仅支持录制主显示器画面。</p>",unsafe_allow_html=True)



        screentime_not_change_to_pause_record = st.number_input('当画面几分钟没有变化时，暂停录制下个视频切片（0为永不暂停）', value=config.screentime_not_change_to_pause_record, min_value=0)

        st.divider()

        # 自动化维护选项 WIP
        st.markdown(d_lang[config.lang]["tab_setting_maintain_title"])
        ocr_strategy_option_dict = {
            "不自动更新，仅手动更新":0,
            "视频切片录制完毕时自动索引（推荐）":1
        }
        ocr_strategy_option = st.selectbox('OCR 索引策略',
                     (list(ocr_strategy_option_dict.keys())),
                     index=config.OCR_index_strategy
                     )
        
        col1d,col2d,col3d = st.columns([1,1,1])
        with col1d:
            vid_store_day = st.number_input(d_lang[config.lang]["tab_setting_m_vid_store_time"], min_value=0, value=config.vid_store_day, help="0 为永不删除。")
        with col2d:
            vid_compress_day = st.number_input("原视频在保留几天后进行压缩",value=config.vid_compress_day,min_value=0,help="0 为永不压缩。")
        with col3d:
            video_compress_selectbox_dict = {'0.75':0, '0.5':1, '0.25':2}
            video_compress_rate_selectbox = st.selectbox("压缩到原先画面尺寸的",list(video_compress_selectbox_dict.keys()),index=video_compress_selectbox_dict[config.video_compress_rate])

        st.divider()

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary",key="SaveBtnRecord"):
            config.set_and_save_config("screentime_not_change_to_pause_record",screentime_not_change_to_pause_record)
            config.set_and_save_config("OCR_index_strategy",ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("vid_store_day",vid_store_day)
            config.set_and_save_config("vid_compress_day",vid_compress_day)
            config.set_and_save_config("video_compress_rate",video_compress_rate_selectbox)
            st.toast("已应用更改。", icon="🦝")
            time.sleep(2)
            st.experimental_rerun()

    with col2c:
        st.empty()

    with col3c:
        howitwork_markdown = Path("config\\src\\how_it_work_" + config.lang + ".md").read_text(encoding='utf-8')
        st.markdown(howitwork_markdown,unsafe_allow_html=True)



def update_database_clicked():
    st.session_state.update_button_disabled = True


# 设置页
with tab5:
    st.markdown(d_lang[config.lang]["tab_setting_title"])

    col1b, col2b, col3b = st.columns([1, .5, 1.5])
    with col1b:
        # 更新数据库
        st.markdown(d_lang[config.lang]["tab_setting_db_title"])

        # 绘制数据库提示横幅
        draw_db_status()

        col1, col2 = st.columns([1, 1])
        with col1:
            update_db_btn = st.button(d_lang[config.lang]["tab_setting_db_btn"], type="secondary", key='update_button_key',
                                      disabled=st.session_state.get("update_button_disabled", False),
                                      on_click=update_database_clicked)
            is_shutdown_pasocon_after_updatedDB = st.checkbox('更新完毕后关闭计算机', value=False,disabled=st.session_state.get("update_button_disabled", False))
        
        with col2:
            # 设置ocr引擎
            check_ocr_engine()
            config_ocr_engine = st.selectbox('本地 OCR 引擎', ('Windows.Media.Ocr.Cli', 'ChineseOCR_lite_onnx'),
                                             index=config_ocr_engine_choice_index,
                                             help="（待补充描述）推荐使用 Windows.Media.Ocr.Cli")

            # 设置排除词
            exclude_words = st.text_area("当 OCR 存在以下词语之一时跳过索引",value=utils.list_to_string(config.exclude_words),help="当有些画面/应用不想被索引时，可以在此添加它们可能出现的关键词，以半角逗号“, ”分割。比如不想记录在 捕风记录仪 的查询画面，可以添加“, 捕风记录仪”。")
            

        # 更新数据库按钮
        if update_db_btn:
            try:
                st.divider()
                estimate_time_str = utils.estimate_indexing_time() # 预估剩余时间
                with st.spinner(d_lang[config.lang]["tab_setting_db_tip1"].format(estimate_time_str=estimate_time_str)):
                    timeCost = time.time() # 预埋计算实际时长
                    maintainManager.maintain_manager_main() # 更新数据库

                    timeCost = time.time() - timeCost
            except Exception as ex:
                st.exception(ex)
            else:
                timeCostStr = utils.convert_seconds_to_hhmmss(timeCost)
                st.success(d_lang[config.lang]["tab_setting_db_tip3"].format(timeCostStr=timeCostStr),icon="🧃")
            finally:
                if is_shutdown_pasocon_after_updatedDB:
                    subprocess.run(["shutdown", "-s", "-t", "60"], shell=True)
                st.snow()
                st.session_state.update_button_disabled = False
                st.button(d_lang[config.lang]["tab_setting_db_btn_gotit"], key=reset_button_key)

        st.divider()
        col1pb, col2pb = st.columns([1,1])
        with col1pb:
            st.markdown("**OCR 时忽略屏幕四边的区域范围**",help="填入数字为百分比，比如'6' == 6%。此选项可以在 OCR 时忽略屏幕四边的元素，如浏览器的标签栏、Windows 的开始菜单、网页内的花边广告信息等。")
        with col2pb:
            st.session_state.ocr_screenshot_refer_used = st.toggle("用当前屏幕截图参照",False)

        if 'ocr_padding_top' not in st.session_state:
            st.session_state.ocr_padding_top = config.ocr_image_crop_URBL[0]
        if 'ocr_padding_right' not in st.session_state:
            st.session_state.ocr_padding_right = config.ocr_image_crop_URBL[1]
        if 'ocr_padding_bottom' not in st.session_state:
            st.session_state.ocr_padding_bottom = config.ocr_image_crop_URBL[2]
        if 'ocr_padding_left' not in st.session_state:
            st.session_state.ocr_padding_left = config.ocr_image_crop_URBL[3]

        col1pa, col2pa, col3pa = st.columns([.5,.5,1])
        with col1pa:
            st.session_state.ocr_padding_top = st.number_input("上边框",value=st.session_state.ocr_padding_top,min_value=0,max_value=40)
            st.session_state.ocr_padding_bottom = st.number_input("下边框",value=st.session_state.ocr_padding_bottom,min_value=0,max_value=40)
            
        with col2pa:
            st.session_state.ocr_padding_left = st.number_input("左边框",value=st.session_state.ocr_padding_left,min_value=0,max_value=40)
            st.session_state.ocr_padding_right = st.number_input("右边框",value=st.session_state.ocr_padding_right,min_value=0,max_value=40)
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
        col1_ui, col2_ui = st.columns([1,1])
        with col1_ui:
            st.markdown(d_lang[config.lang]["tab_setting_ui_title"])
            option_show_oneday_wordcloud = st.checkbox("在「一天之时」下展示每日词云",value=config.show_oneday_wordcloud)
            # 使用中文形近字进行搜索
            config_use_similar_ch_char_to_search = st.checkbox("使用中文形近字进行搜索",value=config.use_similar_ch_char_to_search)
        with col2_ui:
            config_wordcloud_user_stop_words = st.text_area("在词云生成中过滤以下词语：", help="待补充", value=utils.list_to_string(config.wordcloud_user_stop_words))

        # 每页结果最大数量
        config_max_search_result_num = st.number_input(d_lang[config.lang]["tab_setting_ui_result_num"], min_value=1,
                                                       max_value=500, value=config.max_page_result)
        
        config_oneday_timeline_num = st.number_input("「一天之时」时间轴的横向缩略图数量", min_value=50, max_value=100, value=config.oneday_timeline_pic_num)

        # 选择语言
        lang_choice = OrderedDict((k, '' + v) for k, v in lang_map.items())   #根据读入列表排下序
        language_option = st.selectbox(
            'Interface Language / 更改显示语言',
            (list(lang_choice.values())),
            index=lang_index)

        st.divider()

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary",key="SaveBtnGeneral"):
            config_set_lang(language_option)
            config.set_and_save_config("max_page_result", config_max_search_result_num)
            config.set_and_save_config("ocr_engine", config_ocr_engine)
            config.set_and_save_config("exclude_words", utils.string_to_list(exclude_words))
            config.set_and_save_config("show_oneday_wordcloud",option_show_oneday_wordcloud)
            config.set_and_save_config("use_similar_ch_char_to_search",config_use_similar_ch_char_to_search)
            config.set_and_save_config("ocr_image_crop_URBL",[st.session_state.ocr_padding_top, st.session_state.ocr_padding_right, st.session_state.ocr_padding_bottom, st.session_state.ocr_padding_left])
            config.set_and_save_config("wordcloud_user_stop_words", utils.string_to_list(config_wordcloud_user_stop_words))
            config.set_and_save_config("oneday_timeline_pic_num", config_oneday_timeline_num)
            st.toast("已应用更改。", icon="🦝")
            time.sleep(2)
            st.experimental_rerun()

    with col2b:
        st.empty()

    with col3b:
        # 关于
        about_path = "config\\src\\meta.json"
        with open(about_path, 'r', encoding='utf-8') as f:
            about_json = json.load(f)
        about_markdown = Path("config\\src\\about_" + config.lang + ".md").read_text(encoding='utf-8').format(version=about_json["version"], update_date=about_json["update_date"])
        st.markdown(about_markdown,unsafe_allow_html=True)

web_footer_state()
