import datetime
import os

import pandas as pd
import pyautogui

import windrecorder.file_utils as file_utils
import windrecorder.utils as utils
from windrecorder.config import config

# 从托盘标记时间点，在 webui 检索记录表

FLAG_MARK_NOTE_FILEPATH = os.path.join(config.userdata_dir, config.flag_mark_note_filename)
CSV_TEMPLATE_DF = pd.DataFrame(columns=["thumbnail", "datetime", "note", "mark"])


def load_csv():
    pass


def check_and_create_csv_if_not_exist():
    if not os.path.exists(FLAG_MARK_NOTE_FILEPATH):
        file_utils.ensure_dir(config.userdata_dir)
        file_utils.save_dataframe_to_path(CSV_TEMPLATE_DF, file_path=FLAG_MARK_NOTE_FILEPATH)


def add_new_flag_record_from_tray():
    """
    从托盘添加旗标时，将当前时间、屏幕缩略图记录进去
    """
    df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
    current_screenshot = pyautogui.screenshot()
    img_b64 = utils.resize_image_as_base64(current_screenshot)

    new_data = {"thumbnail": img_b64, "datetime": datetime.datetime.now(), "mark": False}

    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)


def update_record():
    pass


check_and_create_csv_if_not_exist()
