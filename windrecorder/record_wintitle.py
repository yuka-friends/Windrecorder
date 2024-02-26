# 记录活动前台的窗口标题名
import calendar
import datetime
import os
import re

import pandas as pd
import pygetwindow
import streamlit as st

from windrecorder import file_utils, utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger
from windrecorder.oneday import OneDay
from windrecorder.utils import get_text as _t

logger = get_logger(__name__)

CSV_TEMPLATE_DF = pd.DataFrame(columns=["datetime", "window_title"])
window_title_last_record = ""


def get_csv_filepath(datetime: datetime.datetime):
    """取得对应 datetime 的 wintitle csv 路径"""
    csv_filename = datetime.strftime("%Y-%m-%d") + ".csv"
    csv_filepath = os.path.join(config.win_title_dir, csv_filename)
    return csv_filepath


def get_df_by_csv_filepath(csv_filepath):
    """根据csv路径获取dataframe。只读属性，若无返回 None"""
    if os.path.exists(csv_filepath):
        return file_utils.read_dataframe_from_path(file_path=csv_filepath)
    else:
        return None


def get_current_wintitle(optimize_name=True):
    """获取当前的前台窗口标题"""
    if optimize_name:
        res = optimize_wintitle_name(pygetwindow.getActiveWindowTitle())
    else:
        res = str(pygetwindow.getActiveWindowTitle())
    return res


def get_lastest_wintitle_from_df(df, filter=True):
    """获取dataframe中不在跳过项中的最后一行"""
    if filter:
        existing_list = ["", "nan", "任务切换", "ctk"]
        # 倒序遍历数据帧
        for i in df.index[::-1]:
            # 检查 'window_title' 列中的值是否不在已有列表中
            if str(df.loc[i, "window_title"]).lower() not in existing_list:
                # 输出满足条件的最后一行数据
                return df.loc[i]
    else:
        return df.iloc[-1]


def record_wintitle_now():
    """流程：记录当下的前台窗口标题到 csv"""
    global window_title_last_record
    windowTitle = get_current_wintitle(optimize_name=True)

    # 如果与上次检测结果一致，则跳过
    if windowTitle == window_title_last_record:
        return

    csv_filepath = get_csv_filepath(datetime.datetime.now())
    if not os.path.exists(csv_filepath):
        file_utils.ensure_dir(config.win_title_dir)
        file_utils.save_dataframe_to_path(CSV_TEMPLATE_DF, file_path=csv_filepath)

    df = file_utils.read_dataframe_from_path(file_path=csv_filepath)

    new_data = {
        "datetime": datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S"),
        "window_title": windowTitle,
    }
    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, file_path=csv_filepath)
    window_title_last_record = windowTitle  # 更新本轮检测结果


def get_wintitle_by_timestamp(timestamp: int):
    """根据输入时间戳，搜寻对应窗口名。"""
    # 规则：如果离后边记录的时间超过1s，则取上一个的记录
    target_time = utils.seconds_to_datetime(timestamp)
    csv_filepath = get_csv_filepath(target_time)
    if not os.path.exists(csv_filepath):
        return None

    df = file_utils.read_dataframe_from_path(file_path=csv_filepath)
    df["datetime"] = pd.to_datetime(df["datetime"])

    # 从dataframe中查找时间戳对应的window_title
    try:
        for i in range(len(df)):
            if i == 0 and target_time <= df.loc[i, "datetime"]:  # 如果时间戳对应的是第一条记录，直接返回该记录的window_title
                return df.loc[i, "window_title"]
            elif target_time >= df.loc[i, "datetime"] and target_time < df.loc[i + 1, "datetime"]:  # 如果时间戳对应的记录在中间
                # 如果时间早于下一条记录1秒则返回上一条记录的window_title
                if df.loc[i + 1, "datetime"] - target_time < datetime.timedelta(seconds=1):
                    return df.loc[i + 1, "window_title"]
                else:  # 否则返回当前记录的window_title
                    return df.loc[i, "window_title"]
            elif i == len(df) - 1 and target_time >= df.loc[i, "datetime"]:  # 如果时间戳对应的是最后一条记录，直接返回该记录的window_title
                return df.loc[i, "window_title"]
    except (ValueError, KeyError) as e:
        logger.error(e)
        pass

    return None


def optimize_wintitle_name(text):
    """根据特定策略优化页面名字"""
    text = str(text)

    # telegram: 只保留对话名
    # eg. "(1) 大懒趴俱乐部 – (283859)"
    text = re.sub(" – \\(\\d+\\)", "", text)  # 移除最后的总未读消息
    text = re.sub(" - \\(\\d+\\)", "", text)
    text = re.sub("^\\(\\d+\\) ", "", text)  # 移除最开始的当前对话未读消息

    # Microsoft Edge: 移除其中的标签数量
    # eg. "XXXX and 64 more pages - Personal - Microsoft Edge"
    text = re.sub(" and \\d+ more pages", "", text)
    text = re.sub(" - Personal", "", text)

    return text


def count_all_page_times_by_raw_dataframe(df: pd.DataFrame):
    """
    根据 sqlite 获取的某段时间范围的 dataframe 数据，统计前台窗口标题时间

    key: wintitle str 名称
    value: int 秒数
    """
    # 在生成前清洗数据：
    # df["win_title"] = df["win_title"].apply(record_wintitle.optimize_wintitle_name)
    df.sort_values(by="videofile_time", ascending=True, inplace=True)
    df = df.reset_index(drop=True)
    stat = {}
    for index, row in df.iterrows():
        win_title_name = str(row["win_title"])
        if win_title_name == "None" or win_title_name == "nan":
            continue
        if win_title_name not in stat:
            stat[win_title_name] = 0
        if index == df.index.max():
            break
        second_interval = int(df.loc[index + 1, "videofile_time"] - df.loc[index, "videofile_time"])
        if second_interval > 100:  # 添加阈值，排除时间差值过大的 row，比如隔夜、锁屏期间的记录等
            second_interval = 100
        stat[win_title_name] += second_interval

    stat = {key: val for key, val in stat.items() if val > 1}  # 移除统计时间过短项
    return stat


def turn_dict_into_display_dataframe(stat: dict):
    """
    将 dict 转为 streamlit 可以直接呈现的 dataframe

    Page     | Screen Time
    wintitle | 1h02m03s
    """
    df_show = pd.DataFrame(list(stat.items()), columns=["Page", "Screen Time"])
    if len(df_show) == 0:
        return df_show
    # 使用 str.contains 和 ' | '.join 方法来生成一个判断条件语句，然后利用 ~ 来进行逻辑非操作
    mask = df_show["Page"].apply(lambda x: any(word in x for word in config.exclude_words))  # 过滤掉自定义跳过词
    df_show = df_show[~mask]
    df_show.sort_values(by="Screen Time", ascending=False, inplace=True)
    df_show = df_show.reset_index(drop=True)
    df_show["Screen Time"] = df_show["Screen Time"].apply(utils.convert_seconds_to_hhmmss, args=(False,))
    return df_show


def get_wintitle_stat_in_day(dt_in: datetime.datetime):
    """流程：获取当天前台窗口标题时间统计 dataframe、屏幕时间总和"""
    df = OneDay().search_day_data(dt_in, search_content="")
    stat = count_all_page_times_by_raw_dataframe(df)
    df_show = turn_dict_into_display_dataframe(stat)
    time_sum = sum(int(value) for value in stat.values())

    return df_show, time_sum


def get_wintitle_stat_dict_in_month(dt_in: datetime.datetime):
    """流程：获取当月前台窗口标题的时间统计 dict"""
    dt_start = datetime.datetime(dt_in.year, dt_in.month, 1, 0, 0, 1)
    dt_end = datetime.datetime(dt_in.year, dt_in.month, calendar.monthrange(dt_in.year, dt_in.month)[1], 23, 59, 59)
    df, _, _ = db_manager.db_search_data("", dt_start, dt_end)
    stat = count_all_page_times_by_raw_dataframe(df)

    return stat


# ------------streamlit component
# 一日之时 窗口标题组件
def component_wintitle_stat(day_date_input):
    day_wintitle_df_statename_date = day_date_input.strftime("%Y-%m-%d")
    day_wintitle_df_statename = f"wintitle_stat_{day_wintitle_df_statename_date}"
    if day_wintitle_df_statename not in st.session_state:
        (
            st.session_state[day_wintitle_df_statename],
            st.session_state[day_wintitle_df_statename + "_screentime_sum"],
        ) = get_wintitle_stat_in_day(day_date_input)
    if len(st.session_state[day_wintitle_df_statename]) > 0:
        st.dataframe(
            st.session_state[day_wintitle_df_statename],
            column_config={
                "Page": st.column_config.TextColumn(
                    _t("oneday_wt_text")
                    + "   -   "
                    + utils.convert_seconds_to_hhmmss(
                        st.session_state[day_wintitle_df_statename + "_screentime_sum"], complete_with_zero=False
                    ),
                    help=_t("oneday_wt_help"),
                )
            },
            height=850,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.markdown(_t("oneday_ls_text_no_wintitle_stat"), unsafe_allow_html=True)


# 月统计组件
def component_month_wintitle_stat(month_dt: datetime.datetime):
    if "wintitle_month_dt_last_time" not in st.session_state:  # diff 当前显示表的日期，用于和控件用户输入对比判断是否更新
        st.session_state.wintitle_month_dt_last_time = month_dt

    month_wintitle_df_statename_date = month_dt.strftime("%Y-%m")
    month_wintitle_df_statename = f"wintitle_stat_{month_wintitle_df_statename_date}"
    if month_wintitle_df_statename not in st.session_state:  # 初始化显示的表状态
        st.session_state[month_wintitle_df_statename] = pd.DataFrame()
        st.session_state[month_wintitle_df_statename + "_screentime_sum"] = 0

    current_month_wintitle_stat_json_name = f"{month_wintitle_df_statename_date}.json"
    current_month_wintitle_stat_json_filepath = os.path.join(
        config.wintitle_result_dir_ud, current_month_wintitle_stat_json_name
    )

    # 如果切换了时间或第一次加载，进行更新
    update_condition = False
    if utils.set_full_datetime_to_YYYY_MM(st.session_state.wintitle_month_dt_last_time) != utils.set_full_datetime_to_YYYY_MM(
        month_dt
    ):
        update_condition = True
        st.session_state.wintitle_month_dt_last_time = month_dt

    def _generate_stat():
        """生成统计，结果放于 session state 中"""
        st.session_state["month_wintitle_stat_dict"] = get_wintitle_stat_dict_in_month(month_dt)
        file_utils.save_dict_as_json_to_path(
            st.session_state["month_wintitle_stat_dict"], current_month_wintitle_stat_json_filepath
        )

    def _read_stat_on_disk_cache():
        """读取统计"""
        st.session_state["month_wintitle_stat_dict"] = file_utils.read_json_as_dict_from_path(
            current_month_wintitle_stat_json_filepath
        )

    if st.session_state[month_wintitle_df_statename].empty or update_condition:
        # 检查磁盘上有无统计缓存，然后检查是否过时
        if os.path.exists(current_month_wintitle_stat_json_filepath):
            if current_month_wintitle_stat_json_name[:7] == datetime.datetime.today().strftime("%Y-%m"):  # 如果是需要时效性的当下月数据
                if not file_utils.is_file_modified_recently(
                    current_month_wintitle_stat_json_filepath, time_gap=720
                ):  # 超过半天未更新，过时 重新生成
                    with st.spinner(_t("stat_text_counting")):
                        _generate_stat()
            # 进行读取操作
            _read_stat_on_disk_cache()
        else:  # 磁盘上不存在缓存
            with st.spinner(_t("stat_text_counting")):
                _generate_stat()

        # 处理数据
        st.session_state[month_wintitle_df_statename] = turn_dict_into_display_dataframe(
            st.session_state["month_wintitle_stat_dict"]
        )
        st.session_state[month_wintitle_df_statename + "_screentime_sum"] = sum(
            int(value) for value in st.session_state["month_wintitle_stat_dict"].values()
        )

    if len(st.session_state[month_wintitle_df_statename]) > 0:
        st.dataframe(
            st.session_state[month_wintitle_df_statename],
            column_config={
                "Page": st.column_config.TextColumn(
                    "⏱️ "
                    + _t("oneday_wt_text")
                    + "   -   "
                    + utils.convert_seconds_to_hhmmss(
                        st.session_state[month_wintitle_df_statename + "_screentime_sum"], complete_with_zero=False
                    ),
                    help=_t("oneday_wt_help"),
                )
            },
            height=1000,
            hide_index=True,
            use_container_width=True,
        )
        st.markdown(f"`{current_month_wintitle_stat_json_filepath}`")
    else:
        st.markdown(_t("oneday_ls_text_no_wintitle_stat_momnth"), unsafe_allow_html=True)
