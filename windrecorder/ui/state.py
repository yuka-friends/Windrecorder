import datetime
import os

import pandas as pd
import streamlit as st
from PIL import Image

import windrecorder.state as state
import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.utils import get_text as _t


def render():
    state_col, memory_col = st.columns([1, 2])
    with state_col:
        # 懒加载
        if "stat_db_earliest_datetime" not in st.session_state:
            st.session_state["stat_db_earliest_datetime"] = utils.seconds_to_datetime(
                db_manager.db_first_earliest_record_time()
            )
        if "stat_db_latest_datetime" not in st.session_state:
            st.session_state["stat_db_latest_datetime"] = utils.seconds_to_datetime(db_manager.db_latest_record_time())

        st.markdown(_t("stat_md_month_title"))
        # 年月时间选择器
        col_year_selector, col_month_selector, col_blank = st.columns([0.5, 0.5, 1])
        with col_year_selector:
            st.session_state.Stat_query_Year = st.number_input(
                label="Stat_query_Year",
                min_value=st.session_state.stat_db_earliest_datetime.year,
                max_value=st.session_state.stat_db_latest_datetime.year,
                value=st.session_state.stat_db_latest_datetime.year,
                label_visibility="collapsed",
            )

        # 根据传入的年份，计算当年最早与最晚有数据的月份
        select_year_earliest_datetime = (
            st.session_state.stat_db_earliest_datetime
            if st.session_state.Stat_query_Year == st.session_state.stat_db_earliest_datetime.year
            else datetime.datetime(st.session_state.Stat_query_Year, 1, 1)
        )
        select_year_latest_datetime = (
            st.session_state.stat_db_latest_datetime
            if st.session_state.Stat_query_Year == st.session_state.stat_db_latest_datetime.year
            else datetime.datetime(st.session_state.Stat_query_Year, 12, 31)
        )

        with col_month_selector:
            st.session_state.Stat_query_Month = st.number_input(
                label="Stat_query_Month",
                min_value=select_year_earliest_datetime.month,
                max_value=select_year_latest_datetime.month,
                value=select_year_latest_datetime.month,
                label_visibility="collapsed",
            )
        with col_blank:
            st.empty()

        st.session_state.stat_select_month_datetime = datetime.datetime(
            st.session_state.Stat_query_Year,
            st.session_state.Stat_query_Month,
            1,
            10,
            0,
            0,
        )
        get_show_month_data_state(st.session_state.stat_select_month_datetime)  # 显示当月概览

        stat_year_title = st.session_state.stat_select_month_datetime.year
        st.markdown(_t("stat_md_year_title").format(stat_year_title=stat_year_title))
        get_show_year_data_state(st.session_state.stat_select_month_datetime)  # 显示当年概览

    with memory_col:
        st.markdown(_t("stat_md_memory_title"))

        col1_mem, col2_mem = st.columns([1, 1])
        with col1_mem:
            current_month_cloud_img_name = (
                str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            )
            current_month_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_month_cloud_img_name)

            if st.button(_t("stat_btn_generate_update_word_cloud")):
                with st.spinner(_t("stat_text_generating_word_cloud")):
                    wordcloud.generate_word_cloud_in_month(
                        utils.datetime_to_seconds(st.session_state.stat_select_month_datetime),
                        current_month_cloud_img_name,
                    )

            if os.path.exists(current_month_cloud_img_path):
                image = Image.open(current_month_cloud_img_path)
                st.image(image, caption=current_month_cloud_img_path)
            else:
                st.info(_t("stat_text_no_month_word_cloud_pic"))

        with col2_mem:
            current_month_lightbox_img_name = (
                str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            )
            current_month_lightbox_img_path = os.path.join(config.lightbox_result_dir, current_month_lightbox_img_name)

            if st.button(_t("stat_btn_generate_lightbox")):
                with st.spinner(_t("stat_text_generating_lightbox")):
                    state.generate_month_lightbox(
                        st.session_state.stat_select_month_datetime,
                        img_saved_name=current_month_lightbox_img_name,
                    )

            if os.path.exists(current_month_lightbox_img_path):
                image = Image.open(current_month_lightbox_img_path)
                st.image(image, caption=current_month_lightbox_img_path)
            else:
                st.info(_t("stat_text_no_month_lightbox"))


# 生成并显示每月数据量概览
def get_show_month_data_state(stat_select_month_datetime: datetime.datetime):
    if "df_month_stat" not in st.session_state:  # 初始化显示的表状态
        st.session_state.df_month_stat = pd.DataFrame()
    if "df_month_stat_dt" not in st.session_state:  # 初始化当前显示表的日期
        st.session_state.df_month_stat_dt = stat_select_month_datetime

    df_file_name = stat_select_month_datetime.strftime("%Y-%m") + "_month_data_state.csv"
    df_cache_dir = "cache"
    df_filepath = os.path.join(df_cache_dir, df_file_name)

    update_condition = False
    if not st.session_state.df_month_stat.empty and utils.set_full_datetime_to_YYYY_MM(
        st.session_state.df_month_stat_dt
    ) <= utils.set_full_datetime_to_YYYY_MM(st.session_state.stat_select_month_datetime):
        update_condition = True

    if (
        st.session_state.df_month_stat.empty
        or update_condition
        or utils.set_full_datetime_to_YYYY_MM(st.session_state.df_month_stat_dt)
        != utils.set_full_datetime_to_YYYY_MM(st.session_state.stat_select_month_datetime)
    ):  # 页面内无缓存，或不是当月日期
        # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):  # 存在
            if df_file_name[:7] == datetime.datetime.today().strftime("%Y-%m"):  # 如果是需要时效性的当下月数据
                if not file_utils.is_file_modified_recently(df_filepath, time_gap=120):  # 超过120分钟未更新，过时 重新生成
                    # 更新操作
                    with st.spinner(_t("text_updating_month_stat")):
                        st.session_state.df_month_stat = state.get_month_day_overview_scatter(stat_select_month_datetime)
                        file_utils.save_dataframe_to_path(st.session_state.df_month_stat, file_path=df_filepath)
            # 进行读取操作
            st.session_state.df_month_stat = file_utils.read_dataframe_from_path(file_path=df_filepath)

        else:  # 磁盘上不存在缓存
            with st.spinner(_t("text_updating_month_stat")):
                st.session_state.df_month_stat = state.get_month_day_overview_scatter(stat_select_month_datetime)
                file_utils.save_dataframe_to_path(st.session_state.df_month_stat, file_path=df_filepath)

    st.scatter_chart(
        st.session_state.df_month_stat,
        x="day",
        y="hours",
        size="data_count",
        color="#AC79D5",
    )


# 生成并显示每年数据量概览
def get_show_year_data_state(stat_select_year_datetime: datetime.datetime):
    if "df_year_stat" not in st.session_state:  # 初始化显示的表状态
        st.session_state.df_year_stat = pd.DataFrame()

    df_file_name = stat_select_year_datetime.strftime("%Y") + "_year_data_state.csv"
    df_cache_dir = "cache"
    df_filepath = os.path.join(df_cache_dir, df_file_name)

    if st.session_state.df_year_stat.empty:  # 页面内无缓存
        # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(df_filepath):  # 存在
            if not file_utils.is_file_modified_recently(df_filepath, time_gap=3000):  # 超过3000分钟未更新，过时 重新生成
                # 更新操作
                with st.spinner(_t("text_updating_yearly_stat")):
                    st.session_state.df_year_stat = state.get_year_data_overview_scatter(stat_select_year_datetime)
                    file_utils.save_dataframe_to_path(st.session_state.df_year_stat, file_path=df_filepath)
            else:
                # 未过时，进行读取操作
                st.session_state.df_year_stat = file_utils.read_dataframe_from_path(file_path=df_filepath)

        else:  # 磁盘上不存在缓存
            with st.spinner(_t("text_updating_yearly_stat")):
                st.session_state.df_year_stat = state.get_year_data_overview_scatter(stat_select_year_datetime)
                file_utils.save_dataframe_to_path(st.session_state.df_year_stat, file_path=df_filepath)

    st.scatter_chart(
        st.session_state.df_year_stat,
        x="month",
        y="day",
        size="data_count",
        color="#C873A6",
        height=350,
    )
