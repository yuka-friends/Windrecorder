import datetime
import os

import customtkinter
import pandas as pd
import pyautogui

import windrecorder.file_utils as file_utils
import windrecorder.utils as utils
from windrecorder.config import config

# 从托盘标记时间点，在 webui 检索记录表

FLAG_MARK_NOTE_FILEPATH = os.path.join(config.userdata_dir, config.flag_mark_note_filename)
CSV_TEMPLATE_DF = pd.DataFrame(columns=["thumbnail", "datetime", "note", "mark"])


def check_and_create_csv_if_not_exist():
    if not os.path.exists(FLAG_MARK_NOTE_FILEPATH):
        file_utils.ensure_dir(config.userdata_dir)
        file_utils.save_dataframe_to_path(CSV_TEMPLATE_DF, file_path=FLAG_MARK_NOTE_FILEPATH)


def add_new_flag_record_from_tray(datetime_created=datetime.datetime.now()):
    """
    从托盘添加旗标时，将当前时间、屏幕缩略图记录进去
    """
    df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
    current_screenshot = pyautogui.screenshot()
    img_b64 = utils.resize_image_as_base64(current_screenshot)

    new_data = {"thumbnail": img_b64, "datetime": datetime_created, "mark": False}

    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)


def add_note_to_csv_by_datetime(note, datetime_created):
    """
    根据输入的datetime，更新其记录的备注信息
    """
    df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
    df.loc[df["datetime"] == str(datetime_created), "note"] = note
    file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)


def update_record():
    pass


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
            target_y = int((screen_height * 4 / 5))
        else:
            target_x = int((screen_width * 4 / 5) * SCALE_FACTOR)
            target_y = int((screen_height * 4 / 5) * SCALE_FACTOR)

        # print(f"{dpi=}\n{SCALE_FACTOR=}\n{screen_width=}\n{screen_height=}\n{target_x=}\n{target_y=}")

        self.geometry("%dx%d+%d+%d" % (window_width, window_height, target_x, target_y))
        self.grid_columnconfigure((0, 1), weight=1)
        # self.attributes("-toolwindow", True)   # 移除窗口放大与最小化选项
        self.resizable(False, False)
        self.iconbitmap("__assets__\\icon-tray.ico")
        FONT_CONFIG = ("Microsoft YaHei", 13)

        customtkinter.set_appearance_mode("system")

        self.label_added = customtkinter.CTkLabel(self, text="✔ 已添加此时的标记。", fg_color="transparent", font=FONT_CONFIG)
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
        self.textbox.insert("0.0", "备注：")

        self.button_remove = customtkinter.CTkButton(
            self,
            text="❌ 移除标记",
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
            text="✔ 添加备注",
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
        if user_input_note.startswith("备注："):
            user_input_note = user_input_note.replace("备注：", "")

        add_note_to_csv_by_datetime(user_input_note, datetime_input)
        self.destroy()

    def delete_record(self, datetime_input):
        """
        删除对应时间的记录
        """
        df = file_utils.read_dataframe_from_path(FLAG_MARK_NOTE_FILEPATH)
        df = df.drop(df[df["datetime"] == str(datetime_input)].index)
        file_utils.save_dataframe_to_path(df, FLAG_MARK_NOTE_FILEPATH)
        self.destroy()


# app = Flag_mark_window()
# app.mainloop()

check_and_create_csv_if_not_exist()
