import base64
import datetime
import os
import re
from io import BytesIO

import numpy as np
import pandas as pd
from PIL import Image

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager


# 一天之时功能模块
class OneDay:
    def __init__(self):
        pass

    # 在数据库中搜索当天所有关于xx的数据
    def search_day_data(self, dt_in, search_content=""):
        # 入参：查询时间，搜索内容
        begin_day = config.begin_day
        search_date_range_in = dt_in.replace(
            hour=begin_day // 60, minute=begin_day % 60, second=0, microsecond=0
        )
        search_date_range_out = dt_in.replace(
            day=dt_in.day + (1 if begin_day > 0 else 0),
            hour=(23 + begin_day // 60) % 24,
            minute=(59 + begin_day % 60) % 60,
            second=59,
            microsecond=0,
        )
        df, _, _ = db_manager.db_search_data(
            search_content, search_date_range_in, search_date_range_out
        )
        return df

    # 检查当天数据索引情况
    def checkout(self, dt_in):
        # 获取输入的时间
        # dt_in 的输入格式：datetime.datetime

        # 划定日期范围，取得其中所有数据
        # search_content = ""
        # search_date_range_in = dt_in.replace(hour=0, minute=0, second=0, microsecond=0)
        # search_date_range_out = dt_in.replace(hour=23, minute=59, second=59, microsecond=0)
        # page_index = 0
        # # 获取当日所有的索引信息
        # df,_,_ = db_manager.db_search_data(search_content, search_date_range_in, search_date_range_out,page_index,is_p_index_used=False) # 不启用页数限制，以返回所有结果
        df = OneDay().search_day_data(dt_in)

        # 获得结果数量
        search_result_num = len(df)

        if search_result_num < 2:
            # 没有结果的处理
            _, noocred_count = file_utils.get_videos_and_ocred_videos_count(
                config.record_videos_dir
            )
            return False, noocred_count, 0, None, None, None
        else:
            # 有结果 - 返回其中最早、最晚的结果，以写入slider；提供总索引数目、未索引数量
            min_timestamp = df["videofile_time"].min()
            max_timestamp = df["videofile_time"].max()
            min_timestamp_dt = utils.seconds_to_datetime(min_timestamp)
            max_timestamp_dt = utils.seconds_to_datetime(max_timestamp)
            _, noocred_count = file_utils.get_videos_and_ocred_videos_count(
                config.record_videos_dir
            )
            return (
                True,
                noocred_count - 1,
                search_result_num,
                min_timestamp_dt,
                max_timestamp_dt,
                df,
            )
        # 返回：当天是否有数据、没有索引的文件数量、搜索结果总数、最早时间datetime、最晚时间datetime、df

    # 获得当天表中的时间轴统计数据
    def get_day_statistic_chart_overview(self, df, start_dt, end_dt):
        # 入参：df、开始小时数、结束小时数
        df_B = df.copy()
        # 新建一份表，统计每个时间段中有多少视频
        df_C = pd.DataFrame(columns=["hour", "data"])
        for step in pd.date_range(start=start_dt, end=end_dt, freq="6min"):
            filtered = df_B[
                (df_B["videofile_time"] >= step.timestamp())
                & (
                    df_B["videofile_time"]
                    < (step + pd.Timedelta(minutes=6)).timestamp()
                )
            ]
            df_C.loc[len(df_C)] = [step, len(filtered)]
        df_C["hour"] = df_C["hour"].dt.round("1min")
        # df_C['hour'] = df_C['hour'].apply(int)
        return df_C

    # 当输入时间戳时，查询最近的视频文件，同时检查是否为合法的对应范围（通过config 录制视频时间长度来比对）
    # 以寻找视频文件的方式
    def find_closest_video_by_filesys(self, target_datetime):
        # 获取视频文件名列表
        # video_files = os.listdir(config.record_videos_dir)

        # 提取视频文件名中的时间信息
        file_times = []
        for root, dirs, files in os.walk(config.record_videos_dir):
            for file in files:
                match = re.match(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", file)
                if match:
                    file_dt = datetime.datetime.strptime(
                        match.group(1), "%Y-%m-%d_%H-%M-%S"
                    )
                    if file_dt < target_datetime:
                        file_times.append((file, file_dt))
        # 寻找时间距离target_datetime最近的先前时间的视频文件
        closest_file = max(file_times, key=lambda x: x[1])

        # 判断时间差是否在阈值内
        time_diff = abs(closest_file[1] - target_datetime).total_seconds()

        if time_diff > config.record_seconds:
            return False, None
        else:
            return True, closest_file[0]

    # 同上功能，但以搜索数据库的方式
    def find_closest_video_by_database(self, df, time):
        # Find the closest previous time in the dataframe
        prev_time = (
            df["videofile_time"]
            .iloc[(df["videofile_time"] - time).abs().argsort()[:1]]
            .values[0]
        )
        # Check if difference is less than CONFIG seconds
        if time - prev_time < config.record_seconds:
            # Return video name if difference is small enough
            row = df.loc[df["videofile_time"] == prev_time]
            # 只返回时间戳
            # return True, df.loc[df['videofile_time'] == prev_time, 'videofile_name'].values[0]
            return True, row
        else:
            return False, None

    # 通过输入的数据库与index、找到是否有视频文件、返回其时间戳与视频文件名
    def get_result_df_video_time(self, df, index):
        video_name = df.loc[index, "videofile_name"]
        video_search_result_timestamp = df.loc[index, "videofile_time"]
        check_on_disk_path = file_utils.check_video_exist_in_videos_dir(video_name)
        if check_on_disk_path is None:
            # 磁盘上没有文件
            return False, video_name, None
        else:
            # 磁盘上有视频文件
            video_name_timestamp = utils.calc_vid_name_to_timestamp(video_name)
            local_video_timestamp = video_search_result_timestamp - video_name_timestamp
            return True, check_on_disk_path, local_video_timestamp

    # 生成当天时间线预览图
    def generate_preview_timeline_img(
        self,
        day_datetime,
        img_saved_name="default.png",
        img_saved_folder=config.timeline_result_dir,
    ):
        file_utils.check_and_create_folder(img_saved_folder)

        # if config.late_night_poets:
        #     date_in = datetime.datetime(
        #         day_datetime.year, day_datetime.month, day_datetime.day, 0, 0, 1
        #     )
        #     date_out = datetime.datetime(
        #         day_datetime.year, day_datetime.month, day_datetime.day, 23, 59, 59
        #     )
        # else:
        begin_day = config.begin_day
        date_in = datetime.datetime(
            day_datetime.year,
            day_datetime.month,
            day_datetime.day,
            begin_day // 60,
            begin_day % 60,
            1,
        )
        date_out = datetime.datetime(
            day_datetime.year,
            day_datetime.month,
            day_datetime.day + (1 if begin_day > 0 else 0),
            (23 + begin_day // 60) % 24,
            (59 + begin_day % 60) % 60,
            59,
        )

        image_list = db_manager.db_get_day_thumbnail_by_timeavg(
            date_in, date_out, config.oneday_timeline_pic_num
        )

        if image_list is None:
            return False

        # image_list: 按绘制顺序存储图片base64
        # 原始图像大小
        try:  # 尝试获取缩略图大小，失败则fallback
            original_width, original_height = utils.get_image_dimensions(image_list[2])
        except Exception:
            original_width = 70
            original_height = 39

        # 目标图像大小（缩小到50%）?
        target_width = int(original_width * 1)
        target_height = int(original_height * 1)

        # 创建一个新的空白图像，用于拼贴图片
        result_width = target_width * len(image_list) + (len(image_list) - 1)  # 考虑到间隔像素
        result_height = target_height
        result = Image.new(
            "RGBA", (result_width, result_height), (0, 0, 0, 0)
        )  # 透明色为 (0, 0, 0, 0)

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
