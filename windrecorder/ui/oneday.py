import datetime
import os

import pandas as pd
import streamlit as st
from pandas.testing import assert_frame_equal
from PIL import Image
from send2trash import send2trash

from windrecorder import file_utils, flag_mark_note, utils, wordcloud
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.oneday import OneDay
from windrecorder.ui import components
from windrecorder.utils import get_text as _t


def render():
    # onboarding checking
    if db_manager.check_is_onboarding():
        col1, col2 = st.columns([1, 2])
        with col1:
            components.web_onboarding()
        with col2:
            st.empty()

    # 标题 # todo:添加今天是星期几以增强时间观念

    # 日期选择器
    if "day_date_input" not in st.session_state:
        st.session_state["day_date_input"] = datetime.date.today()

    title_col, yesterday_col, tomorrow_col, today_col, date_col, spacing_col, search_col = st.columns(
        [0.4, 0.25, 0.25, 0.15, 0.25, 0.2, 1]
    )
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
    with date_col:
        st.session_state.day_date_input = st.date_input(
            "Today Date",
            label_visibility="collapsed",
            value=st.session_state.day_date_input,
        )

        # 获取输入的日期
        # 清理格式到HMS
        dt_in = datetime.datetime(
            st.session_state.day_date_input.year,
            st.session_state.day_date_input.month,
            st.session_state.day_date_input.day,
            0,
            0,
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
        ) = OneDay().checkout(dt_in)
    with spacing_col:
        st.empty()
    with search_col:
        # 初始化时间线滑杆启用状态，这个状态同时用来判断是否启用搜索功能，如果True则启用
        if "day_time_slider_disable" not in st.session_state:
            st.session_state["day_time_slider_disable"] = False

        # 关键词搜索组件
        if "day_search_query_page_index" not in st.session_state:
            st.session_state["day_search_query_page_index"] = 0

        toggle_col, keyword_col, result_cnt_col, turn_page_col, refresh_col = st.columns([1, 1.5, 1, 1, 0.5])
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
                st.session_state.df_day_search_result = OneDay().search_day_data(
                    utils.complete_datetime(st.session_state.day_date_input),
                    search_content=st.session_state.day_search_keyword,
                )

            st.session_state.day_search_keyword = st.text_input(
                _t("text_search_keyword"),
                "Keyword",
                key=2,
                label_visibility="collapsed",
                disabled=not st.session_state.day_time_slider_disable,
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
                        utils.set_full_datetime_to_day_time(
                            utils.seconds_to_datetime(
                                st.session_state.df_day_search_result.loc[
                                    st.session_state.day_search_result_index_num,
                                    "videofile_time",
                                ]
                            )
                        )
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
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_day_cloud_and_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir, current_day_cloud_and_TL_img_name)
        else:
            # current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.year) + "-" + str(st.session_state.day_date_input.month) + "-" + str(st.session_state.day_date_input.day) + ".png"
            current_day_cloud_and_TL_img_name = str(st.session_state.day_date_input.strftime("%Y-%m-%d")) + ".png"
            current_day_cloud_img_path = os.path.join(config.wordcloud_result_dir, current_day_cloud_and_TL_img_name)
            current_day_TL_img_path = os.path.join(config.timeline_result_dir, current_day_cloud_and_TL_img_name)

        # 时间滑动控制杆
        start_time = datetime.time(day_min_timestamp_dt.hour, day_min_timestamp_dt.minute)
        end_time = datetime.time(day_max_timestamp_dt.hour, day_max_timestamp_dt.minute)
        st.session_state.day_time_select_24h = st.slider(
            "Time Rewind",
            label_visibility="collapsed",
            min_value=start_time,
            max_value=end_time,
            value=end_time,
            step=datetime.timedelta(seconds=30),
            disabled=st.session_state.day_time_slider_disable,
            key="day_time_select_slider",
        )

        # 展示时间轴缩略图
        def update_day_timeline_thumbnail():
            with st.spinner(_t("oneday_text_generate_timeline_thumbnail")):
                if OneDay().generate_preview_timeline_img(
                    st.session_state.day_date_input,
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
            for filename in os.listdir(config.timeline_result_dir):
                if filename.endswith("-today-.png") and filename != real_today_day_cloud_and_TL_img_name:
                    file_path = os.path.join(config.timeline_result_dir, filename)
                    try:
                        os.remove(file_path)
                        print(f"webui: Deleted file: {file_path}")
                    except Exception as e:
                        print(f"webui: {e}")
        elif current_day_TL_img_path.endswith("-today-.png"):
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

            # st.image(image_thumbnail,use_column_width="always")
        else:
            st.markdown(
                _t("oneday_md_no_enough_thunmbnail_for_timeline"),
                unsafe_allow_html=True,
            )

        # 可视化数据时间轴
        # day_chart_data_overview = OneDay().get_day_statistic_chart_overview(df = day_df, start = day_min_timestamp_dt.hour, end = day_max_timestamp_dt.hour+1)
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
            st.session_state.cache_videofile_ondisk_list_oneday = file_utils.get_file_path_list(config.record_videos_dir)

        # 视频展示区域
        col1a, col2a, col3a = st.columns([1, 3, 1])
        with col1a:
            # 居左部分
            if st.session_state.day_is_search_data and not st.session_state.df_day_search_result.empty:
                # 如果是搜索视图，这里展示全部的搜索结果
                df_day_search_result_refine = db_manager.db_refine_search_data_day(
                    st.session_state.df_day_search_result,
                    cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list_oneday,
                )  # 优化下数据展示
                components.video_dataframe(df_day_search_result_refine)
            else:
                # 时间标记清单

                def update_df_flag_mark_note():
                    """
                    更新 streamlit 状态中，时间标记清单表的状态
                    """
                    st.session_state.df_flag_mark_note_origin = file_utils.read_dataframe_from_path(
                        config.flag_mark_note_filepath
                    )  # 取得原表
                    st.session_state.df_flag_mark_note = tweak_df_flag_mark_note_to_display(
                        st.session_state.df_flag_mark_note_origin
                    )  # 调整数据后，给编辑器的表
                    st.session_state.df_flag_mark_note_last_change = st.session_state.df_flag_mark_note  # 同步 diff 更改对照

                def save_flag_mark_note_from_editor(df_origin, df_editor):
                    """
                    保存操作：删除用户选择条目，将 streamlit 编辑器的表还原为原表状态，将编辑完成的内容写回 csv
                    """
                    df_editor = df_editor.iloc[::-1]  # 还原编辑器展示的倒序

                    # 删除用户在编辑器选中的数据
                    if (df_editor["delete"] == 1).all():  # 如果全选，则直接删除记录文件
                        send2trash(config.flag_mark_note_filepath)
                        return

                    condition = df_editor["delete"] != 1
                    selected_rows = df_editor[condition]
                    df_editor = selected_rows.reset_index(drop=True)

                    # 将编辑器表中数据还原为原始的数据格式
                    df_origin["thumbnail"] = df_editor["thumbnail"].str.replace("data:image/png;base64,", "")
                    df_editor["datetime"] = df_editor.apply(
                        lambda row: datetime.datetime.strftime(
                            datetime.datetime.strptime(row["datetime"], "%Y/%m/%d   %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
                        ),
                        axis=1,
                    )
                    df_origin["datetime"] = df_editor["datetime"]
                    df_origin["note"] = df_editor["note"]
                    df_origin = df_origin.dropna(how="all")  # 删除 dataframe 中包含缺失值的行
                    file_utils.save_dataframe_to_path(df_origin, config.flag_mark_note_filepath)

                    # 更新 streamlit 表控件状态
                    update_df_flag_mark_note()

                def is_df_equal(df1, df2):
                    """
                    比对两个 dataframe 是否一致
                    """
                    try:
                        assert_frame_equal(df1, df2)
                        return True
                    except AssertionError:
                        return False

                def tweak_df_flag_mark_note_to_display(df_origin):
                    """
                    将原始的数据调整为适合编辑器展示的数据
                    """
                    df_tweak = df_origin.copy()

                    # 为缩略图添加解析前缀
                    def process_thumbnail(thumbnail_value):
                        if thumbnail_value is not None:
                            return "data:image/png;base64," + str(thumbnail_value)
                        else:
                            return thumbnail_value

                    # 缩略图添加解析前缀
                    df_tweak["thumbnail"] = df_tweak["thumbnail"].apply(process_thumbnail)
                    # 将时间转化为容易阅读的格式
                    df_tweak["datetime"] = df_tweak.apply(
                        lambda row: datetime.datetime.strftime(
                            datetime.datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S"),
                            "%Y/%m/%d   %H:%M:%S",  # todo: 这里时间展示格式需要封为统一的可配置项，全局搜索的也是
                        ),
                        axis=1,
                    )
                    # 添加可执行选择删除操作的列
                    df_tweak.insert(3, "delete", 0)
                    # 将 dataframe 倒序排列，使用户新增的内容排在前面
                    df_tweak = df_tweak.iloc[::-1]
                    return df_tweak

                def create_timestamp_flag_mark_note_from_oneday_timeselect():
                    """
                    为一日之时正在选择的时间创建时间戳
                    """
                    flag_mark_note.ensure_flag_mark_note_csv_exist()
                    # 合并控件选择的时间为 datetime
                    datetime_created = utils.merge_date_day_datetime_together(
                        st.session_state.day_date_input,
                        st.session_state.day_time_select_24h,
                    )
                    # 获取选择时间附近的缩略图
                    thumbnail = db_manager.db_get_closest_thumbnail_around_by_datetime(datetime_created)
                    # 添加数据
                    new_data = {"thumbnail": thumbnail, "datetime": datetime_created, "note": "_"}
                    df = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
                    df.loc[len(df)] = new_data
                    file_utils.save_dataframe_to_path(df, config.flag_mark_note_filepath)
                    # 更新 streamlit 表控件状态
                    update_df_flag_mark_note()

                if st.toggle(" 🚩" + _t("oneday_toggle_flag_mark")):  # 显示时间标记清单
                    st.button(
                        "🚩" + _t("oneday_btn_add_flag_mark_from_select_time"),
                        use_container_width=True,
                        on_click=create_timestamp_flag_mark_note_from_oneday_timeselect,
                    )

                    if not os.path.exists(config.flag_mark_note_filepath):
                        # 未使用过此功能，展示 onboard 介绍
                        st.success("💡" + _t("oneday_text_flag_mark_help"))
                    elif len(file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)) == 0:  # csv 表内无数据
                        # 未使用过此功能，展示 onboard 介绍
                        send2trash(config.flag_mark_note_filepath)
                        st.success(_t("oneday_text_flag_mark_help"))
                    else:  # 有数据情况下
                        # 初始化状态
                        if "df_flag_mark_note" not in st.session_state:  # 获取编辑器表数据
                            if "df_flag_mark_note_origin" not in st.session_state:  # 取得原表
                                st.session_state["df_flag_mark_note_origin"] = file_utils.read_dataframe_from_path(
                                    config.flag_mark_note_filepath
                                )
                            st.session_state["df_flag_mark_note"] = tweak_df_flag_mark_note_to_display(
                                st.session_state.df_flag_mark_note_origin
                            )  # 给编辑器的表
                        if "df_flag_mark_note_last_change" not in st.session_state:  # 建立更改对照
                            st.session_state["df_flag_mark_note_last_change"] = st.session_state.df_flag_mark_note

                        update_df_flag_mark_note()  # 打开 toggle 时刷新，确保表内容为最新

                        # 表编辑器部分
                        st.session_state.df_flag_mark_note = st.data_editor(
                            st.session_state.df_flag_mark_note,
                            column_config={
                                "thumbnail": st.column_config.ImageColumn(
                                    "thumbnail",
                                ),
                                "note": st.column_config.TextColumn("note", width="large"),
                                "delete": st.column_config.CheckboxColumn(
                                    "delete",
                                    default=False,
                                ),
                            },
                            disabled=["thumbnail", "datetime"],
                            hide_index=True,
                            use_container_width=True,
                            height=600,
                        )
                        st.markdown(f"`{config.flag_mark_note_filepath}`")

                        # 点击保存按钮后，当编辑与输入不一致时，更新文件
                        if st.button("✔️" + _t("oneday_btn_flag_mark_save_df"), use_container_width=True) and not is_df_equal(
                            st.session_state.df_flag_mark_note, st.session_state.df_flag_mark_note_last_change
                        ):
                            save_flag_mark_note_from_editor(
                                st.session_state.df_flag_mark_note_origin, st.session_state.df_flag_mark_note
                            )
                            st.session_state.df_flag_mark_note_last_change = st.session_state.df_flag_mark_note  # 更新 diff
                            st.experimental_rerun()

                st.empty()

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
                    st.markdown(_t("oneday_md_rewinding_video_name").format(day_video_file_name=day_video_file_name))
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
                day_full_select_datetime = utils.merge_date_day_datetime_together(
                    st.session_state.day_date_input,
                    st.session_state.day_time_select_24h,
                )  # 合并时间为datetime
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
                else:
                    # 没有对应的视频，查一下有无索引了的数据
                    is_data_found, found_row = OneDay().find_closest_video_by_database(
                        day_df, utils.datetime_to_seconds(day_full_select_datetime)
                    )
                    if is_data_found:
                        st.info(_t("oneday_text_not_found_vid_but_has_data"), icon="🎐")
                        found_row = db_manager.db_refine_search_data_day(
                            found_row,
                            cache_videofile_ondisk_list=st.session_state.cache_videofile_ondisk_list_oneday,
                        )  # 优化下数据展示
                        components.video_dataframe(found_row, heightIn=0)
                    else:
                        # 如果是当天第一次打开但数据库正在索引因而无法访问
                        if (
                            st.session_state.day_date_input == utils.set_full_datetime_to_YYYY_MM_DD(datetime.datetime.today())
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

        with col3a:
            if config.show_oneday_wordcloud:
                # 是否展示当天词云
                def update_day_word_cloud():
                    with st.spinner(_t("oneday_text_generate_word_cloud")):
                        day_input_datetime_finetune = datetime.datetime(
                            st.session_state.day_date_input.year,
                            st.session_state.day_date_input.month,
                            st.session_state.day_date_input.day,
                            0,
                            0,
                            2,
                        )
                        wordcloud.generate_word_cloud_in_day(
                            utils.datetime_to_seconds(day_input_datetime_finetune),
                            img_save_name=current_day_cloud_and_TL_img_name,
                        )

                if not os.path.exists(current_day_cloud_img_path):
                    # 如果词云不存在，创建之
                    update_day_word_cloud()
                    # 移除非今日的-today.png
                    for filename in os.listdir(config.wordcloud_result_dir):
                        if filename.endswith("-today-.png") and filename != real_today_day_cloud_and_TL_img_name:
                            file_path = os.path.join(config.wordcloud_result_dir, filename)
                            os.remove(file_path)
                            print(f"webui: Deleted file: {file_path}")

                # 展示词云
                try:
                    image = Image.open(current_day_cloud_img_path)
                    st.image(image)
                except Exception as e:
                    st.exception(_t("text_cannot_open_img") + e)

                def update_wordcloud_btn_clicked():
                    st.session_state.update_wordcloud_button_disabled = True

                if st.button(
                    _t("oneday_btn_update_word_cloud"),
                    key="refresh_day_cloud",
                    use_container_width=True,
                    disabled=st.session_state.get("update_wordcloud_button_disabled", False),
                    on_click=update_wordcloud_btn_clicked,
                ):
                    try:
                        update_day_word_cloud()
                    except Exception as ex:
                        st.exception(ex)
                    finally:
                        st.session_state.update_wordcloud_button_disabled = False
                        st.experimental_rerun()
            else:
                st.markdown(_t("oneday_md_word_cloud_turn_off"), unsafe_allow_html=True)

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
    videofile_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, video_file_name)
    print("webui: videofile_path: " + videofile_path)
    # 打开并展示定位视频文件
    video_file = open(videofile_path, "rb")
    video_bytes = video_file.read()
    with st.empty():
        st.video(video_bytes, start_time=st.session_state.day_timestamp)


# 显示时间轴
def daily_timeline_html(image_b64):
    st.markdown(
        f"<img style='max-width: 97%;max-height: 100%;margin: 0 0px 5px 50px' src='data:image/png;base64, {image_b64}'/>",
        unsafe_allow_html=True,
    )
