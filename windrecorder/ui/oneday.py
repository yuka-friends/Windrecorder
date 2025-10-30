import datetime
import os

import pandas as pd
import streamlit as st

from windrecorder import file_utils, flag_mark_note, utils
from windrecorder.config import config
from windrecorder.const import (
    SCREENSHOT_CACHE_FILEPATH,
    SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME,
)
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger
from windrecorder.oneday import OneDay
from windrecorder.ui import components
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)


def render():
    # onboarding checking
    if "is_onboarding" not in st.session_state:
        st.session_state["is_onboarding"] = db_manager.check_is_onboarding()

    if st.session_state.is_onboarding:
        col1, col2 = st.columns([1, 2])
        with col1:
            components.web_onboarding()
        with col2:
            st.empty()

    # 标题 # todo:添加今天是星期几以增强时间观念

    # 日期选择器
    if "day_date_input" not in st.session_state:
        st.session_state["day_date_input"] = datetime.date.today() - (
            datetime.timedelta(days=1)
            if (datetime.datetime.now() - datetime.datetime.now().replace(hour=0, minute=0, second=0))
            < datetime.timedelta(minutes=config.day_begin_minutes)
            else datetime.timedelta(seconds=0)
        )  # 如果在分隔时间内则矫正到缺省选择昨天

    (
        title_col,
        yesterday_col,
        tomorrow_col,
        today_col,
        date_col,
        spacing_col,
        search_col,
    ) = st.columns([0.4, 0.25, 0.25, 0.15, 0.25, 0.2, 1])
    with title_col:
        st.markdown(_t("oneday_title"))
    with yesterday_col:
        if st.button(_t("oneday_btn_yesterday"), use_container_width=True):
            st.session_state.day_date_input -= datetime.timedelta(days=1)
    with tomorrow_col:
        if st.button(_t("oneday_btn_tomorrow"), use_container_width=True):
            st.session_state.day_date_input += datetime.timedelta(days=1)
    with today_col:
        if st.button(_t("oneday_btn_today"), use_container_width=True):
            st.session_state.day_date_input = datetime.date.today()
            if (datetime.datetime.now().hour < config.day_begin_minutes // 60) or (
                datetime.datetime.now().hour == config.day_begin_minutes // 60
                and datetime.datetime.now().minute < config.day_begin_minutes % 60
            ):
                st.session_state.day_date_input -= datetime.timedelta(days=1)
    with date_col:
        st.session_state.day_date_input = st.date_input(
            "Today Date",
            label_visibility="collapsed",
            value=st.session_state.day_date_input,
        )

        # 获取输入的日期
        # 清理格式到HMS
        begin_day = config.day_begin_minutes
        dt_in = datetime.datetime(
            st.session_state.day_date_input.year,
            st.session_state.day_date_input.month,
            st.session_state.day_date_input.day,
            begin_day // 60,
            begin_day % 60,
            0,
        )
        # 检查数据库中关于今天的数据
        (
            day_has_data,
            day_noocred_count,
            day_search_result_num,
            day_min_timestamp_dt,
            day_max_timestamp_dt,
            day_df,
        ) = OneDay().checkout_daily_data_meta(dt_in)
        # 如果有比数据库更早或更晚的截图数据，则使用其范围
        if config.record_mode == "screenshot_array":
            earliest_screenshot_dt, latest_screenshot_dt = OneDay().find_earliest_latest_screenshots_cache_datetime_via_date(
                st.session_state.day_date_input
            )
            if earliest_screenshot_dt and latest_screenshot_dt and day_min_timestamp_dt and day_max_timestamp_dt:
                if day_min_timestamp_dt > earliest_screenshot_dt and earliest_screenshot_dt > datetime.datetime(
                    earliest_screenshot_dt.year,
                    earliest_screenshot_dt.month,
                    earliest_screenshot_dt.day,
                    int(config.day_begin_minutes / 60),
                    int(config.day_begin_minutes % 60),
                    0,
                ):
                    day_min_timestamp_dt = earliest_screenshot_dt
                if day_max_timestamp_dt < latest_screenshot_dt:
                    day_max_timestamp_dt = latest_screenshot_dt

        logger.info(f"{day_min_timestamp_dt=}, {day_max_timestamp_dt=}")
    with spacing_col:
        st.empty()
    with search_col:
        # 初始化时间线滑杆启用状态，这个状态同时用来判断是否启用搜索功能，如果True则启用
        if "day_time_slider_disable" not in st.session_state:
            st.session_state["day_time_slider_disable"] = False

        # 关键词搜索组件
        if "day_search_query_page_index" not in st.session_state:
            st.session_state["day_search_query_page_index"] = 0

        (
            toggle_col,
            keyword_col,
            result_cnt_col,
            turn_page_col,
            refresh_col,
        ) = st.columns([1, 1.5, 1, 1, 0.5])
        with toggle_col:
            if st.toggle(_t("oneday_toggle_search"), help=_t("oneday_toggle_search_help")):
                st.session_state.day_time_slider_disable = True
                st.session_state.day_is_search_data = True
            else:
                st.session_state.day_time_slider_disable = False
                st.session_state.day_is_search_data = False
        with keyword_col:
            # 搜索框

            # 懒加载，输入不变时节省性能
            if "df_day_search_result" not in st.session_state:
                st.session_state.df_day_search_result = pd.DataFrame()
            if "day_search_keyword" not in st.session_state:
                st.session_state.day_search_keyword = None
            if "day_search_keyword_lazy" not in st.session_state:
                st.session_state.day_search_keyword_lazy = "Keyword"
            if "day_date_input_lazy" not in st.session_state:
                st.session_state.day_date_input_lazy = st.session_state.day_date_input

            def do_day_keyword_search():
                # 搜索前清除状态
                st.session_state.day_search_result_index_num = 0  # 条目检索
                if (
                    st.session_state.day_search_keyword_lazy == st.session_state.day_search_keyword
                    and st.session_state.day_date_input_lazy == st.session_state.day_date_input
                ):
                    return
                st.session_state.day_search_keyword_lazy = st.session_state.day_search_keyword
                st.session_state.day_date_input_lazy = st.session_state.day_date_input
                if st.session_state.day_search_keyword != "Keyword":
                    components.record_search_history(
                        search_content=st.session_state.day_search_keyword, search_type="Oneday - OCR Text Search"
                    )
                st.session_state.df_day_search_result = OneDay().search_day_data(
                    utils.complete_datetime(st.session_state.day_date_input),
                    search_content=st.session_state.day_search_keyword,
                )

            st.session_state.day_search_keyword = st.text_input(
                _t("text_search_keyword"),
                "",
                key=2,
                label_visibility="collapsed",
                disabled=not st.session_state.day_time_slider_disable,
                placeholder="Keyword",
            )
            do_day_keyword_search()

            # 执行搜索，搜索结果
            # df_day_search_result = OneDay().search_day_data(utils.complete_datetime(st.session_state.day_date_input),search_content=st.session_state.day_search_keyword)
        with result_cnt_col:
            # 结果条目数
            if st.session_state.day_is_search_data:
                # 启用了搜索功能
                if st.session_state.df_day_search_result.empty:
                    st.markdown(_t("oneday_search_md_none"), unsafe_allow_html=True)
                else:
                    result_num = st.session_state.df_day_search_result.shape[0]
                    st.markdown(
                        _t("oneday_search_md_result").format(result_num=result_num),
                        unsafe_allow_html=True,
                    )
            else:
                st.empty()
        with turn_page_col:
            # 翻页器
            if st.session_state.df_day_search_result.empty:
                st.empty()
            else:

                def update_slider(dt):
                    # 翻页结果时刷新控制时间滑杆的定位；入参：需要被定位的datetime.time
                    if st.session_state.day_is_search_data:
                        st.session_state.day_time_select_slider = dt

                # 初始化值
                if "day_search_result_index_num" not in st.session_state:
                    st.session_state["day_search_result_index_num"] = 0
                # 翻页控件
                st.session_state.day_search_result_index_num = st.number_input(
                    "PageIndex",
                    value=0,
                    min_value=0,
                    max_value=st.session_state.df_day_search_result.shape[0] - 1,
                    label_visibility="collapsed",
                    disabled=not st.session_state.day_time_slider_disable,
                    on_change=update_slider(
                        # utils.set_full_datetime_to_day_time(
                        utils.seconds_to_datetime(
                            st.session_state.df_day_search_result.loc[
                                st.session_state.day_search_result_index_num,
                                "videofile_time",
                            ]
                        )
                        # )
                    ),
                )
        with refresh_col:
            st.button(label="⟳", use_container_width=True)

    # 判断数据库中有无今天的数据，有则启用功能：
    if day_has_data:
        # 准备词云与时间轴（timeline）所需要的文件命名规范与变量，文件名用同一种命名方式，但放到不同的路径下
        real_today_day_cloud_and_TL_img_name = str(datetime.datetime.today().strftime("%Y-%m-%d")) + "-today-.png"
        # real_today_day_cloud_and_TL_img_name = str(datetime.datetime.today().date().year) + "-" + str(datetime.datetime.today().date().month) + "-" + str(datetime.datetime.today().date().day) + "-today-.png"
        if st.session_state.day_date_input == datetime.datetime.today().date():
            # 如果是今天的结果，以-today结尾，以使次日回溯时词云能被自动更新
            # current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + "-today-" + ".png"
            current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + "-today-.png"
            # 太邪门了，.png前不能是alphabet/数字字符，否则词云的.to_file会莫名其妙自己多添加一个.png
            current_day_TL_img_path = os.path.join(config.timeline_result_dir_ud, current_day_cloud_and_TL_img_name)
        else:
            # current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + ".png"
            current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + ".png"
            current_day_TL_img_path = os.path.join(config.timeline_result_dir_ud, current_day_cloud_and_TL_img_name)

        # 时间滑动控制杆
        # start_time = datetime.time(
        #     day_min_timestamp_dt.hour, day_min_timestamp_dt.minute
        # )
        # end_time = datetime.time(day_max_timestamp_dt.hour, day_max_timestamp_dt.minute)

        # if end_time < start_time:
        #     end_time = datetime.time(day_max_timestamp_dt.hour + 24, day_max_timestamp_dt.minute)
        st.session_state.day_time_select_24h = st.slider(
            "Time Rewind",
            label_visibility="collapsed",
            min_value=day_min_timestamp_dt,
            max_value=day_max_timestamp_dt,
            value=day_max_timestamp_dt,
            format="MM/DD - HH:mm" if day_min_timestamp_dt.day != day_max_timestamp_dt.day else "HH:mm",
            step=datetime.timedelta(seconds=30),
            disabled=st.session_state.day_time_slider_disable,
            key="day_time_select_slider",
        )

        # 展示时间轴缩略图
        def update_day_timeline_thumbnail():
            with st.spinner(_t("oneday_text_generate_timeline_thumbnail")):
                if OneDay().generate_preview_timeline_img(
                    dt_in=day_min_timestamp_dt,
                    dt_out=day_max_timestamp_dt,
                    img_saved_name=current_day_cloud_and_TL_img_name,
                ):
                    return True
                else:
                    return False

        get_generate_result = True
        if not os.path.exists(current_day_TL_img_path):
            # 如果时间轴缩略图不存在，创建之
            get_generate_result = update_day_timeline_thumbnail()
            # 移除非今日的-today.png
            for filename in os.listdir(config.timeline_result_dir_ud):
                if "-today-" in filename and filename != real_today_day_cloud_and_TL_img_name:
                    file_path = os.path.join(config.timeline_result_dir_ud, filename)
                    try:
                        os.remove(file_path)
                        logger.info(f"webui: Deleted file: {file_path}")
                    except Exception as e:
                        logger.error(f"webui: {e}")
        elif "-today-" in current_day_TL_img_path:
            # 如果已存在今日的，重新生成覆盖更新
            if not file_utils.is_file_modified_recently(current_day_TL_img_path):
                # 如果修改日期超过30分钟则更新
                get_generate_result = update_day_timeline_thumbnail()

        # 展示时间轴缩略图
        if get_generate_result:
            # 添加时间标记
            flag_mark_timeline_img_filepath = None
            if os.path.exists(config.flag_mark_note_filepath):  # 读取标记数据
                df_flag_mark_for_timeline = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
                if len(df_flag_mark_for_timeline) > 0:  # 绘制旗标图
                    flag_mark_timeline_img_filepath = flag_mark_note.add_visual_mark_on_oneday_timeline_thumbnail(
                        df=df_flag_mark_for_timeline, image_filepath=current_day_TL_img_path
                    )

            if flag_mark_timeline_img_filepath:
                daily_timeline_html(utils.image_to_base64(flag_mark_timeline_img_filepath))
            else:
                daily_timeline_html(utils.image_to_base64(current_day_TL_img_path))

        else:
            st.markdown(
                _t("oneday_md_no_enough_thunmbnail_for_timeline"),
                unsafe_allow_html=True,
            )

        # 可视化数据时间轴
        day_chart_data_overview = OneDay().get_day_statistic_chart_overview(
            df=day_df, start_dt=day_min_timestamp_dt, end_dt=day_max_timestamp_dt
        )
        st.area_chart(
            day_chart_data_overview,
            x="hour",
            y="data",
            use_container_width=True,
            height=100,
            color="#AC79D5",
        )

        # 初始化懒加载状态
        if "cache_videofile_ondisk_list_oneday" not in st.session_state:  # 减少io查询，预拿视频文件列表供比对是否存在
            st.session_state.cache_videofile_ondisk_list_oneday = file_utils.get_file_path_list(config.record_videos_dir_ud)

        # 视频展示区域
        if config.enable_3_columns_in_oneday:  # 是否启用三栏
            col1a, col2a, col3a = st.columns([1, 3, 1])
        else:
            col1a, col2a = st.columns([2, 3])

        with col1a:
            # 居左部分
            st.empty()
            if st.session_state.day_is_search_data and not st.session_state.df_day_search_result.empty:
                # 如果是搜索视图，这里展示全部的搜索结果
                df_day_search_result_refine = db_manager.db_refine_search_data_day(
                    st.session_state.df_day_search_result,
                    cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list_oneday,
                )  # 优化下数据展示
                components.video_dataframe(df_day_search_result_refine)
            else:
                # 工具栏：活动统计，旗标。如果启用三栏，则放置右侧
                if not config.enable_3_columns_in_oneday:
                    components.oneday_side_toolbar()

        with col2a:
            # 居中部分：视频结果显示区域
            if st.session_state.day_is_search_data and not st.session_state.df_day_search_result.empty:
                # 【搜索功能】
                # 获取关键词，搜索出所有结果的dt，然后使用上下翻页来定位，定位后展示对应的视频
                (
                    day_is_video_ondisk,
                    day_video_file_name,
                    shown_timestamp,
                ) = OneDay().get_result_df_video_time(
                    st.session_state.df_day_search_result,
                    st.session_state.day_search_result_index_num,
                )
                if day_is_video_ondisk:
                    show_and_locate_video_timestamp_by_filename_and_time(day_video_file_name, shown_timestamp)
                    if config.enable_ocr_str_highlight_indicator:
                        try:
                            components.ocr_res_position_visualization(
                                ocr_text_full=st.session_state.df_day_search_result.loc[
                                    st.session_state.day_search_result_index_num, "ocr_text"
                                ],
                                ocr_text_query=st.session_state.day_search_keyword,
                            )
                        except Exception as e:
                            st.error(e)
                    st.markdown(_t("oneday_md_rewinding_video_name").format(day_video_file_name=day_video_file_name))
                    try_get_and_render_deep_linking(method="serach_df")
                else:
                    st.info(_t("oneday_text_not_found_vid_but_has_data"), icon="🎐")
                    found_row = (
                        st.session_state.df_day_search_result.loc[st.session_state.day_search_result_index_num].to_frame().T
                    )
                    found_row = db_manager.db_refine_search_data_day(
                        found_row,
                        cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list_oneday,
                    )  # 优化下数据展示
                    components.video_dataframe(found_row, heightIn=0)

            else:
                # 【时间线速查功能】
                # 获取选择的时间，查询对应时间下有无视频，有则换算与定位
                day_full_select_datetime = st.session_state.day_time_select_24h
                (
                    day_is_result_exist,
                    day_video_file_name,
                ) = OneDay().find_closest_video_by_filesys(
                    day_full_select_datetime
                )  # 通过文件查询
                # 计算换算用于播放视频的时间

                if day_is_result_exist:
                    # 换算时间、定位播放视频
                    vidfile_timestamp = utils.calc_vid_name_to_timestamp(day_video_file_name)
                    select_timestamp = utils.datetime_to_seconds(day_full_select_datetime)
                    shown_timestamp = select_timestamp - vidfile_timestamp
                    show_and_locate_video_timestamp_by_filename_and_time(day_video_file_name, shown_timestamp)
                    st.markdown(_t("oneday_md_rewinding_video_name").format(day_video_file_name=day_video_file_name))
                    try_get_and_render_deep_linking(method="timeline_locate", data=day_full_select_datetime)
                else:
                    # 是否有缓存的截图
                    (
                        day_is_screenshot_result_exist,
                        day_screenshot_filepath,
                    ) = OneDay().find_closest_video_by_filesys(
                        day_full_select_datetime,
                        threshold=20,
                        dir_path=SCREENSHOT_CACHE_FILEPATH,
                        return_as_full_filepath=True,
                    )
                    if day_is_screenshot_result_exist:
                        if os.path.exists(day_screenshot_filepath):
                            display_screenshot_recall(day_screenshot_filepath)
                    else:
                        # 没有对应的视频和缓存截图，查一下有无索引了的数据
                        is_data_found, found_row = OneDay().find_closest_video_by_database(
                            day_df, utils.datetime_to_seconds(day_full_select_datetime)
                        )
                        df_vid_filename = None
                        if found_row is not None:
                            df_vid_filename = file_utils.check_video_exist_in_videos_dir(found_row["videofile_name"].iloc[0])
                        df_vid_filepath = ""
                        if df_vid_filename:
                            df_vid_filepath = file_utils.convert_vid_filename_as_vid_filepath(
                                file_utils.check_video_exist_in_videos_dir(found_row["videofile_name"].iloc[0])
                            )
                        if is_data_found and found_row is not None:
                            # screenshots compatible
                            if os.path.exists(found_row["picturefile_name"].iloc[0]):
                                display_screenshot_recall(found_row["picturefile_name"].iloc[0])
                            # more than config.record_seconds video compatible
                            elif os.path.exists(df_vid_filepath):
                                vidfile_timestamp = utils.calc_vid_name_to_timestamp(df_vid_filename)
                                select_timestamp = utils.datetime_to_seconds(day_full_select_datetime)
                                shown_timestamp = select_timestamp - vidfile_timestamp
                                if shown_timestamp >= 0:
                                    show_and_locate_video_timestamp_by_filename_and_time(df_vid_filename, shown_timestamp)
                                    st.markdown(
                                        _t("oneday_md_rewinding_video_name").format(day_video_file_name=df_vid_filename)
                                    )
                                else:
                                    st.info(_t("oneday_text_no_found_record_and_vid_on_disk"), icon="🎐")
                            else:
                                st.info(_t("oneday_text_not_found_vid_but_has_data"), icon="🎐")
                                found_row = db_manager.db_refine_search_data_day(
                                    found_row,
                                    cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list_oneday,
                                )  # 优化下数据展示
                                components.video_dataframe(found_row, heightIn=0)
                        else:
                            # 如果是当天第一次打开但数据库正在索引因而无法访问
                            if (
                                st.session_state.day_date_input
                                == utils.set_full_datetime_to_YYYY_MM_DD(datetime.datetime.today())
                                and utils.is_maintain_lock_valid()
                            ):
                                st.warning(
                                    _t("oneday_text_data_indexing_wait_and_refresh"),
                                    icon="🦫",
                                )
                            else:
                                st.warning(
                                    _t("oneday_text_no_found_record_and_vid_on_disk"),
                                    icon="🦫",
                                )

        if config.enable_3_columns_in_oneday:  # 是否启用三栏
            with col3a:
                st.empty()
                components.oneday_side_toolbar()

    else:
        # 数据库中没有今天的记录
        # 判断videos下有无今天的视频文件
        if file_utils.find_filename_in_dir("videos", utils.datetime_to_dateDayStr(dt_in)):
            st.info(_t("oneday_text_has_vid_but_not_index"), icon="📎")
        else:
            st.info(_t("oneday_text_vid_and_data_not_found"), icon="🎐")


# 直接定位视频时间码、展示视频
def show_and_locate_video_timestamp_by_filename_and_time(video_file_name, timestamp):
    st.session_state.day_timestamp = int(timestamp)
    # 合并视频文件路径
    videofile_path_month_dir = file_utils.convert_vid_filename_as_YYYY_MM(video_file_name)  # 获取对应的日期目录
    videofile_path = os.path.join(config.record_videos_dir_ud, videofile_path_month_dir, video_file_name)
    logger.info(f"webui: videofile_path: {videofile_path}")
    # 打开并展示定位视频文件
    video_file = open(videofile_path, "rb")
    video_bytes = video_file.read()
    with st.empty():
        if st.session_state.day_timestamp < 0:
            st.toast(f"invalid locate timestamp: {st.session_state.day_timestamp}, set to 1s.")
            st.session_state.day_timestamp = 1
        st.video(video_bytes, start_time=st.session_state.day_timestamp)

    # 显示音频播放器（如果启用音频录制）
    if config.enable_audio_recording:
        show_audio_players(video_file_name, timestamp)


# 显示时间轴
def daily_timeline_html(image_b64):
    st.markdown(
        f"<img style='max-width: 97%;max-height: 100%;margin: 0 0px 5px 50px' src='data:image/png;base64, {image_b64}'/>",
        unsafe_allow_html=True,
    )


# 显示音频播放器
def show_audio_players(video_file_name, timestamp):
    """显示系统音频和麦克风音频播放器"""
    # 获取音频文件路径
    system_audio_path = utils.get_audio_path(video_file_name, "system")
    mic_audio_path = utils.get_audio_path(video_file_name, "mic")

    # 创建两列布局
    audio_col1, audio_col2 = st.columns(2)

    with audio_col1:
        st.markdown(f"**{_t('oneday_audio_system')}**")
        if system_audio_path and os.path.exists(system_audio_path):
            try:
                # 读取并显示音频
                with open(system_audio_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3", start_time=int(timestamp))
            except Exception as e:
                logger.error(f"Error loading system audio: {e}")
                st.caption(f"⚠️ {_t('oneday_audio_not_available')}")
        else:
            st.caption(f"⚠️ {_t('oneday_audio_not_available')}")

    with audio_col2:
        st.markdown(f"**{_t('oneday_audio_mic')}**")
        if mic_audio_path and os.path.exists(mic_audio_path):
            try:
                # 读取并显示音频
                with open(mic_audio_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3", start_time=int(timestamp))
            except Exception as e:
                logger.error(f"Error loading mic audio: {e}")
                st.caption(f"⚠️ {_t('oneday_audio_not_available')}")
        else:
            st.caption(f"⚠️ {_t('oneday_audio_not_available')}")


# 优化显示回溯截图
def display_screenshot_recall(day_screenshot_filepath):
    screenshot_col1, screenshot_col2, screenshot_col3 = st.columns([0.15, 1, 0.15])
    with screenshot_col1:
        st.empty()
    with screenshot_col2:
        try:
            st.image(day_screenshot_filepath, caption=day_screenshot_filepath)
            try_get_and_render_deep_linking(method="screenshot_json", data=day_screenshot_filepath)
        except OSError:
            st.warning(_t("oneday_text_file_damaged").format(day_screenshot_filepath=day_screenshot_filepath), icon="🖼️")
    with screenshot_col3:
        st.empty()


def try_get_and_render_deep_linking(method="serach_df", data=""):
    """
    :param method: "serach_df", "timeline_locate", "screenshot_json"
    """
    if not config.record_deep_linking:
        return

    try:
        deep_linking = ""
        if method == "serach_df":
            deep_linking = st.session_state.df_day_search_result.loc[
                st.session_state.day_search_result_index_num,
                "deep_linking",
            ]
        elif method == "timeline_locate":
            # data: locate datetime
            df_row = db_manager.db_get_closest_row_around_by_datetime(dt=data, time_threshold=30)
            deep_linking = df_row.loc[df_row.first_valid_index(), "deep_linking"]
        elif method == "screenshot_json":
            # data: screenshot filepath
            json_path = os.path.join(os.path.dirname(data), SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME)
            if os.path.exists(json_path):
                tmp_db_json = file_utils.read_json_as_dict_from_path(json_path)
                sec = utils.dtstr_to_seconds(os.path.basename(data)[:19])
                threshold_sec = 10
                for v in tmp_db_json["data"]:
                    if -2 <= sec - v["videofile_time"] <= threshold_sec:
                        deep_linking = v["deep_linking"]
                        break
        if deep_linking:
            components.render_deep_linking(deep_linking)
    except Exception as e:
        logger.debug(e)
        pass
