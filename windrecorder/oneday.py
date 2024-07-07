import base64
import calendar
import datetime
import os
import re
from io import BytesIO

import pandas as pd
from PIL import Image

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.const import (
    DATETIME_FORMAT,
    SCREENSHOT_CACHE_FILEPATH,
    SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME,
)
from windrecorder.db_manager import db_manager


# 一天之时功能模块
class OneDay:
    def __init__(self):
        pass

    def search_day_data(self, dt_in, search_content=""):
        """
        在数据库中搜索当天所有关于xx的数据

        :param dt_in: datetime.datetime/date 当天其中一个时间点，会自动转为当天的范围
        :param search_content: str 搜索内容
        """
        # 入参：查询时间，搜索内容
        day_begin_minutes = config.day_begin_minutes
        if type(dt_in) is datetime.date:
            # datetime 对象只包含年月日信息
            search_date_range_in = datetime.datetime.combine(
                dt_in, datetime.time(day_begin_minutes // 60, day_begin_minutes % 60, 0)
            )
            _, month_days = calendar.monthrange(dt_in.year, dt_in.month)
            if dt_in.day == month_days:  # month last day
                search_date_range_out = datetime.datetime.combine(
                    dt_in.replace(month=dt_in.month + 1, day=1),
                    datetime.time((23 + day_begin_minutes // 60) % 24, (59 + day_begin_minutes % 60) % 60, 59),
                )
            else:
                search_date_range_out = datetime.datetime.combine(
                    dt_in.replace(day=dt_in.day + (1 if day_begin_minutes > 0 else 0)),
                    datetime.time((23 + day_begin_minutes // 60) % 24, (59 + day_begin_minutes % 60) % 60, 59),
                )
        elif type(dt_in) is datetime.datetime:
            # datetime 对象包含年月日以及时间信息
            search_date_range_in = utils.get_datetime_in_day_range_pole_by_config_day_begin(dt_in, range="start")
            search_date_range_out = utils.get_datetime_in_day_range_pole_by_config_day_begin(dt_in, range="end")

        df, _, _ = db_manager.db_search_data(search_content, search_date_range_in, search_date_range_out)
        return df

    def checkout_daily_data_meta(self, dt_in):
        """
        检查当天数据索引情况
        返回：当天是否有数据、没有索引的文件数量、搜索结果总数、最早时间datetime、最晚时间datetime、df

        :param dt_in:datetime.datetime 当天时间点
        """
        df = OneDay().search_day_data(dt_in)

        # 获得结果数量
        search_result_num = len(df)

        if search_result_num < 2:
            # 没有结果的处理
            _, noocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir_ud)
            return False, noocred_count, 0, None, None, None
        else:
            # 有结果 - 返回其中最早、最晚的结果，以写入slider；提供总索引数目、未索引数量
            min_timestamp = df["videofile_time"].min()
            max_timestamp = df["videofile_time"].max()
            min_timestamp_dt = utils.seconds_to_datetime(min_timestamp)
            max_timestamp_dt = utils.seconds_to_datetime(max_timestamp)
            _, noocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir_ud)
            return (
                True,
                noocred_count - 1,
                search_result_num,
                min_timestamp_dt,
                max_timestamp_dt,
                df,
            )

    def get_day_statistic_chart_overview(self, df, start_dt, end_dt):
        """
        获得当天表中的时间轴统计数据

        :param df: pd.Dataframe
        :param start_dt: datetime.datetime 开始时间
        :param end_dt: datetime.datetime 结束时间
        """
        df_B = df.copy()
        # 新建一份表，统计每个时间段中有多少视频
        df_C = pd.DataFrame(columns=["hour", "data"])
        for step in pd.date_range(start=start_dt, end=end_dt, freq="6min"):
            filtered = df_B[
                (df_B["videofile_time"] >= step.timestamp())
                & (df_B["videofile_time"] < (step + pd.Timedelta(minutes=6)).timestamp())
            ]
            df_C.loc[len(df_C)] = [step, len(filtered)]

        df_C["hour"] = df_C["hour"].dt.round("1min")
        # df_C['hour'] = df_C['hour'].apply(int)
        # df_C["hour"] = df_C["hour"].round(1)
        return df_C

    def find_closest_video_by_filesys(
        self,
        target_datetime,
        threshold=config.record_seconds,
        dir_path=config.record_videos_dir_ud,
        return_as_full_filepath=False,
    ):
        """
        当输入时间戳时，查询最近的视频文件，同时检查是否为合法的对应范围（通过config 录制视频时间长度来比对）
        以寻找视频文件的方式
        """
        # 提取视频文件名中的时间信息
        file_times = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if "_cropped" in file:
                    continue
                match = re.match(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", file)
                if match:
                    file_dt = datetime.datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S")
                    if file_dt < target_datetime:
                        if return_as_full_filepath:
                            file_times.append((os.path.join(root, file), file_dt))
                        else:
                            file_times.append((file, file_dt))
        # 寻找时间距离target_datetime最近的先前时间的视频文件
        if len(file_times) == 0:
            return False, None
        closest_file = max(file_times, key=lambda x: x[1])

        # 判断时间差是否在阈值内
        time_diff = abs(closest_file[1] - target_datetime).total_seconds()

        if time_diff > threshold:
            return False, None
        else:
            return True, closest_file[0]

    # 同上功能，但以搜索数据库的方式
    def find_closest_video_by_database(self, df, time):
        # Find the closest previous time in the dataframe
        prev_time = df["videofile_time"].iloc[(df["videofile_time"] - time).abs().argsort()[:1]].values[0]
        # Check if difference is less than CONFIG seconds
        if time - prev_time < config.record_seconds:
            # Return video name if difference is small enough
            row = df.loc[df["videofile_time"] == prev_time]
            # 只返回时间戳
            # return True, df.loc[df['videofile_time'] == prev_time, 'videofile_name'].values[0]
            return True, row
        else:
            return False, None

    def find_earliest_latest_screenshots_folders_via_date(
        self, target_date: datetime.date, directory=SCREENSHOT_CACHE_FILEPATH
    ):
        """
        在截图缓存目录下找出与给定日期匹配的最早和最晚的文件夹路径。

        :param directory: 要搜索的目录路径
        :param target_date: datetime.date对象，指定的日期
        :return: 一个元组，包含最早和最晚的文件夹路径。如果没有找到匹配的文件夹，则为(None, None)
        """
        earliest_folder = None
        latest_folder = None
        earliest_time = None
        latest_time = None

        for folder in os.listdir(directory):
            try:
                # 从文件夹名称中提取日期和时间部分
                date_time_part = folder[:19]  # "%Y-%m-%d_%H-%M-%S" 占据19个字符 FIXME:hardcode here
                folder_date_time = datetime.datetime.strptime(date_time_part, DATETIME_FORMAT)
                # 检查文件夹日期是否与目标日期匹配
                if folder_date_time.date() == target_date:
                    if earliest_time is None or folder_date_time < earliest_time:
                        earliest_time = folder_date_time
                        earliest_folder = folder
                    if latest_time is None or folder_date_time > latest_time:
                        latest_time = folder_date_time
                        latest_folder = folder
            except ValueError:
                # 如果文件夹名称不符合预期格式，则忽略该文件夹
                continue

        # 返回最早和最晚的文件夹路径
        if earliest_folder is not None:
            earliest_folder = os.path.join(directory, earliest_folder)
        if latest_folder is not None:
            latest_folder = os.path.join(directory, latest_folder)

        return (earliest_folder, latest_folder)

    def find_earliest_latest_screenshots_cache_datetime_via_date(self, target_date: datetime.date):
        """根据日期寻找截图缓存文件夹 tmp_db 中最近的截图"""
        folder_filepath = self.find_earliest_latest_screenshots_folders_via_date(target_date)
        earliest_screenshot_datetime = None
        latest_screenshot_datetime = None
        if folder_filepath[0] is not None and folder_filepath[1] is not None:
            earliest_all_files_json_filepath = os.path.join(folder_filepath[0], SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME)
            tmp_db_json_all_files = file_utils.read_json_as_dict_from_path(earliest_all_files_json_filepath)
            if tmp_db_json_all_files:
                if len(tmp_db_json_all_files["data"]) > 3:
                    earliest_screenshot_datetime = utils.dtstr_to_datetime(
                        tmp_db_json_all_files["data"][0]["datetime_str_record"]
                    )
            latest_all_files_json_filepath = os.path.join(folder_filepath[1], SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME)
            tmp_db_json_all_files = file_utils.read_json_as_dict_from_path(latest_all_files_json_filepath)
            if tmp_db_json_all_files:
                if len(tmp_db_json_all_files["data"]) > 3:
                    latest_screenshot_datetime = utils.dtstr_to_datetime(
                        tmp_db_json_all_files["data"][-1]["datetime_str_record"]
                    )

        return (earliest_screenshot_datetime, latest_screenshot_datetime)

    # 通过输入的数据库与index、找到是否有视频文件、返回其时间戳与视频文件名
    def get_result_df_video_time(self, df, index):
        video_name = df.loc[index, "videofile_name"]
        video_search_result_timestamp = df.loc[index, "videofile_time"]
        video_filename = file_utils.check_video_exist_in_videos_dir(video_name)
        if video_filename is None:
            # 磁盘上没有文件
            return False, video_name, None
        else:
            # 磁盘上有视频文件
            video_name_timestamp = utils.calc_vid_name_to_timestamp(video_name)
            local_video_timestamp = video_search_result_timestamp - video_name_timestamp
            return True, video_filename, local_video_timestamp

    # 生成当天时间线预览图
    def generate_preview_timeline_img(
        self,
        dt_in: datetime.datetime,
        dt_out: datetime.datetime,
        img_saved_name,
        img_saved_folder=config.timeline_result_dir_ud,
    ):
        file_utils.ensure_dir(img_saved_folder)

        # dt_in = utils.get_datetime_in_day_range_pole_by_config_day_begin(day_datetime, range="start")
        # dt_out = utils.get_datetime_in_day_range_pole_by_config_day_begin(day_datetime, range="end")

        image_list = db_manager.db_get_day_thumbnail_by_timeavg(dt_in, dt_out, config.oneday_timeline_pic_num)

        if image_list is None:
            return False

        # image_list: 按绘制顺序存储图片base64
        # 原始图像大小
        try:  # 尝试获取缩略图大小，失败则fallback
            sample_time = 5
            original_width = 20
            original_height = 20
            for i in range(sample_time):  # 截图录制模式下可能有不同大小截图，需要取几个样本，寻找其中最大的大小（性能考虑）
                width, height = utils.get_image_dimensions(image_list[2 + ((len(image_list) - 2) / (sample_time - 1)) * i])
                if width > original_width:
                    original_width = width
                if height > original_height:
                    original_height = height
            # original_width, original_height = utils.get_image_dimensions(image_list[2])
        except Exception:
            original_width = 70
            original_height = 39

        # 目标图像大小（缩小到50%）?
        target_width = int(original_width * 1)
        target_height = int(original_height * 1)

        # 创建一个新的空白图像，用于拼贴图片
        result_width = target_width * len(image_list) + (len(image_list) - 1)  # 考虑到间隔像素
        result_height = target_height
        result = Image.new("RGBA", (result_width, result_height), (0, 0, 0, 0))  # 透明色为 (0, 0, 0, 0)

        # 按顺序拼贴图片
        x_offset = 0
        for image_data in image_list:
            if image_data is None:
                # 创建一个与缩略图大小一致的空图像
                image = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))

                # 将图像粘贴到结果图像上，并手动指定透明度掩码
                result.paste(image, (x_offset, 0), image)
            else:
                # 将base64编码的图像数据解码为图像
                image = Image.open(BytesIO(base64.b64decode(image_data)))
                image = image.resize((target_width, target_height))

                # 创建一个与图像大小相同的纯白色图像作为透明度掩码
                mask = Image.new("L", image.size, 255)  # 'L' 表示灰度图像，255 表示完全不透明

                # 将图像粘贴到结果图像上，并手动指定透明度掩码
                result.paste(image, (x_offset, 0), mask)

                # 缩放图像到目标大小
                # image = image.resize((target_width, target_height), Image.ANTIALIAS)
                # 将图像粘贴到结果图像上
                # result.paste(image, (x_offset, 0), image)

            # 更新下一个图像的横向偏移量（考虑到间隔像素）
            x_offset += target_width + 1

        # 保存结果图像
        img_saved_path = os.path.join(img_saved_folder, img_saved_name)
        result.save(img_saved_path, format="PNG")
        return True

    # 获取当天前台窗口标题统计情况
    def get_wintitle_stat_in_day(self, dt_in: datetime.datetime):
        df = self.search_day_data(dt_in, search_content="")
        # 在生成前清洗数据：
        # from windrecorder import record_wintitle
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
            second_interval = df.loc[index + 1, "videofile_time"] - df.loc[index, "videofile_time"]
            if second_interval > 100:  # 添加阈值，排除时间差值过大的 row，比如隔夜、锁屏期间的记录等
                second_interval = 100
            stat[win_title_name] += second_interval

        # 清洗整理数据
        stat = {key: val for key, val in stat.items() if val > 1}
        df_show = pd.DataFrame(list(stat.items()), columns=["Page", "Screen Time"])
        df_show.sort_values(by="Screen Time", ascending=False, inplace=True)
        df_show = df_show.reset_index(drop=True)
        df_show["Screen Time"] = df_show["Screen Time"].apply(utils.convert_seconds_to_hhmmss)

        return df_show
