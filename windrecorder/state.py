import base64
import calendar
import datetime
import os
from io import BytesIO

import pandas as pd
from PIL import Image

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager


# 统计当月数据概览：条形图
def get_month_data_overview(dt: datetime.datetime):
    month_days = calendar.monthrange(dt.year, dt.month)[1]

    df_month_data = pd.DataFrame(columns=["day", "data_count"])
    for day in range(1, month_days + 1):
        day_datetime_start = datetime.datetime(dt.year, dt.month, day, 0, 0, 1)
        day_datetime_end = datetime.datetime(dt.year, dt.month, day, 23, 59, 59)

        df, _, _ = db_manager.db_search_data("", day_datetime_start, day_datetime_end)

        row_count = len(df)
        df_month_data.loc[day - 1] = [day, row_count]

    return df_month_data


# 统计当月数据概览：散点图
def get_month_day_overview_scatter(dt: datetime.datetime):
    month_days = calendar.monthrange(dt.year, dt.month)[1]

    df_month_data = pd.DataFrame(columns=["day", "hours", "data_count"])

    query_month_start = datetime.datetime(dt.year, dt.month, 1, 0, 0, 1)
    query_month_end = datetime.datetime(dt.year, dt.month, month_days, 23, 59, 59)
    df, _, _ = db_manager.db_search_data("", query_month_start, query_month_end)  # 获取当月所有数据

    for day in range(1, month_days + 1):
        for hour in range(1, 24):
            timestamp_start = utils.datetime_to_seconds(datetime.datetime(dt.year, dt.month, day, hour - 1, 0, 0))
            timestamp_end = utils.datetime_to_seconds(datetime.datetime(dt.year, dt.month, day, hour, 0, 0))
            result = df.loc[(df["videofile_time"] >= timestamp_start) & (df["videofile_time"] <= timestamp_end)]  # 获取当小时的所有数据
            row_count = len(result)
            df_month_data.loc[len(df_month_data.index)] = [day, hour, row_count]

    return df_month_data


# 统计全年数据概览
def get_year_data_overview(dt: datetime.datetime):
    months_count = 12

    df_year_data = pd.DataFrame(columns=["month", "data_count"])
    for month in range(1, months_count + 1):
        month_days = calendar.monthrange(dt.year, month)[1]
        dt_month_start = datetime.datetime(dt.year, month, 1, 0, 0, 1)
        dt_month_end = datetime.datetime(dt.year, month, month_days, 23, 23, 59)

        df, _, _ = db_manager.db_search_data("", dt_month_start, dt_month_end)

        row_count = len(df)
        df_year_data.loc[month - 1] = [month, row_count]

    return df_year_data


# 统计全年数据概览：散点图
def get_year_data_overview_scatter(dt: datetime.datetime):
    df_year_data = pd.DataFrame(columns=["month", "day", "data_count"])

    query_year_start = datetime.datetime(dt.year, 1, 1, 0, 0, 1)
    query_year_end = datetime.datetime(dt.year, 12, 1, 23, 23, 59)
    df, _, _ = db_manager.db_search_data("", query_year_start, query_year_end)  # 获取全年所有数据

    for month in range(1, 13):
        month_days = calendar.monthrange(dt.year, month)[1]
        for day in range(1, month_days + 1):
            day_ts_start = utils.datetime_to_seconds(datetime.datetime(dt.year, month, day, 0, 0, 1))
            day_ts_end = utils.datetime_to_seconds(datetime.datetime(dt.year, month, day, 23, 23, 59))
            result = df.loc[(df["videofile_time"] >= day_ts_start) & (df["videofile_time"] <= day_ts_end)]  # 获取当小时的所有数据
            row_count = len(result)
            df_year_data.loc[len(df_year_data.index)] = [month, day, row_count]

    return df_year_data


# 生成当月光箱（规格：1000x1000，每边30张图）
def generate_month_lightbox(
    dt: datetime.datetime,
    img_saved_name="default.png",
    img_saved_folder=config.lightbox_result_dir,
):
    file_utils.check_and_create_folder(img_saved_folder)

    month_days = calendar.monthrange(dt.year, dt.month)[1]
    dt_month_start = datetime.datetime(dt.year, dt.month, 1, 0, 0, 1)
    dt_month_end = datetime.datetime(dt.year, dt.month, month_days, 23, 23, 59)

    # 光箱容纳图片容量
    pic_width_num = 25
    pic_height_num = 35
    all_pic_num = pic_height_num * pic_width_num

    # 获取时间段所需图片列表（b64）
    image_list = db_manager.db_get_day_thumbnail_by_distributeavg(dt_month_start, dt_month_end, all_pic_num)
    if image_list is None:
        return False

    thumbnail_width, thumbnail_height = utils.get_image_dimensions(image_list[3])

    lightbox_width = 1750 + pic_width_num - 1

    # 计算每张图的resize
    thumbnail_resize_width = int(lightbox_width / pic_width_num)
    thumbnail_resize_height = int(thumbnail_height * thumbnail_resize_width / thumbnail_width)

    lightbox_height = thumbnail_resize_height * pic_height_num + pic_height_num - 1
    # 创建光箱画布
    lightbox_img = Image.new("RGBA", (lightbox_width, lightbox_height), (0, 0, 0, 0))

    x_offset = 0
    y_offset = 0
    x_num = 0

    for image_data in image_list:
        if image_data is None:
            continue

        image_thumbnail = Image.open(BytesIO(base64.b64decode(image_data)))
        image_thumbnail = image_thumbnail.resize((thumbnail_resize_width, thumbnail_resize_height))
        # 创建一个与图像大小相同的纯白色图像作为透明度掩码
        mask_cover = Image.new("L", image_thumbnail.size, 255)  # 'L' 表示灰度图像，255 表示完全不透明

        lightbox_img.paste(image_thumbnail, (x_offset, y_offset), mask_cover)
        x_offset += thumbnail_resize_width + 1
        x_num += 1
        if x_num >= pic_width_num:
            x_offset = 0
            x_num = 0
            y_offset += thumbnail_resize_height + 1

    img_saved_path = os.path.join(img_saved_folder, img_saved_name)
    lightbox_img.save(img_saved_path, format="PNG")
    return True
