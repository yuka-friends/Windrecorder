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

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
import pandas as pd

from windrecorder.dbManager import dbManager
from windrecorder.oneday import OneDay
from windrecorder.config import config
import windrecorder.maintainManager as maintainManager
import windrecorder.utils as utils
import windrecorder.files as files
import windrecorder.config
import windrecorder.record as record

update_button_key = "update_button"
reset_button_key = "setting_reset"

# python -m streamlit run webui.py

# 获取i18n表，调用方式为 d_lang[config.lang]["key"].format(var=var, var=var)
with open("languages.json", encoding='utf-8') as f:
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
        videofile_path = os.path.join(config.record_videos_dir, files.add_OCRED_suffix(df.iloc[num]['videofile_name']))
        print("videofile_path: " + videofile_path)
        vid_timestamp = utils.calc_vid_inside_time(df, num)
        print("vid_timestamp: " + str(vid_timestamp))

        st.session_state.vid_vid_timestamp = 0
        st.session_state.vid_vid_timestamp = vid_timestamp
        # st.session_state.vid_vid_timestamp
        # 判断视频文件是否存在
        if os.path.isfile(videofile_path):
            video_file = open(videofile_path, 'rb')
            video_bytes = video_file.read()
            with st.empty():
                st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
        else:
            # st.markdown(f"Video File **{videofile_path}** not on disk.")
            st.warning(f"Video File **{videofile_path}** not on disk.", icon="🦫")


# 直接定位视频时间码、展示视频
def show_n_locate_video_timestamp_by_filename_n_time(video,timestamp):
    st.session_state.day_timestamp = int(timestamp)
    # 合并视频文件路径
    videofile_path = os.path.join(config.record_videos_dir, video)
    print("videofile_path: " + videofile_path)
    # 打开并展示定位视频文件
    video_file = open(videofile_path, 'rb')
    video_bytes = video_file.read()
    with st.empty():
        st.video(video_bytes, start_time=st.session_state.day_timestamp)


# 检测是否初次使用工具，如果不存在数据库/数据库中只有一条数据，则判定为是
def check_is_onboarding():
    is_db_existed = dbManager.db_main_initialize()
    if not is_db_existed:
        return True
    latest_db_records = dbManager.db_num_records()
    if latest_db_records == 1:
        return True
    return False


# 检测并渲染onboarding提示
def web_onboarding():
    is_onboarding = check_is_onboarding()
    if is_onboarding:
        # 数据库不存在，展示 Onboarding 提示
        st.success("欢迎使用 Windrecorder！", icon="😺")
        intro_markdown = Path("onboarding.md").read_text(encoding='utf-8')
        st.markdown(intro_markdown)
        st.divider()


# 选择播放视频的行数 的滑杆组件
def choose_search_result_num(df, is_df_result_exist):
    select_num = 0

    if is_df_result_exist == 1:
        # 如果结果只有一个，直接显示结果而不显示滑杆
        return 0
    elif not is_df_result_exist == 0:
        # shape是一个元组,索引0对应行数,索引1对应列数。
        total_raw = df.shape[0]
        print("total_raw:" + str(total_raw))

        # 使用滑杆选择视频
        col1, col2 = st.columns([5, 1])
        with col1:
            select_num = st.slider(d_lang[config.lang]["def_search_slider"], 0, total_raw - 1, select_num)
        with col2:
            select_num = st.number_input(d_lang[config.lang]["def_search_slider"], label_visibility="hidden", min_value=0,
                                         max_value=total_raw - 1, value=select_num)

        return select_num
    else:
        return 0


# 对搜索结果执行翻页查询
def db_set_page(btn, page_index):
    if btn == "L":
        if page_index <= 0:
            return 0
        else:
            page_index -= 1
            return page_index
    elif btn == "R":
        page_index += 1
        return page_index


# 数据库的前置更新索引状态提示
def draw_db_status():
    count, nocred_count = files.get_videos_and_ocred_videos_count(config.record_videos_dir)
    timeCostStr = utils.estimate_indexing_time()
    if nocred_count == 1 and record.is_recording():
        st.success(d_lang[config.lang]["tab_setting_db_state3"].format(nocred_count=nocred_count, count=count), icon='✅')
    elif nocred_count >= 1:
        st.warning(d_lang[config.lang]["tab_setting_db_state1"].format(nocred_count=nocred_count, count=count, timeCostStr=timeCostStr), icon='🧭')
    else:
        st.success(d_lang[config.lang]["tab_setting_db_state2"].format(nocred_count=nocred_count, count=count), icon='✅')


# 规范化的打表渲染组件
def draw_dataframe(df,heightIn=800):
    st.dataframe(
        df,
        column_config={
            "is_videofile_exist": st.column_config.CheckboxColumn(
                "is_videofile_exist",
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


# 检查配置使用的ocr引擎
def check_ocr_engine():
    global config_ocr_engine_choice_index
    if config.ocr_engine == "Windows.Media.Ocr.Cli":
        config_ocr_engine_choice_index = 0
    elif config.ocr_engine == "ChineseOCR_lite_onnx":
        config_ocr_engine_choice_index = 1


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
    latest_record_time_int = dbManager.db_latest_record_time()
    latest_record_time_str = utils.seconds_to_date(latest_record_time_int)

    latest_db_records = dbManager.db_num_records()

    videos_file_size = round(utils.get_dir_size(config.record_videos_dir) / (1024 * 1024 * 1024), 3)

    # webUI draw
    st.divider()
    # st.markdown(f'Database latest record time: **{latest_record_time_str}**, Database records: **{latest_db_records}**, Video Files on disk: **{videos_file_size} GB**')
    st.markdown(d_lang[config.lang]["footer_info"].format(latest_record_time_str=latest_record_time_str,
                                                   latest_db_records=latest_db_records,
                                                   videos_file_size=videos_file_size))

















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
    
    # 日期选择器们
    if 'day_date_input' not in st.session_state:
        st.session_state['day_date_input'] = datetime.date.today()

    col1, col2, col3 = st.columns([.8,1,1])
    with col1:
        st.markdown("### 一天之时")
    with col2:
        # 日期切换控件
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("← 前一天",use_container_width=True):
                st.session_state.day_date_input -= datetime.timedelta(days=1)
        with col2:
            if st.button("后一天 →",use_container_width=True):
               st.session_state.day_date_input += datetime.timedelta(days=1)
        with col3:
            st.session_state.day_date_input = st.date_input("当天日期",label_visibility="collapsed",value=st.session_state.day_date_input)
    with col3:
        st.empty()


    # 获取输入的日期
    # 清理格式到HMS
    dt_in = datetime.datetime(st.session_state.day_date_input.year,st.session_state.day_date_input.month,st.session_state.day_date_input.day,0,0,0)
    # 检查数据库中关于今天的数据
    day_has_data, day_noocred_count,day_search_result_num,day_min_timestamp_dt,day_max_timestamp_dt,day_df = OneDay().checkout(dt_in)


    # 判断数据库中有无今天的数据，有则启用功能：
    if day_has_data:

        # 初始化滑杆启用状态，这个状态同时用来判断是否启用搜索功能，如果True则启用
        if 'day_time_slider_disable' not in st.session_state:
            st.session_state['day_time_slider_disable'] = False

        # 关键词搜索模块
        col1b, col2b,col3b = st.columns([.8,1,1])
        with col1b:
            st.empty()
        with col2b:
            # 搜索组件
            if 'day_search_query_page_index' not in st.session_state:
                st.session_state['day_search_query_page_index'] = 0

            col1c,col2c,col3c,col4c,col5c = st.columns([1,1.5,1.5,1.5,.5])
            with col1c:
                if st.checkbox("关键词搜索",help="不输入任何内容直接回车搜索，可列出当日所有数据。"):
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
                        st.markdown(f"<p align='right' style='line-height:2.3;'> 没有找到结果 </p>", unsafe_allow_html=True)
                    else:
                        result_num = df_day_search_result.shape[0]
                        st.markdown(f"<p align='right' style='line-height:2.3;'> 共找到 {result_num} 条结果：</p>", unsafe_allow_html=True)
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
                if df_day_search_result.empty:
                    st.empty()
                else:
                    st.button(label="⟳",
                              on_click=update_slider(utils.set_full_datetime_to_day_time(utils.seconds_to_datetime(df_day_search_result.loc[st.session_state.day_search_result_index_num, 'videofile_time']))),
                              disabled=not st.session_state.day_time_slider_disable,use_container_width=True
                              )

        with col3b:
            st.empty()


        # 时间滑动控制杆
        start_time = datetime.time(day_min_timestamp_dt.hour, day_min_timestamp_dt.minute)
        end_time = datetime.time(day_max_timestamp_dt.hour, day_max_timestamp_dt.minute)
        st.session_state.day_time_select_24h = st.slider("Time Rewind",label_visibility="collapsed",min_value=start_time,max_value=end_time,value=end_time,step=timedelta(seconds=30),disabled=st.session_state.day_time_slider_disable,key="day_time_select_slider")


        # 可视化数据时间轴
        day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df = day_df, start = day_min_timestamp_dt.hour, end = day_max_timestamp_dt.hour+1)
        st.bar_chart(day_chart_data_overview,x="hour",y="data",use_container_width=True,height=100)


        # 视频展示区域
        col1a, col2a, col3a = st.columns([1,3,1])
        with col1a:
            # 居左部分
            if st.session_state.day_is_search_data and not df_day_search_result.empty:
                # 如果是搜索视图，这里展示全部的搜索结果
                df_day_search_result_refine = dbManager.db_refine_search_data(df_day_search_result) # 优化下数据展示
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
                    found_row = dbManager.db_refine_search_data(found_row) # 优化下数据展示
                    draw_dataframe(found_row,heightIn=0)

            else:
                # 【时间线速查功能】
                # 获取选择的时间，查询对应时间下有无视频，有则换算与定位
                day_full_select_datetime = utils.merge_date_day_datetime_together(st.session_state.day_date_input,st.session_state.day_time_select_24h) #合并时间为dt
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
                        found_row = dbManager.db_refine_search_data(found_row) # 优化下数据展示
                        draw_dataframe(found_row,heightIn=0)
                    else:
                        st.warning("磁盘上没有找到这个时间的视频文件和索引记录。", icon="🦫")


    else:
        # 数据库中没有今天的记录
        # 判断videos下有无今天的视频文件
        if files.find_filename_in_dir("videos",utils.datetime_to_dateDayStr(dt_in)):
            st.info("数据库中没有这一天的数据索引。不过，磁盘上有这一天的视频还未索引，请前往「设置」进行索引。→", icon="📎")
        else:
            st.info("没有找到这一天的数据索引和视频文件。", icon="🎐")






# tab：全局关键词搜索
with tab2:
    st.markdown(d_lang[config.lang]["tab_search_title"])
    col1, col2 = st.columns([1, 2])
    with col1:
        web_onboarding()

        col1a, col2a, col3a = st.columns([3, 2, 1])
        with col1a:
            search_content = st.text_input(d_lang[config.lang]["tab_search_compname"], 'Hello')
        with col2a:
            # 时间搜索范围组件
            latest_record_time_int = dbManager.db_latest_record_time()
            earlist_record_time_int = dbManager.db_first_earliest_record_time()
            search_date_range_in, search_date_range_out = st.date_input(
                d_lang[config.lang]["tab_search_daterange"],
                (datetime.datetime(1970, 1, 2)
                    + datetime.timedelta(seconds=earlist_record_time_int)
                    - datetime.timedelta(seconds=86400),
                datetime.datetime(1970, 1, 2)
                    + datetime.timedelta(seconds=latest_record_time_int)
                    - datetime.timedelta(seconds=86400)
                ),
                format="YYYY-MM-DD"
            )
        with col3a:
            # 翻页
            if 'max_page_count' not in st.session_state:
                st.session_state.max_page_count = 1
            page_index = st.number_input("搜索结果页数", min_value=1, step=1,max_value=st.session_state.max_page_count+1) - 1

        # 获取数据
        df,all_result_counts,st.session_state.max_page_count = dbManager.db_search_data(search_content, search_date_range_in, search_date_range_out,
                                      page_index)
        df = dbManager.db_refine_search_data(df)
        is_df_result_exist = len(df)
        st.markdown(f"`搜索到 {all_result_counts} 条、共 {st.session_state.max_page_count} 页关于 \"{search_content}\" 的结果。`")

        # 滑杆选择
        result_choose_num = choose_search_result_num(df, is_df_result_exist)

        if len(df) == 0:
            st.info(d_lang[config.lang]["tab_search_word_no"].format(search_content=search_content), icon="🎐")

        else:
            # 打表
            draw_dataframe(df,heightIn=800)

    with col2:
        # 选择视频
        show_n_locate_video_timestamp_by_df(df, result_choose_num)




with tab3:
    
    col1, col2 = st.columns([1,2])
    with col1:
        st.markdown("### 当月数据统计")
        col1a, col2a, col3a = st.columns([.5,.5,1])
        with col1a:
            st.number_input(label="Stat_query_Year",min_value=2020,max_value=2024,value=2023,label_visibility="collapsed")
        with col2a:
            st.number_input(label="Stat_query_Month",min_value=1,max_value=12,value=9,label_visibility="collapsed")
        with col3a:
            st.button("回到本月")
    with col2:
        st.markdown("### 记忆摘要")
        st.button("生成/更新本月词云")
        st.write("词云")


with tab4:
    st.markdown(d_lang[config.lang]["tab_record_title"])

    col1c, col2c = st.columns([1, 2])
    with col1c:
        # 检查录屏服务有无进行中
        # todo：持续、自动探测服务状态？

        # 管理刷新服务的按钮状态：手动管理状态，polyfill streamlit只能读按钮是否被按下的问题（一旦有其他按钮按下，其他按钮就会回弹导致持续的逻辑重置、重新加载）
        # todo：去掉需要双击的操作……
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

        
        btn_refresh = st.button("刷新服务状态 ⟳",on_click=update_record_btn_state)

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
        st.write('WIP')

        if 'is_create_startup_shortcut' not in st.session_state:
            st.session_state.is_create_startup_shortcut = record.is_file_already_in_startup('start_record.bat.lnk')
        st.session_state.is_create_startup_shortcut = st.checkbox(
            '开机后自动开始录制', value=record.is_file_already_in_startup('start_record.bat.lnk'), 
            on_change=record.create_startup_shortcut(is_create=st.session_state.is_create_startup_shortcut))

        
        st.checkbox('当画面一段时间没有变化时暂停录制，直到画面开始改变', value=False)
        st.number_input('画面没有变化的第几分钟暂停录制', value=5, min_value=1)

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary",key="SaveBtnRecord"):
            st.toast("已应用更改。", icon="🦝")
            time.sleep(2)
            st.experimental_rerun()


    with col2c:
        st.write("WIP")


def update_database_clicked():
    st.session_state.update_button_disabled = True


with tab5:
    st.markdown(d_lang[config.lang]["tab_setting_title"])

    col1b, col2b = st.columns([1, 2])
    with col1b:
        # 更新数据库
        st.markdown(d_lang[config.lang]["tab_setting_db_title"])

        # 绘制数据库提示横幅
        draw_db_status()

        col1, col2 = st.columns([1, 1])
        with col1:
            update_db_btn = st.button(d_lang[config.lang]["tab_setting_db_btn"], type="primary", key='update_button_key',
                                      disabled=st.session_state.get("update_button_disabled", False),
                                      on_click=update_database_clicked)
            is_shutdown_pasocon_after_updatedDB = st.checkbox('更新完毕后关闭计算机', value=False)
        
        with col2:
            # 设置ocr引擎
            check_ocr_engine()
            config_ocr_engine = st.selectbox('本地 OCR 引擎', ('Windows.Media.Ocr.Cli', 'ChineseOCR_lite_onnx'),
                                             index=config_ocr_engine_choice_index,
                                             help="（待补充描述）推荐使用 Windows.Media.Ocr.Cli")

            # 设置排除词
            exclude_words = st.text_area("当 OCR 存在以下词语时跳过索引",value=utils.list_to_string(config.exclude_words),help="当有些画面/应用不想被索引时，可以在此添加它们可能出现的关键词，以半角逗号“, ”分割。比如不想记录在 捕风记录仪 的查询画面，可以添加“, 捕风记录仪”。")
            

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

        # 自动化维护选项 WIP
        st.markdown(d_lang[config.lang]["tab_setting_maintain_title"])
        st.write("WIP")
        ocr_strategy_option_dict = {
            "不自动更新，仅手动更新":0,
            "视频切片录制完毕时自动索引":1
        }
        ocr_strategy_option = st.selectbox('OCR 索引策略',
                     (list(ocr_strategy_option_dict.keys())),
                     index=config.OCR_index_strategy
                     )
        col1c,col2c = st.columns([1,1])
        with col1c:
            config_vid_store_day = st.number_input(d_lang[config.lang]["tab_setting_m_vid_store_time"], min_value=1, value=config.config_vid_store_day)
        with col2c:
            st.number_input("原视频在保留几天后进行二次压缩（0 为永不压缩）",value=10,min_value=0)

        st.divider()


        # 界面设置组
        st.markdown(d_lang[config.lang]["tab_setting_ui_title"])

        # 每页结果最大数量
        config_max_search_result_num = st.number_input(d_lang[config.lang]["tab_setting_ui_result_num"], min_value=1,
                                                       max_value=500, value=config.max_page_result)

        # 选择语言
        lang_choice = OrderedDict((k, '' + v) for k, v in lang_map.items())   #根据读入列表排下序
        language_option = st.selectbox(
            'Interface Language / 更改显示语言',
            (list(lang_choice.values())),
            index=lang_index)

        st.divider()

        if st.button('Save and Apple All Change / 保存并应用所有更改', type="primary",key="SaveBtnGeneral"):
            config_set_lang(language_option)
            config.set_and_save_config("OCR_index_strategy",ocr_strategy_option_dict[ocr_strategy_option])
            config.set_and_save_config("config_vid_store_day",config_vid_store_day)
            config.set_and_save_config("max_page_result", config_max_search_result_num)
            config.set_and_save_config("ocr_engine", config_ocr_engine)
            config.set_and_save_config("exclude_words",utils.string_to_list(exclude_words))
            st.toast("已应用更改。", icon="🦝")
            time.sleep(2)
            st.experimental_rerun()

    with col2b:
        st.markdown(
            "关注 [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) on Youtube")

web_footer_state()
