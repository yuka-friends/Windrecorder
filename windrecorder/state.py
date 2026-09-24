import base64
import datetime
import json
import os
from io import BytesIO
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config
from windrecorder.const import ASSET_DIR, FOOTER_STATE_CAHCE_FILEPATH
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger
from windrecorder.storage import atomic_write_json

logger = get_logger(__name__)


def calendar_range(dt, period):
    """Calendar boundaries use the same naive wall clock as persisted timestamps."""
    if period == "month":
        start = datetime.datetime(dt.year, dt.month, 1)
        end = (start + datetime.timedelta(days=32)).replace(day=1)
    elif period == "year":
        start = datetime.datetime(dt.year, 1, 1)
        end = datetime.datetime(dt.year + 1, 1, 1)
    else:
        raise ValueError("period must be month or year")
    return start, end


def _calendar_grid(dt, period, frequency):
    start, end = calendar_range(dt, period)
    dates = pd.date_range(start, end, freq={"hour": "h", "day": "D", "month": "MS"}[frequency], inclusive="left")
    if period == "month":
        axes = {"day": dates.day}
        if frequency == "hour":
            # Keep the existing chart labels: 1 denotes 00:00–01:00, 24 the last hour.
            axes["hours"] = dates.hour + 1
    else:
        axes = {"month": dates.month}
        if frequency == "day":
            axes["day"] = dates.day
    return pd.DataFrame(axes, dtype="int64"), dates


def _calendar_overview(dt, period, frequency):
    start, end = calendar_range(dt, period)
    frame, dates = _calendar_grid(dt, period, frequency)
    counts = db_manager.db_get_record_counts(start, end, frequency)
    frame["data_count"] = [counts.get(date.strftime("%Y-%m-%d %H:%M:%S"), 0) for date in dates]
    return frame


def get_month_data_overview(dt: datetime.datetime):
    return _calendar_overview(dt, "month", "day")


def get_month_day_overview_scatter(dt: datetime.datetime):
    return _calendar_overview(dt, "month", "hour")


def get_year_data_overview(dt: datetime.datetime):
    return _calendar_overview(dt, "year", "month")


def get_year_data_overview_scatter(dt: datetime.datetime):
    return _calendar_overview(dt, "year", "day")


def get_cached_calendar_overview(dt, period):
    """Derived cache belongs to the data layer, never to a Streamlit selection.

    Versioned JSON leaves legacy CSVs intact. Source fingerprints also invalidate
    historical periods when recordings are imported, deleted, or committed to WAL.
    """
    start, end = calendar_range(dt, period)
    frequency = "hour" if period == "month" else "day"
    key = start.strftime("%Y-%m" if period == "month" else "%Y")
    path = Path(config.date_state_dir_ud) / f"{key}_calendar_v2.json"
    signature = db_manager.db_period_signature(start, end)
    expected, _ = _calendar_grid(dt, period, frequency)
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached["version"] == 2 and cached["source"] == signature:
            frame = pd.DataFrame(cached["records"])
            if (
                list(frame.columns) == [*expected.columns, "data_count"]
                and frame[expected.columns].equals(expected)
                and pd.api.types.is_integer_dtype(frame.data_count)
                and frame.data_count.ge(0).all()
            ):
                return frame
    except (FileNotFoundError, ValueError, TypeError, KeyError):
        pass
    frame = _calendar_overview(dt, period, frequency)
    # A write during the query makes this view transient; do not cache it as current.
    if signature == db_manager.db_period_signature(start, end):
        try:
            atomic_write_json(path, {"version": 2, "source": signature, "records": frame.to_dict("records")})
        except OSError as error:
            logger.warning("Cannot save summary cache %s: %s", path, error)
    return frame


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
