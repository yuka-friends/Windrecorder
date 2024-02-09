import datetime
import os

import customtkinter
import pandas as pd
import pyautogui
import streamlit as st
from PIL import Image, ImageDraw
from send2trash import send2trash

from windrecorder import file_utils, record_wintitle, utils
from windrecorder.config import config
from windrecorder.db_manager import db_manager
from windrecorder.utils import get_text as _t

# 从托盘标记时间点，在 webui 检索记录表
# 使用 main.py 中的 create_timestamp_flag_mark_note() 进行调试


CSV_TEMPLATE_DF = pd.DataFrame(columns=["thumbnail", "datetime", "note"])


def ensure_flag_mark_note_csv_exist():
    if not os.path.exists(config.flag_mark_note_filepath):
        file_utils.ensure_dir(config.userdata_dir)
        file_utils.save_dataframe_to_path(CSV_TEMPLATE_DF, file_path=config.flag_mark_note_filepath)


def add_new_flag_record_from_tray(datetime_created=None):
    """
    从托盘添加旗标时，将当前时间、屏幕缩略图记录进去
    """
    if datetime_created is None:
        datetime_created = datetime.datetime.now()
    ensure_flag_mark_note_csv_exist()
    df = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
    current_screenshot = pyautogui.screenshot()
    img_b64 = utils.resize_image_as_base64(current_screenshot)

    new_data = {
        "thumbnail": img_b64,
        "note": "_",
        "datetime": datetime.datetime.strftime(datetime_created, "%Y-%m-%d %H:%M:%S"),
    }

    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, config.flag_mark_note_filepath)


def update_note_to_csv_by_datetime(note, datetime_created):
    """
    根据输入的datetime，更新其记录的备注信息
    """
    ensure_flag_mark_note_csv_exist()
    if not note:
        note = "_"
    df = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
    df.loc[df["datetime"] == datetime.datetime.strftime(datetime_created, "%Y-%m-%d %H:%M:%S"), "note"] = note
    file_utils.save_dataframe_to_path(df, config.flag_mark_note_filepath)


def add_visual_mark_on_oneday_timeline_thumbnail(df, image_filepath):
    """
    在一日之时的时间轴缩略图上添加旗标

    :param df: 将记录时间戳与备注的 csv 以 DataFrame 形态传入
    :param image_filepath: 原始的一日之时时间缩略图
    """
    # 旗标表中是否有今天的数据，有的话绘制
    # 查询当天最早记录时间与最晚记录时间，获取图像宽度中百分比位置
    # 绘制上去，然后存为 -flag 文件返回
    img_saved_name = f"{os.path.basename(image_filepath).split('.')[0]}-flag-.png"  # 新的临时存储文件名
    img_saved_folder = config.timeline_result_dir
    img_saved_filepath = os.path.join(img_saved_folder, img_saved_name)

    img_datetime_str = os.path.basename(image_filepath).split(".")[0].replace("-today-", "")  # 从源文件名获取时间（日期）
    img_datetime = datetime.datetime.strptime(img_datetime_str, "%Y-%m-%d")

    # 从 df 中提取源文件名包含的当天时间（日期一致）
    datetime_str_list = df["datetime"].tolist()
    datetime_str_list_filtered = [item for item in datetime_str_list if item.startswith(img_datetime_str)]
    datetime_obj_list = [datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") for date_str in datetime_str_list_filtered]

    # 如果有当天时间的记录
    if datetime_obj_list:
        # tl = timeline, pos = position
        img_tl = Image.open(image_filepath)
        img_tl_width, img_tl_height = img_tl.size
        day_min_datetime, day_max_datetime = db_manager.db_get_time_min_and_max_through_datetime(
            img_datetime
        )  # 获取当天时间轴最小、最大时间

        # 绘制旗标图像
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

        # 逐个往时间轴中添加旗标图像
        for item in datetime_obj_list:
            record_second = utils.datetime_to_seconds(item)
            # 当旗标时间范围在已记录的时间范围中时
            if day_min_datetime < record_second < day_max_datetime:
                position_ratio = (record_second - day_min_datetime) / (day_max_datetime - day_min_datetime)
                draw_start_pos_x = int(img_tl_width * position_ratio)
                img_tl.paste(mark_img, (draw_start_pos_x, 0), mark_img)

        img_tl.save(img_saved_filepath)
        return img_saved_filepath

    else:  # 如果没有当天时间的记录
        return None


class Flag_mark_window(customtkinter.CTk):
    """绘制托盘备注记录弹窗"""

    FONT_CONFIG = ("Microsoft YaHei", 13)
    WINDOW_ICON = "__assets__\\icon-tray.ico"

    def __init__(self, datetime_input):
        super().__init__()

        # 计算窗口在屏幕中的显示位置（右下角）
        dpi = self.winfo_fpixels("1i")
        SCALE_FACTOR = dpi / 72
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 400
        window_height = 190
        # target_x = int((screen_width * 4 / 5))
        # target_y = int((screen_height * 3 / 5))
        target_x = int(screen_width - (window_width * SCALE_FACTOR))
        target_y = int(screen_height - ((window_height + 34) * SCALE_FACTOR))

        print(f"flag window DEBUG: \n{dpi=}\n{SCALE_FACTOR=}\n{screen_width=}\n{screen_height=}\n{target_x=}\n{target_y=}")

        # 窗口配置项
        self.title("Windrecorder - Flag")
        self.geometry(f"{window_width}x{window_height}+{target_x}+{target_y}")
        self.grid_columnconfigure((0, 1), weight=1)
        # self.attributes("-toolwindow", True)   # 移除窗口放大与最小化选项
        self.resizable(False, False)  # 移除窗口放大选项
        self.iconbitmap(self.WINDOW_ICON)
        customtkinter.set_appearance_mode("system")

        # 添加标记后的提示项
        self.label_added = customtkinter.CTkLabel(
            self, text="✔ " + _t("flag_text_mark_added"), fg_color="transparent", font=self.FONT_CONFIG, text_color="#A4E074"
        )
        self.label_added.grid(row=0, column=0, padx=15, pady=5, sticky="w")
        self.label_time = customtkinter.CTkLabel(
            self,
            text=datetime.datetime.strftime(datetime_input, "%Y-%m-%d %H:%M:%S"),
            fg_color="transparent",
            text_color="#878787",
            font=self.FONT_CONFIG,
        )
        self.label_time.grid(row=0, column=3, padx=15, pady=0, sticky="e")

        # 备注输入框
        self.textbox = customtkinter.CTkTextbox(master=self, height=80, font=self.FONT_CONFIG)
        self.textbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="ew")
        # 添加最接近的标题名作为默认备注
        wintitle_note_df = record_wintitle.get_df_by_csv_filepath(
            record_wintitle.get_csv_filepath(datetime=datetime.datetime.now())
        )
        wintitle_note = record_wintitle.get_lastest_wintitle_from_df(wintitle_note_df, filter=True)["window_title"]
        self.textbox.insert("0.0", _t("flag_input_note") + wintitle_note + "\n")

        # 移除标记 按钮
        self.button_remove = customtkinter.CTkButton(
            self,
            text="❌ " + _t("flag_btn_remove_mark"),
            command=lambda: self.delete_record(datetime_input=datetime_input),
            width=0,
            fg_color=("#DFDDDD", "#3D3D3D"),
            text_color=("#3A3A3A", "#E7E7E7"),
            hover_color=("#d4cdc8", "#303030"),
            font=self.FONT_CONFIG,
        )
        self.button_remove.grid(row=3, column=0, padx=5, pady=5, columnspan=1, sticky="ew")

        # 添加标记 按钮
        self.button_add_note = customtkinter.CTkButton(
            self,
            text="✔ " + _t("flag_btn_add_note"),
            command=lambda: self.add_note(datetime_input=datetime_input),
            fg_color=("#E5DBFB", "#8262c9"),
            text_color=("#4B357E", "#ffffff"),
            hover_color=("#cfbef6", "#6f53af"),
            font=self.FONT_CONFIG,
        )
        self.button_add_note.grid(row=3, column=1, padx=5, pady=5, columnspan=3, sticky="ew")

    def add_note(self, datetime_input):
        """
        添加标记按钮 的回调
        """
        # "1.0"：表示从第一行的第一个字符开始获取文本。
        # "end-1c"：表示获取到文本的倒数第二个字符为止，这样可以避免获取到最后的换行符。
        user_input_note = self.textbox.get("1.0", "end-1c")
        if user_input_note.startswith(_t("flag_input_note")):  # 移除输入框中的提示前缀
            user_input_note = user_input_note.replace(_t("flag_input_note"), "")

        update_note_to_csv_by_datetime(user_input_note, datetime_input)
        self.destroy()

    def delete_record(self, datetime_input):
        """
        删除标记按钮 的回调：删除对应时间的记录
        """
        df = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
        df = df.drop(df[df["datetime"] == str(datetime.datetime.strftime(datetime_input, "%Y-%m-%d %H:%M:%S"))].index)
        file_utils.save_dataframe_to_path(df, config.flag_mark_note_filepath)
        self.destroy()


# ------------streamlit component
def st_update_df_flag_mark_note():
    """
    更新 streamlit 状态中，时间标记清单表的状态
    """
    st.session_state.df_flag_mark_note_origin = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)  # 取得原表
    st.session_state.df_flag_mark_note = st_tweak_df_flag_mark_note_to_display(
        st.session_state.df_flag_mark_note_origin
    )  # 调整数据后，给编辑器的表
    st.session_state.df_flag_mark_note_last_change = st.session_state.df_flag_mark_note  # 同步 diff 更改对照


def st_save_flag_mark_note_from_editor(df_origin, df_editor):
    """
    保存操作：删除用户选择条目，然后将 streamlit 编辑器的表还原为原表状态，将编辑完成的内容写回 csv

    原表结构：
    ```csv
    thumbnail, datetime, note
    无解析头的base64, 较早的时间(%Y-%m-%d %H:%M:%S), 用户笔记
    ......
    无解析头的base64, 较晚的时间(%Y-%m-%d %H:%M:%S), 用户笔记
    ```

    ↑ ↓

    streamlit 编辑器的表结构：
    ```dataframe
    thumbnail, datetime, note, delete
    带图片解析头的base64, 较晚的时间("%Y/%m/%d   %H:%M:%S"), 用户笔记, False
    ......
    带图片解析头的base64, 较早的时间("%Y/%m/%d   %H:%M:%S"), 用户笔记, False
    ```
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
    st_update_df_flag_mark_note()


def st_tweak_df_flag_mark_note_to_display(df_origin):
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
            "%Y/%m/%d   %H:%M:%S",  # TODO: 这里时间展示格式需要封为统一的可配置项，全局搜索的也是
        ),
        axis=1,
    )
    # 添加可执行选择删除操作的列
    df_tweak.insert(3, "delete", 0)
    # 将 dataframe 倒序排列，使用户新增的内容排在前面
    df_tweak = df_tweak.iloc[::-1]
    return df_tweak


def st_create_timestamp_flag_mark_note_from_oneday_timeselect():
    """
    为一日之时正在选择的时间创建时间戳
    """
    ensure_flag_mark_note_csv_exist()
    # 合并控件选择的时间为 datetime
    datetime_created = utils.merge_date_day_datetime_together(
        st.session_state.day_date_input,
        st.session_state.day_time_select_24h,
    )
    # 获取选择时间附近的缩略图
    row = db_manager.db_get_closest_row_around_by_datetime(datetime_created)
    # 添加数据到原始 csv 中
    new_data = {
        "thumbnail": "" if row.empty else row["thumbnail"].values[0],
        "datetime": datetime_created,
        "note": "" if row.empty else row["win_title"].values[0],
    }
    df = file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)
    df.loc[len(df)] = new_data
    file_utils.save_dataframe_to_path(df, config.flag_mark_note_filepath)
    # 更新 streamlit 表控件状态
    st_update_df_flag_mark_note()


# 旗标组件
def component_flag_mark():
    st.button(
        "🚩" + _t("oneday_btn_add_flag_mark_from_select_time"),
        use_container_width=True,
        on_click=st_create_timestamp_flag_mark_note_from_oneday_timeselect,
    )  # 按钮：为一日之时正在选择的时间创建时间戳

    # 表格编辑器展示区
    if not os.path.exists(config.flag_mark_note_filepath):
        # 没有数据文件，认为未使用过此功能，展示 onboard 介绍
        st.success("💡" + _t("oneday_text_flag_mark_help"))
    elif len(file_utils.read_dataframe_from_path(config.flag_mark_note_filepath)) == 0:  # 有 csv 但表内无数据
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
            st.session_state["df_flag_mark_note"] = st_tweak_df_flag_mark_note_to_display(
                st.session_state.df_flag_mark_note_origin
            )  # 给编辑器的表
        if "df_flag_mark_note_last_change" not in st.session_state:  # 建立更改对照
            st.session_state["df_flag_mark_note_last_change"] = st.session_state.df_flag_mark_note

        st_update_df_flag_mark_note()  # 打开 toggle 时刷新，确保表内容为最新

        # 表编辑器部分
        st.session_state.df_flag_mark_note = st.data_editor(
            st.session_state.df_flag_mark_note,
            column_config={
                "thumbnail": st.column_config.ImageColumn(
                    "thumbnail",
                ),
                "datetime": st.column_config.TextColumn(
                    help=_t("oneday_text_help_locate_manually"),
                ),
                "note": st.column_config.TextColumn(
                    "note",
                    width="large",
                ),
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
        if st.button(
            "✔️" + _t("oneday_btn_flag_mark_save_df"), use_container_width=True
        ) and not st.session_state.df_flag_mark_note.equals(st.session_state.df_flag_mark_note_last_change):
            st_save_flag_mark_note_from_editor(st.session_state.df_flag_mark_note_origin, st.session_state.df_flag_mark_note)
            st.session_state.df_flag_mark_note_last_change = st.session_state.df_flag_mark_note  # 更新 diff
            st.experimental_rerun()
