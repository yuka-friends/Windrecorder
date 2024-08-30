# Set workspace to Windrecorder dir
import datetime
import os
import sys

import streamlit as st

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.db_manager import db_manager  # NOQA: E402

# from windrecorder.state import generate_month_lightbox    # NOQA: E402
from windrecorder.ui.search import ui_component_date_range_selector  # NOQA: E402

st.set_page_config(page_title="Create custom lightbox - Windrecord - webui", page_icon="🦝", layout="wide")


def init_st_state():
    # 初始化时间搜索范围组件（懒加载）
    if "search_latest_record_time_int" not in st.session_state:
        st.session_state["search_latest_record_time_int"] = db_manager.db_latest_record_time()
    if "search_earlist_record_time_int" not in st.session_state:
        st.session_state["search_earlist_record_time_int"] = db_manager.db_first_earliest_record_time()
    if "search_date_range_in" not in st.session_state:
        st.session_state.search_date_range_in = datetime.datetime.today() - datetime.timedelta(seconds=86400)
    if "search_date_range_out" not in st.session_state:
        st.session_state.search_date_range_out = datetime.datetime.today()


def generate_lightbox_data_range(is_add_watermark=True):
    pass


def ui_custom_data_range():
    data_range_type_lst = ["大致月份范围", "精确日期范围"]
    data_range_type = st.radio("日期选择器", data_range_type_lst, label_visibility="collapsed")
    if data_range_type == data_range_type_lst[0]:
        ui_component_date_range_selector(data_type="month_range")
    elif data_range_type == data_range_type_lst[1]:
        ui_component_date_range_selector(data_type="exact_date")

    col_L_params, col_R_params = st.columns([1, 1])
    with col_L_params:
        width_thumbnail_num = st.number_input("横向缩略图数量", min_value=5, max_value=1000, value=25, step=1)
    with col_R_params:
        height_thumbnail_num = st.number_input("纵向缩略图数量", min_value=5, max_value=1000, value=35, step=1)
    st.markdown(f"包含缩略图总数：`{width_thumbnail_num*height_thumbnail_num}`")
    is_add_watermark = st.checkbox("添加底部水印信息")
    if st.button("创建图片", use_container_width=True, type="primary"):
        generate_lightbox_data_range(is_add_watermark=is_add_watermark)


def main_webui():
    st.markdown("#### 自定义光箱生成器")
    col_L, col_R = st.columns([1, 3])
    with col_L:
        st.empty()
        lightbox_generate_type_lst = ["自定义时间段", "月份内每日时间轴"]
        lightbox_generate_type = st.selectbox("光箱类型", lightbox_generate_type_lst, index=0, label_visibility="collapsed")
        if lightbox_generate_type == lightbox_generate_type_lst[0]:
            ui_custom_data_range()
    with col_R:
        st.empty()


init_st_state()
main_webui()
