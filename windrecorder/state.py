import base64
import calendar
import datetime
import os
from io import BytesIO

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.const import ASSET_DIR, FOOTER_STATE_CAHCE_FILEPATH
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger

logger = get_logger(__name__)


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
        dt_month_end = datetime.datetime(dt.year, month, month_days, 23, 59, 59)

        df, _, _ = db_manager.db_search_data("", dt_month_start, dt_month_end)

        row_count = len(df)
        df_year_data.loc[month - 1] = [month, row_count]

    return df_year_data


# 统计全年数据概览：散点图
def get_year_data_overview_scatter(dt: datetime.datetime):
    df_year_data = pd.DataFrame(columns=["month", "day", "data_count"])

    query_year_start = datetime.datetime(dt.year, 1, 1, 0, 0, 1)
    query_year_end = datetime.datetime(dt.year, 12, 1, 23, 59, 59)
    df, _, _ = db_manager.db_search_data("", query_year_start, query_year_end)  # 获取全年所有数据

    for month in range(1, 13):
        month_days = calendar.monthrange(dt.year, month)[1]
        for day in range(1, month_days + 1):
            day_ts_start = utils.datetime_to_seconds(datetime.datetime(dt.year, month, day, 0, 0, 1))
            day_ts_end = utils.datetime_to_seconds(datetime.datetime(dt.year, month, day, 23, 59, 59))
            result = df.loc[(df["videofile_time"] >= day_ts_start) & (df["videofile_time"] <= day_ts_end)]  # 获取当小时的所有数据
            row_count = len(result)
            df_year_data.loc[len(df_year_data.index)] = [month, day, row_count]

    return df_year_data


# 生成当月光箱（规格：1000x1000，每边30张图）
def generate_lightbox_from_datetime_range(
    dt_month_start: datetime.datetime,
    dt_month_end: datetime.datetime,
    image_lst_mode="distributeavg",
    img_saved_name="default.png",
    img_saved_folder=config.lightbox_result_dir_ud,
    pic_width_num=25,
    pic_height_num=35,
    lightbox_width=1774,
    enable_month_lightbox_watermark=config.enable_month_lightbox_watermark,
):
    """
    :param image_lst_mode: 图片列表生成模式, distributeavg 在已有数据中平均分配，timeavg 按时间平均分配
    """
    file_utils.ensure_dir(img_saved_folder)

    # 光箱容纳图片容量
    all_pic_num = pic_height_num * pic_width_num

    # 获取时间段所需图片列表（b64）
    if image_lst_mode == "distributeavg":
        image_list = db_manager.db_get_day_thumbnail_by_distributeavg(dt_month_start, dt_month_end, all_pic_num)
    elif image_lst_mode == "timeavg":
        image_list = db_manager.db_get_day_thumbnail_by_timeavg(dt_month_start, dt_month_end, all_pic_num)

    if image_list is None:
        return False
    if len(image_list) < all_pic_num:
        logger.error("Not enough images")
        return False

    thumbnail_width, thumbnail_height = utils.calc_max_thumbnail_size(image_list)

    # 计算每张图的resize
    thumbnail_resize_width = int(lightbox_width / pic_width_num)
    thumbnail_resize_height = int(thumbnail_height * thumbnail_resize_width / thumbnail_width)

    lightbox_height = thumbnail_resize_height * pic_height_num + pic_height_num - 1
    # 创建光箱画布
    background_color = (255, 250, 246, 0)
    lightbox_img = Image.new("RGBA", (lightbox_width, lightbox_height), background_color)

    x_offset = 0
    y_offset = 0
    x_num = 0

    blank_canvas = Image.new("RGBA", (thumbnail_resize_width, thumbnail_resize_height), background_color)

    for image_data in image_list:
        if image_data is None:
            if image_lst_mode == "timeavg":
                image_thumbnail = blank_canvas
            else:
                continue
        else:
            try:
                image_thumbnail = Image.open(BytesIO(base64.b64decode(image_data)))
                image_thumbnail = image_thumbnail.resize((thumbnail_resize_width, thumbnail_resize_height))
            except Exception:  # binascii.Error: Incorrect padding
                image_thumbnail = blank_canvas
        # 创建一个与图像大小相同的纯白色图像作为透明度掩码
        mask_cover = Image.new("L", image_thumbnail.size, 255)  # 'L' 表示灰度图像，255 表示完全不透明

        lightbox_img.paste(image_thumbnail, (x_offset, y_offset), mask_cover)
        x_offset += thumbnail_resize_width + 1
        x_num += 1
        if x_num >= pic_width_num:
            x_offset = 0
            x_num = 0
            y_offset += thumbnail_resize_height + 1

    if enable_month_lightbox_watermark:
        lightbox_img = add_watermark_to_lightbox_img(lightbox_img, dt_month_start, dt_month_end)

    img_saved_path = os.path.join(img_saved_folder, img_saved_name)
    lightbox_img.save(img_saved_path, format="PNG")
    return True


def add_watermark_to_lightbox_img(input_image, dt_in: datetime.datetime, dt_out: datetime.datetime):
    # 1. 获取输入图像的宽度并创建新画布
    width, _ = input_image.size
    height = 100
    canvas = Image.new("RGBA", (width, height), (255, 250, 246, 0))  # 使用 RGBA 模式创建透明画布

    watermark_badge = Image.open(os.path.join(ASSET_DIR, "watermark-badge.png"))
    watermark_line = Image.open(os.path.join(ASSET_DIR, "watermark-line.png"))

    # 2. 粘贴水印徽标
    offset = (width - watermark_badge.size[0] - 20, 15)
    canvas.paste(watermark_badge, offset, watermark_badge)

    # 3. 添加日期文本
    text_fill_color = (157, 130, 103)
    draw = ImageDraw.Draw(canvas)
    monospace_neon_wide_medium = ImageFont.truetype(os.path.join(ASSET_DIR, "MonaspaceNeon-WideRegular.otf"), 24)
    draw.text((37, 22), dt_in.strftime("%Y.%m.%d"), font=monospace_neon_wide_medium, fill=text_fill_color, antialias=True)
    draw.text((338, 49), dt_out.strftime("%Y.%m.%d"), font=monospace_neon_wide_medium, fill=text_fill_color, antialias=True)

    # 4. 添加天数文本
    monospace_neon_medium_italic = ImageFont.truetype(os.path.join(ASSET_DIR, "MonaspaceNeon-Italic.otf"), 14)
    draw.text(
        (253, 49), str((dt_out - dt_in).days) + " d", font=monospace_neon_medium_italic, fill=(190, 170, 152), antialias=True
    )

    # 5. 粘贴水印线条
    canvas.paste(watermark_line, (24, 16), watermark_line)

    # 6. 将画布拼合到输入图像的下方
    output_image = Image.new("RGB", (width, input_image.size[1] + height))
    output_image.paste(input_image, (0, 0))
    output_image.paste(canvas, (0, input_image.size[1]))

    # 7. 绘制边框
    draw = ImageDraw.Draw(output_image)
    draw.rectangle((0, 0, output_image.size[0], output_image.size[1]), outline=(215, 205, 197), width=3)

    return output_image


def get_footer_state_data():
    res = {}
    res["first_record_time_str"] = utils.seconds_to_date_goodlook_formart(db_manager.db_first_earliest_record_time())
    res["latest_record_time_str"] = utils.seconds_to_date_goodlook_formart(db_manager.db_latest_record_time())
    res["latest_db_records_num"] = db_manager.db_num_records()
    res["videos_file_size"] = round(file_utils.get_dir_size(config.record_videos_dir_ud) / (1024 * 1024 * 1024), 3)
    res["videos_files_count"], _ = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir_ud)

    return res


def make_webui_footer_state_data_cache(ask_from="idle"):
    time_gap = 2880
    if ask_from == "idle":
        time_gap = 720
    if os.path.exists(FOOTER_STATE_CAHCE_FILEPATH):
        if not file_utils.is_file_modified_recently(FOOTER_STATE_CAHCE_FILEPATH, time_gap=time_gap):
            # time to update state cache
            file_utils.save_dict_as_json_to_path(data=get_footer_state_data(), filepath=FOOTER_STATE_CAHCE_FILEPATH)
            logger.info("footer info updated.")
        return file_utils.read_json_as_dict_from_path(FOOTER_STATE_CAHCE_FILEPATH)
    else:
        file_utils.ensure_dir(os.path.dirname(FOOTER_STATE_CAHCE_FILEPATH))
        footer_state_data = get_footer_state_data()
        file_utils.save_dict_as_json_to_path(data=footer_state_data, filepath=FOOTER_STATE_CAHCE_FILEPATH)
        logger.info("footer info updated.")
        return footer_state_data
