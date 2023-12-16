import datetime
import os

import customtkinter
import pandas as pd
import pyautogui
from PIL import Image, ImageDraw

import windrecorder.file_utils as file_utils
import windrecorder.utils as utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.utils import get_text as _t

# 从托盘标记时间点，在 webui 检索记录表

FLAG_MARK_NOTE_FILEPATH = os.path.join(config.userdata_dir, config.flag_mark_note_filename)
CSV_TEMPLATE_DF = pd.DataFrame(columns=["thumbnail", "datetime", "note"])


def check_and_create_csv_if_not_exist():
    if not os.path.exists(FLAG_MARK_NOTE_FILEPATH):
        file_utils.ensure_dir(config.userdata_dir)
        file_utils.save_dataframe_to_path(CSV_TEMPLATE_DF, file_path=FLAG_MARK_NOTE_FILEPATH)


def add_new_flag_record_from_tray(datetime_created=datetime.datetime.now()):
    """
    从托盘添加旗标时，将当前时间、屏幕缩略图记录进去
    """
    check_and_create_csv_if_not_exist()
    df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
    current_screenshot = pyautogui.screenshot()
    img_b64 = utils.resize_image_as_base64(current_screenshot)

    new_data = {
        "thumbnail": img_b64,
        "note": "_",
        "datetime": datetime.datetime.strftime(datetime_created, "%Y-%m-%d %H:%M:%S"),
    }

    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)


def add_note_to_csv_by_datetime(note, datetime_created):
    """
    根据输入的datetime，更新其记录的备注信息
    """
    check_and_create_csv_if_not_exist()
    if not note:
        note = "_"
    df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
    df.loc[df["datetime"] == datetime.datetime.strftime(datetime_created, "%Y-%m-%d %H:%M:%S"), "note"] = note
    file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)


def add_visual_mark_on_oneday_timeline_thumbnail(df, image_filepath):
    """
    在一日之时的时间轴缩略图上添加旗标
    """
    # 旗标表中是否有今天的数据，有的话绘制
    # 查询当天最早记录时间与最晚记录时间，获取图像宽度中百分比位置
    # 绘制上去，然后存为-flag文件
    img_saved_name = os.path.basename(image_filepath).split(".")[0] + "-flag-" + ".png"
    img_saved_folder = config.timeline_result_dir
    img_saved_filepath = os.path.join(img_saved_folder, img_saved_name)

    img_datetime_str = os.path.basename(image_filepath).split(".")[0].replace("-today-", "")
    img_datetime = datetime.datetime.strptime(img_datetime_str, "%Y-%m-%d")

    datetime_str_list = df["datetime"].tolist()
    datetime_str_list_filtered = [item for item in datetime_str_list if item.startswith(img_datetime_str)]
    datetime_obj = [datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") for date_str in datetime_str_list_filtered]

    if len(datetime_obj) > 0:
        # tl = timeline, pos = position
        img_tl = Image.open(image_filepath)
        img_tl_width, img_tl_height = img_tl.size
        day_min_datetime, day_max_datetime = db_manager.db_get_time_min_and_max_through_datetime(img_datetime)
        mark_width = 4
        mark_color = (255, 0, 0, 200)
        mark_canva_color = (0, 0, 0, 0)

        mark_img = Image.new("RGBA", (img_tl_height, img_tl_height), mark_canva_color)
        mark_img_rectangle = Image.new("RGBA", (mark_width, img_tl_height), mark_color)
        mark_img_triangle_draw = ImageDraw.Draw(mark_img)
        x1, y1 = mark_width, 0
        x2, y2 = img_tl_height / 2, img_tl_height / 4
        x3, y3 = mark_width, img_tl_height / 2
        mark_img_triangle_draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=mark_color)
        mark_img.paste(mark_img_rectangle, (0, 0), mark_img_rectangle)

        for item in datetime_obj:
            # 需要考虑超出范围的情况
            record_second = utils.datetime_to_seconds(item)
            if record_second > day_min_datetime and record_second < day_max_datetime:
                position_ratio = (record_second - day_min_datetime) / (day_max_datetime - day_min_datetime)
                draw_start_pos_x = int(img_tl_width * position_ratio)
                img_tl.paste(mark_img, (draw_start_pos_x, 0), mark_img)
        img_tl.save(img_saved_filepath)
        return img_saved_filepath

    else:
        return None


class Flag_mark_window(customtkinter.CTk):
    def __init__(self, datetime_input):
        super().__init__()

        self.title("Windrecorder")
        dpi = self.winfo_fpixels("1i")
        SCALE_FACTOR = dpi / 72
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 400
        window_height = 190
        # win11 之前返回的分辨率为 hidpi 分辨率，需要处理为物理分辨率
        if utils.is_win11:
            target_x = int((screen_width * 4 / 5))
            target_y = int((screen_height * 3 / 5))
        else:
            target_x = int((screen_width * 4 / 5) * SCALE_FACTOR)
            target_y = int((screen_height * 3 / 5) * SCALE_FACTOR)

        # print(f"{dpi=}\n{SCALE_FACTOR=}\n{screen_width=}\n{screen_height=}\n{target_x=}\n{target_y=}")

        self.geometry("%dx%d+%d+%d" % (window_width, window_height, target_x, target_y))
        self.grid_columnconfigure((0, 1), weight=1)
        # self.attributes("-toolwindow", True)   # 移除窗口放大与最小化选项
        self.resizable(False, False)
        self.iconbitmap("__assets__\\icon-tray.ico")
        FONT_CONFIG = ("Microsoft YaHei", 13)

        customtkinter.set_appearance_mode("system")

        self.label_added = customtkinter.CTkLabel(
            self, text="✔ " + _t("flag_text_mark_added"), fg_color="transparent", font=FONT_CONFIG
        )
        self.label_added.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        self.label_time = customtkinter.CTkLabel(
            self,
            text=datetime.datetime.strftime(datetime_input, "%Y-%m-%d %H:%M:%S"),
            fg_color="transparent",
            text_color="#878787",
            font=FONT_CONFIG,
        )
        self.label_time.grid(row=0, column=3, padx=15, pady=0, sticky="e")

        self.textbox = customtkinter.CTkTextbox(master=self, height=80, font=FONT_CONFIG)
        self.textbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        self.textbox.insert("0.0", _t("flag_input_note"))

        self.button_remove = customtkinter.CTkButton(
            self,
            text="❌ " + _t("flag_btn_remove_mark"),
            command=lambda: self.delete_record(datetime_input=datetime_input),
            width=0,
            fg_color=("#DFDDDD", "#3D3D3D"),
            text_color=("#3A3A3A", "#E7E7E7"),
            hover_color=("#d4cdc8", "#303030"),
            font=FONT_CONFIG,
        )
        self.button_remove.grid(row=3, column=0, padx=5, pady=5, columnspan=1, sticky="ew")

        self.button_add_note = customtkinter.CTkButton(
            self,
            text="✔ " + _t("flag_btn_add_note"),
            command=lambda: self.add_note(datetime_input=datetime_input),
            fg_color=("#E5DBFB", "#8262c9"),
            text_color=("#4B357E", "#ffffff"),
            hover_color=("#cfbef6", "#6f53af"),
            font=FONT_CONFIG,
        )
        self.button_add_note.grid(row=3, column=1, padx=5, pady=5, columnspan=3, sticky="ew")

    def add_note(self, datetime_input):
        user_input_note = self.textbox.get("1.0", "end-1c")
        print(f"{user_input_note=}")
        # "1.0"：表示从第一行的第一个字符开始获取文本。
        # "end-1c"：表示获取到文本的倒数第二个字符为止，这样可以避免获取到最后的换行符。
        if user_input_note.startswith(_t("flag_input_note")):
            user_input_note = user_input_note.replace(_t("flag_input_note"), "")

        add_note_to_csv_by_datetime(user_input_note, datetime_input)
        self.destroy()

    def delete_record(self, datetime_input):
        """
        删除对应时间的记录
        """
        df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
        df = df.drop(df[df["datetime"] == str(datetime.datetime.strftime(datetime_input, "%Y-%m-%d %H:%M:%S"))].index)
        file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)
        self.destroy()


# app = Flag_mark_window()
# app.mainloop()
