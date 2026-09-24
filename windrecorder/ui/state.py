import calendar
import datetime
import os

import streamlit as st
from PIL import Image

import windrecorder.state as state
import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.llm import component_month_poem
from windrecorder.record_wintitle import component_month_wintitle_stat
from windrecorder.ui.components import html_picture
from windrecorder.utils import get_text as _t


def render():
    state_col, memory_col = st.columns([1, 2])
    with state_col:
        first = db_manager.db_first_earliest_record_time()
        latest = db_manager.db_latest_record_time()
        if first is None or latest is None:
            st.info(_t("stat_text_no_records"))
            return
        st.session_state.stat_db_earliest_datetime = utils.seconds_to_datetime(first)
        st.session_state.stat_db_latest_datetime = utils.seconds_to_datetime(latest)

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
        get_show_month_data_state(st.session_state.stat_select_month_datetime)
        has_month_data = bool(st.session_state.df_month_stat.data_count.sum())
        if not has_month_data:
            st.info(_t("stat_text_no_month_data"))

        stat_year_title = st.session_state.stat_select_month_datetime.year
        st.markdown(_t("stat_md_year_title").format(stat_year_title=stat_year_title))
        get_show_year_data_state(st.session_state.stat_select_month_datetime)  # 显示当年概览

    with memory_col:
        st.markdown(_t("stat_md_memory_title"))

        col1_mem, col2_mem = st.columns([1, 1])
        with col1_mem:
            st.empty()
            if has_month_data:
                component_month_wintitle_stat(st.session_state.stat_select_month_datetime)

        with col2_mem:
            # light box
            current_month_lightbox_img_name = (
                str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            )
            current_month_lightbox_img_path = os.path.join(config.lightbox_result_dir_ud, current_month_lightbox_img_name)

            if st.button(_t("stat_btn_generate_lightbox"), disabled=not has_month_data):
                with st.spinner(_t("stat_text_generating_lightbox")):
                    _dt_lightbox = st.session_state.stat_select_month_datetime
                    _month_days = calendar.monthrange(_dt_lightbox.year, _dt_lightbox.month)[1]
                    state.generate_lightbox_from_datetime_range(
                        dt_month_start=datetime.datetime(_dt_lightbox.year, _dt_lightbox.month, 1),
                        dt_month_end=datetime.datetime(_dt_lightbox.year, _dt_lightbox.month, _month_days, 23, 59, 59),
                        img_saved_name=current_month_lightbox_img_name,
                    )
                    if f"html_pic_b64_cache_{current_month_lightbox_img_name}" in st.session_state:
                        del st.session_state[f"html_pic_b64_cache_{current_month_lightbox_img_name}"]

            if os.path.exists(current_month_lightbox_img_path):
                st.caption(_t("stat_text_custom_lightbox"))
                html_picture(current_month_lightbox_img_path, caption=current_month_lightbox_img_path)
                # image = Image.open(current_month_lightbox_img_path)
                # st.image(image, caption=current_month_lightbox_img_path)
            else:
                st.info(_t("stat_text_no_month_lightbox"))

            # ai poem
            if config.enable_ai_day_poem and has_month_data:
                component_month_poem(st.session_state.stat_select_month_datetime)

            # word cloud
            current_month_cloud_img_name = (
                str(st.session_state.Stat_query_Year) + "-" + str(st.session_state.Stat_query_Month) + ".png"
            )
            current_month_cloud_img_path = os.path.join(config.wordcloud_result_dir_ud, current_month_cloud_img_name)

            if st.button(_t("stat_btn_generate_update_word_cloud"), disabled=not has_month_data):
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


def get_show_month_data_state(stat_select_month_datetime: datetime.datetime):
    with st.spinner(_t("text_updating_month_stat")):
        st.session_state.df_month_stat = state.get_cached_calendar_overview(stat_select_month_datetime, "month")
    st.scatter_chart(st.session_state.df_month_stat, x="day", y="hours", size="data_count", color="#AC79D5")


def get_show_year_data_state(stat_select_year_datetime: datetime.datetime):
    with st.spinner(_t("text_updating_yearly_stat")):
        st.session_state.df_year_stat = state.get_cached_calendar_overview(stat_select_year_datetime, "year")
    st.scatter_chart(st.session_state.df_year_stat, x="month", y="day", size="data_count", color="#C873A6", height=350)
