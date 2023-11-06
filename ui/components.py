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

import windrecorder.maintainManager as maintainManager
import windrecorder.record as record
import windrecorder.state as state
import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.dbManager import DBManager
from windrecorder.oneday import OneDay
from windrecorder.utils import get_text as _t


# 检测并渲染onboarding提示
def web_onboarding():
    # 状态懒加载
    if "is_onboarding" not in st.session_state:
        st.session_state["is_onboarding"] = utils.check_is_onboarding()

    if st.session_state.is_onboarding:
        # 数据库不存在，展示 Onboarding 提示
        st.success(_t("text_welcome_to_windrecorder"), icon="😺")
        intro_markdown = Path(f"config\\src\\onboarding_{config.lang}.md").read_text(encoding="utf-8")
        st.markdown(intro_markdown)
        st.divider()


# 显示时间轴
def daily_timeline_html(image_b64):
    st.markdown(
        f"<img style='max-width: 97%;max-height: 100%;margin: 0 0px 5px 50px' src='data:image/png;base64, {image_b64}'/>",
        unsafe_allow_html=True,
    )


# 规范化的打表渲染组件
def video_dataframe(df, heightIn=800):
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
            "ocr_text": st.column_config.TextColumn("ocr_text", width="large"),
            "thumbnail": st.column_config.ImageColumn(
                "thumbnail",
            ),
        },
        height=heightIn,
    )


# 直接定位视频时间码、展示视频
def show_and_locate_video_timestamp_by_filename_and_time(video_file_name, timestamp):
    st.session_state.day_timestamp = int(timestamp)
    # 合并视频文件路径
    videofile_path_month_dir = file_utils.convert_vid_filename_as_YYYY_MM(video_file_name)  # 获取对应的日期目录
    videofile_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, video_file_name)
    print("webui: videofile_path: " + videofile_path)
    # 打开并展示定位视频文件
    video_file = open(videofile_path, "rb")
    video_bytes = video_file.read()
    with st.empty():
        st.video(video_bytes, start_time=st.session_state.day_timestamp)
