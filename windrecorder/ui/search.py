import datetime
import os
import time

import pandas as pd
import streamlit as st

import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.dbManager import DBManager
from windrecorder.ui import components
from windrecorder.utils import get_text as _t


def render():
    search_col, video_col = st.columns([1, 2])
    with search_col:
        # 初始化一些全局状态
        if "db_global_search_result" not in st.session_state:
            st.session_state["db_global_search_result"] = pd.DataFrame()
        if "max_page_count" not in st.session_state:
            st.session_state.max_page_count = 1
        if "all_result_counts" not in st.session_state:
            st.session_state.all_result_counts = 1
        if "search_content" not in st.session_state:
            st.session_state.search_content = ""
        if "search_content_exclude" not in st.session_state:
            st.session_state.search_content_exclude = ""
        if "search_date_range_in" not in st.session_state:
            st.session_state.search_date_range_in = datetime.datetime.today() - datetime.timedelta(seconds=86400)
        if "search_date_range_out" not in st.session_state:
            st.session_state.search_date_range_out = datetime.datetime.today()
        if "cache_videofile_ondisk_list" not in st.session_state:  # 减少io查询，预拿视频文件列表供比对是否存在
            st.session_state.cache_videofile_ondisk_list = file_utils.get_file_path_list(config.record_videos_dir)

        title_col, random_word_btn_col = st.columns([10, 1])
        with title_col:
            st.markdown(_t("gs_md_search_title"))
        with random_word_btn_col:
            # st.selectbox("搜索方式", ('关键词匹配','模糊语义搜索 [不可用]','画面内容搜索 [不可用]'),label_visibility="collapsed")
            if not wordcloud.check_if_word_lexicon_empty():
                if st.button("🎲", use_container_width=True, help=_t("gs_text_randomwalk")):
                    try:
                        st.session_state.search_content = utils.get_random_word_from_lexicon()
                    except Exception as e:
                        print(e)
                        st.session_state.search_content = ""
            st.empty()

        components.web_onboarding()

        # 时间搜索范围组件（懒加载）
        if "search_latest_record_time_int" not in st.session_state:
            st.session_state["search_latest_record_time_int"] = DBManager().db_latest_record_time()
        if "search_earlist_record_time_int" not in st.session_state:
            st.session_state["search_earlist_record_time_int"] = DBManager().db_first_earliest_record_time()

        # 优化streamlit强加载机制导致的索引时间：改变了再重新搜索，而不是每次提交了更改都进行搜索
        if "search_content_lazy" not in st.session_state:
            st.session_state.search_content_lazy = ""
        if "search_content_exclude_lazy" not in st.session_state:
            st.session_state.search_content_exclude_lazy = None
        if "search_date_range_in_lazy" not in st.session_state:
            st.session_state.search_date_range_in_lazy = (
                datetime.datetime(1970, 1, 2)
                + datetime.timedelta(seconds=st.session_state.search_earlist_record_time_int)
                - datetime.timedelta(seconds=86400)
            )
        if "search_date_range_out_lazy" not in st.session_state:
            st.session_state.search_date_range_out_lazy = (
                datetime.datetime(1970, 1, 2)
                + datetime.timedelta(seconds=st.session_state.search_latest_record_time_int)
                - datetime.timedelta(seconds=86400)
            )

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

            (
                st.session_state.db_global_search_result,
                st.session_state.all_result_counts,
                st.session_state.max_page_count,
            ) = DBManager().db_search_data(
                st.session_state.search_content,
                st.session_state.search_date_range_in,
                st.session_state.search_date_range_out,
                keyword_input_exclude=st.session_state.search_content_exclude,
            )

        keyword_col, exclude_col, date_range_col, page_col = st.columns([2, 1, 2, 1])
        with keyword_col:
            st.session_state.search_content = st.text_input(_t("text_search_keyword"), help=_t("gs_input_search_help"))

            do_global_keyword_search()
        with exclude_col:
            st.session_state.search_content_exclude = st.text_input(
                _t("gs_input_exclude"), "", help=_t("gs_input_exclude_help")
            )
            do_global_keyword_search()
        with date_range_col:
            try:
                (
                    st.session_state.search_date_range_in,
                    st.session_state.search_date_range_out,
                ) = st.date_input(
                    _t("text_search_daterange"),
                    (
                        datetime.datetime(1970, 1, 2)
                        + datetime.timedelta(seconds=st.session_state.search_earlist_record_time_int)
                        - datetime.timedelta(seconds=86400),
                        datetime.datetime(1970, 1, 2)
                        + datetime.timedelta(seconds=st.session_state.search_latest_record_time_int)
                        - datetime.timedelta(seconds=86400),
                    ),
                    format="YYYY-MM-DD",
                )
                do_global_keyword_search()
            except Exception:
                st.warning(_t("gs_text_pls_choose_full_date_range"))

        with page_col:
            # 结果翻页器
            st.session_state.page_index = st.number_input(
                _t("gs_input_result_page"),
                min_value=1,
                step=1,
                max_value=st.session_state.max_page_count + 1,
            )

        # 进行搜索
        if not len(st.session_state.search_content) == 0:
            timeCost_globalSearch = time.time()  # 预埋计算实际时长

            df = DBManager().db_search_data_page_turner(st.session_state.db_global_search_result, st.session_state.page_index)

            is_df_result_exist = len(df)

            st.markdown(
                _t("gs_md_search_result_stat").format(
                    all_result_counts=st.session_state.all_result_counts,
                    max_page_count=st.session_state.max_page_count,
                    search_content=st.session_state.search_content,
                    timeCost=timeCost_globalSearch,
                )
            )

            # 滑杆选择
            result_choose_num = result_selector(df, is_df_result_exist)

            if len(df) == 0:
                st.info(
                    _t("text_search_not_found").format(search_content=st.session_state.search_content),
                    icon="🎐",
                )
            else:
                # 打表
                df = DBManager().db_refine_search_data_global(
                    df,
                    cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list,
                )  # 优化数据显示
                components.video_dataframe(df, heightIn=800)

            timeCost_globalSearch = round(time.time() - timeCost_globalSearch, 5)
            st.markdown(_t("gs_md_search_result_below").format(timecost=timeCost_globalSearch))

        else:
            st.info(_t("gs_text_intro"))

    with video_col:
        # 选择视频
        if not len(st.session_state.search_content) == 0:
            show_and_locate_video_timestamp_by_df(df, result_choose_num)
        else:
            st.empty()


# 选择播放视频的行数 的滑杆组件
def result_selector(df, result_cnt):
    if result_cnt == 1:
        # 如果结果只有一个，直接显示结果而不显示滑杆
        return 0
    elif result_cnt > 1:
        # shape是一个元组,索引0对应行数,索引1对应列数。
        # df.shape[0]
        # print("webui: total_raw:" + str(total_raw))

        slider_min_num_display = df.index.min()
        slider_max_num_display = df.index.max()
        select_num = slider_min_num_display

        # 使用滑杆选择视频
        col1, col2 = st.columns([5, 1])
        with col1:
            select_num = st.slider(
                _t("gs_slider_to_rewind_result"),
                slider_min_num_display,
                slider_max_num_display,
                select_num,
            )
        with col2:
            select_num = st.number_input(
                _t("gs_slider_to_rewind_result"),
                label_visibility="hidden",
                min_value=slider_min_num_display,
                max_value=slider_max_num_display,
                value=select_num,
            )

        select_num_real = select_num - slider_min_num_display  # 将绝对范围转换到从0开始的相对范围

        return select_num_real
    else:
        return 0


# 通过表内搜索结果定位视频时间码，展示视频
def show_and_locate_video_timestamp_by_df(df, num):
    # 入参：df，滑杆选择到表中的第几项
    if len(df) == 0:
        return

    # todo 获取有多少行结果 对num进行合法性判断
    videofile_path_month_dir = file_utils.convert_vid_filename_as_YYYY_MM(df.iloc[num]["videofile_name"])  # 获取对应的日期目录
    videofile_path = os.path.join(
        config.record_videos_dir,
        videofile_path_month_dir,
        file_utils.add_OCRED_suffix(df.iloc[num]["videofile_name"]),
    )
    videofile_path_COMPRESS = os.path.join(
        config.record_videos_dir,
        videofile_path_month_dir,
        file_utils.add_COMPRESS_OCRED_suffix(df.iloc[num]["videofile_name"]),
    )
    print("webui: videofile_path: " + videofile_path)
    vid_timestamp = utils.calc_vid_inside_time(df, num)
    print("webui: vid_timestamp: " + str(vid_timestamp))

    st.session_state.vid_vid_timestamp = 0
    st.session_state.vid_vid_timestamp = vid_timestamp
    # st.session_state.vid_vid_timestamp
    # 判断视频文件是否存在
    if os.path.isfile(videofile_path):  # 是否存在未压缩的
        video_file = open(videofile_path, "rb")
        video_bytes = video_file.read()
        with st.empty():
            st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
        st.markdown(f"`{videofile_path}`")
    elif os.path.isfile(videofile_path_COMPRESS):  # 是否存在已压缩的
        video_file = open(videofile_path_COMPRESS, "rb")
        video_bytes = video_file.read()
        with st.empty():
            st.video(video_bytes, start_time=st.session_state.vid_vid_timestamp)
        st.markdown(f"`{videofile_path_COMPRESS}`")
    else:
        st.warning(f"Video File **{videofile_path}** not on disk.", icon="🦫")
