import streamlit as st
from dbManager import dbManager
import os
from os import getpid
import maintainManager
import time
import json
import utils
import datetime
from collections import OrderedDict
import subprocess
from multiprocessing import Semaphore
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx
from pathlib import Path

update_button_key = "update_button"
reset_button_key = "setting_reset"

# python -m streamlit run webui.py
with open('config.json', encoding='utf-8') as f:
    config = json.load(f)
print("config.json:")
print(config)

db_path = config["db_path"]
db_filename = config["db_filename"]
db_filepath = os.path.join(db_path, db_filename)
video_path = config["record_videos_dir"]
lang = config["lang"]

with open("languages.json", encoding='utf-8') as f:
    d_lang = json.load(f)
lang_map = d_lang['lang_map']


# 获取配置中语言选项是第几位；使设置选择项能匹配
def get_language_index(lang, data):
    for i, l in enumerate(data):
        if l == lang:
            return i
    return 1


lang_index = get_language_index(lang, d_lang)

st.set_page_config(
    page_title="Windrecorder",
    page_icon="🦝",
    layout="wide"
)


# 检测是否初次使用工具，如果不存在数据库/数据库中只有一条数据，则判定为是
def check_is_onboarding():
    is_db_existed = dbManager.db_main_initialize()
    if is_db_existed == False:
        return True
    latest_db_records = dbManager.db_num_records()
    if latest_db_records == 1:
        return True
    return False


# 启动定时执行线程
class RepeatingTimer(threading.Thread):
    def __init__(self, interval, function):
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            time.sleep(self.interval)
            self.function()

    def stop(self):
        self.running = False


# 检测录屏服务有没有在运行
state_is_recording = False
# placeholder = st.empty()


def repeat_check_recording():
    with open("lock_file_record", encoding='utf-8') as f:
        check_pid = int(f.read())

    check_result = subprocess.run(['tasklist'], stdout=subprocess.PIPE, text=True)
    check_output = check_result.stdout
    check_result = subprocess.run(['findstr', str(check_pid)], input=check_output, stdout=subprocess.PIPE, text=True)
    check_output = check_result.stdout
    global state_is_recording
    if "python" in check_output:
        state_is_recording = True
    else:
        state_is_recording = False
    print(f"state_is_recording:{state_is_recording}")

    # 试图使用据说可以自动更新的组件来强制刷新状态
    # (https://towardsdatascience.com/creating-dynamic-dashboards-with-streamlit-747b98a68ab5)
    # placeholder.text(
    #     f"state_is_recording:{state_is_recording}")


# 用另外的线程虽然能持续检测到服务有没有运行，但是byd streamlit就是没法自动更新，state只能在主线程访问；
# 用了这个（https://github.com/streamlit/streamlit/issues/1326）讨论中的临时措施
# 虽然可以自动更新了，但还是无法动态更新页面
# 目的：让它可以自动检测服务是否在运行，并且在页面中更新显示状态
# timer_repeat_check_recording = RepeatingTimer(5, repeat_check_recording)
# add_script_run_ctx(timer_repeat_check_recording)
# timer_repeat_check_recording.start()


# 结束录屏服务进程
def kill_recording():
    with open("lock_file_record", encoding='utf-8') as f:
        check_pid = int(f.read())
    check_result = subprocess.run(['taskkill', '/pid', str(check_pid), '-t','-f'], stdout=subprocess.PIPE, text=True)
    st.toast(f"已结束录屏进程，{check_result.stdout}")
    print(f"已结束录屏进程，{check_result.stdout}")


# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def combine_vid_name_withOCR(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 定位视频时间码，展示视频
def show_n_locate_video_timestamp(df, num):
    if is_df_result_exist:
        # todo 获取有多少行结果 对num进行合法性判断
        # todo 判断视频需要存在才能播放
        videofile_path = os.path.join(video_path, combine_vid_name_withOCR(df.iloc[num]['videofile_name']))
        print("videofile_path: " + videofile_path)
        vid_timestamp = calc_vid_inside_time(df, num)
        print("vid_timestamp: " + str(vid_timestamp))

        st.session_state.vid_vid_timestamp = 0
        st.session_state.vid_vid_timestamp = vid_timestamp
        # st.session_state.vid_vid_timestamp
        # 判断视频文件是否存在
        if os.path.isfile(videofile_path):
            video_file = open(videofile_path, 'rb')
            video_bytes = video_file.read()
            st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
        else:
            st.markdown(f"Video File **{videofile_path}** not on disk.")


# 计算视频对应时间戳
def calc_vid_inside_time(df, num):
    fulltime = df.iloc[num]['videofile_time']
    vidfilename = os.path.splitext(df.iloc[num]['videofile_name'])[0]
    vid_timestamp = fulltime - utils.date_to_seconds(vidfilename)
    print("fulltime:" + str(fulltime) + "\n vidfilename:" + str(vidfilename) + "\n vid_timestamp:" + str(vid_timestamp))
    return vid_timestamp


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
            select_num = st.slider(d_lang[lang]["def_search_slider"], 0, total_raw - 1, select_num)
        with col2:
            select_num = st.number_input(d_lang[lang]["def_search_slider"], label_visibility="hidden", min_value=0,
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


# 数据库的前置索引状态提示
def web_db_state_info_before():
    count, nocred_count = web_db_check_folder_marked_file(video_path)
    if nocred_count > 0:
        st.warning(d_lang[lang]["tab_setting_db_state1"].format(nocred_count=nocred_count, count=count), icon='🧭')
        return True
    else:
        st.success(d_lang[lang]["tab_setting_db_state2"].format(nocred_count=nocred_count, count=count), icon='✅')
        return False


# 检查 videos 文件夹内有无以"-OCRED"结尾的视频
def web_db_check_folder_marked_file(folder_path):
    count = 0
    nocred_count = 0
    for filename in os.listdir(folder_path):
        count += 1
        if not filename.split('.')[0].endswith("-OCRED"):
            nocred_count += 1
    return count, nocred_count


# 更改语言
def config_set_lang(lang_name):
    INVERTED_LANG_MAP = {v: k for k, v in lang_map.items()}
    lang_code = INVERTED_LANG_MAP.get(lang_name)

    if not lang_code:
        print(f"Invalid language name: {lang_name}")
        return

    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)

    config['lang'] = lang_code

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


# footer状态信息
def web_footer_state():
    latest_record_time_int = dbManager.db_latest_record_time()
    latest_record_time_str = utils.seconds_to_date(latest_record_time_int)

    latest_db_records = dbManager.db_num_records()

    videos_file_size = round(utils.get_dir_size(video_path) / (1024 * 1024 * 1024), 3)

    # webUI draw
    st.divider()
    # st.markdown(f'Database latest record time: **{latest_record_time_str}**, Database records: **{latest_db_records}**, Video Files on disk: **{videos_file_size} GB**')
    st.markdown(d_lang[lang]["footer_info"].format(latest_record_time_str=latest_record_time_str,
                                                   latest_db_records=latest_db_records,
                                                   videos_file_size=videos_file_size))


# 主界面_________________________________________________________
st.markdown(d_lang[lang]["main_title"])

tab1, tab2, tab3, tab4, tab5 = st.tabs([d_lang[lang]["tab_name_search"], "一天之时","记忆摘要", d_lang[lang]["tab_name_recording"],
                                  d_lang[lang]["tab_name_setting"]])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        is_db_existed = check_is_onboarding()
        if is_db_existed == True:
            # 数据库不存在，展示 Onboarding 提示
            st.success("欢迎使用 Windrecorder！", icon="😺")
            intro_markdown = Path("onboarding.md").read_text(encoding='utf-8')
            st.markdown(intro_markdown)
            st.divider()

        st.markdown(d_lang[lang]["tab_search_title"])

        col1a, col2a, col3a = st.columns([3, 2, 1])
        with col1a:
            search_content = st.text_input(d_lang[lang]["tab_search_compname"], 'Hello')
        with col2a:
            # 时间搜索范围组件
            latest_record_time_int = dbManager.db_latest_record_time()
            search_date_range_in, search_date_range_out = st.date_input(
                d_lang[lang]["tab_search_daterange"],
                (datetime.datetime(2000, 1, 2)
                    + datetime.timedelta(seconds=latest_record_time_int)
                    - datetime.timedelta(seconds=86400),
                datetime.datetime.now()),
                format="YYYY-MM-DD"
            )
        with col3a:
            # 翻页
            page_index = st.number_input("搜索结果页数", min_value=1, step=1) - 1

        # 获取数据
        df = dbManager.db_search_data(search_content, search_date_range_in, search_date_range_out,
                                      page_index)
        df = dbManager.db_refine_search_data(df)
        is_df_result_exist = len(df)

        # 滑杆选择
        result_choose_num = choose_search_result_num(df, is_df_result_exist)

        if len(df) == 0:
            st.info(d_lang[lang]["tab_search_word_no"].format(search_content=search_content), icon="🎐")

        else:
            # 打表
            st.dataframe(
                df,
                column_config={
                    "is_videofile_exist": st.column_config.CheckboxColumn(
                        "is_videofile_exist",
                        help=d_lang[lang]["tab_search_table_help1"],
                        default=False,
                    ),
                    "ocr_text": st.column_config.TextColumn(
                        "ocr_text",
                        help=d_lang[lang]["tab_search_table_help2"],
                        width="large"
                    ),
                    "thumbnail": st.column_config.ImageColumn(
                        "thumbnail",
                        help=d_lang[lang]["tab_search_table_help3"]
                    )

                },
                height=800
            )

    with col2:
        # 选择视频
        show_n_locate_video_timestamp(df, result_choose_num)

with tab2:
    st.write("WIP")

with tab3:
    st.write("WIP")

with tab4:
    st.markdown(d_lang[lang]["tab_record_title"])

    col1c, col2c = st.columns([1, 3])
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
            if st.session_state.update_btn_refresh_press == True:
                st.session_state.update_btn_refresh_press = False
            else:
                st.session_state.update_btn_refresh_press = True
            st.session_state.update_btn_dis_record = False

        
        btn_refresh = st.button("刷新服务状态 ⟳",on_click=update_record_btn_state)

        if st.session_state.update_btn_refresh_press == True :
            repeat_check_recording() # 检测有无运行

            if state_is_recording:
                st.success("正在持续录制屏幕……  请刷新查看最新运行状态。", icon="🦚")
                stop_record_btn = st.button('停止录制屏幕', type="secondary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                if stop_record_btn:
                    st.toast("正在结束录屏进程……")
                    kill_recording()
                    
            else:
                st.error("当前未在录制屏幕。  请刷新查看最新运行状态。", icon="🦫")
                start_record_btn = st.button('开始持续录制', type="primary",disabled=st.session_state.get("update_btn_dis_record",False),on_click=update_record_service_btn_clicked)
                if start_record_btn:
                    os.startfile('start_record.bat', 'open')
                    st.toast("启动录屏中……")
                    st.session_state.update_btn_refresh_press = False





        # st.warning("录制服务已启用。当前暂停录制屏幕。",icon="🦫")
        st.divider()
        st.checkbox('开机后自动开始录制', value=False)
        st.checkbox('当鼠标一段时间没有移动时暂停录制，直到鼠标开始移动', value=False)
        st.number_input('鼠标停止移动的第几分钟暂停录制', value=5, min_value=1)

    with col2c:
        st.write("WIP")


def update_database_clicked():
    st.session_state.update_button_disabled = True


with tab5:
    st.markdown(d_lang[lang]["tab_setting_title"])

    col1b, col2b = st.columns([1, 3])
    with col1b:
        # 更新数据库
        st.markdown(d_lang[lang]["tab_setting_db_title"])
        need_to_update_db = web_db_state_info_before()

        col1, col2 = st.columns([1, 1])
        with col1:
            update_db_btn = st.button(d_lang[lang]["tab_setting_db_btn"], type="primary", key='update_button_key',
                                      disabled=st.session_state.get("update_button_disabled", False),
                                      on_click=update_database_clicked)
            is_shutdown_pasocon_after_updatedDB = st.checkbox('更新完毕后关闭计算机', value=False)

            if update_db_btn:
                try:
                    with st.spinner(d_lang[lang]["tab_setting_db_tip1"]):
                        timeCost = time.time()
                        # todo 给出预估剩余时间
                        maintainManager.maintain_manager_main()

                        timeCost = time.time() - timeCost
                except Exception as ex:
                    st.exception(ex)
                    # st.write(f'Something went wrong!: {ex}')
                else:
                    st.write(d_lang[lang]["tab_setting_db_tip3"].format(timeCost=timeCost))
                finally:
                    if is_shutdown_pasocon_after_updatedDB:
                        subprocess.run(["shutdown", "-s", "-t", "60"], shell=True)
                    st.snow()
                    st.session_state.update_button_disabled = False
                    st.button(d_lang[lang]["tab_setting_db_btn_gotit"], key=reset_button_key)
        with col2:
            if config["ocr_engine"] == "Windows.Media.Ocr.Cli":
                config_ocr_engine_choice_index = 0
            elif config["ocr_engine"] == "ChineseOCR_lite_onnx":
                config_ocr_engine_choice_index = 1
            config_ocr_engine = st.selectbox('本地 OCR 引擎', ('Windows.Media.Ocr.Cli', 'ChineseOCR_lite_onnx'),
                                             index=config_ocr_engine_choice_index)

        st.divider()

        # 自动化维护选项 WIP
        st.markdown(d_lang[lang]["tab_setting_maintain_title"])
        st.selectbox('OCR 索引策略',
                     ('计算机空闲时自动索引', '每录制完一个视频切片就自动更新一次', '不自动更新，仅手动更新')
                     )
        config_vid_store_day = st.number_input(d_lang[lang]["tab_setting_m_vid_store_time"], min_value=1, value=90)

        st.divider()

        # 选择语言
        st.markdown(d_lang[lang]["tab_setting_ui_title"])

        config_max_search_result_num = st.number_input(d_lang[lang]["tab_setting_ui_result_num"], min_value=1,
                                                       max_value=500, value=config["max_page_result"])

        lang_choice = OrderedDict((k, '' + v) for k, v in lang_map.items())
        language_option = st.selectbox(
            'Interface Language / 更改显示语言',
            (list(lang_choice.values())),
            index=lang_index)

        st.divider()

        if st.button('Apple All Change / 应用所有更改', type="primary"):
            config_set_lang(language_option)
            utils.config_set("max_page_result", config_max_search_result_num)
            utils.config_set("ocr_engine", config_ocr_engine)
            st.toast("已应用更改。", icon="🦝")
            st.experimental_rerun()

    with col2b:
        st.markdown(
            "关注 [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) on Youtube")

web_footer_state()
