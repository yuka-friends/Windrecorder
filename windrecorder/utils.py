import base64
import calendar
import ctypes
import datetime
import json
import os
import platform
import random
import re
import subprocess
import sys
import threading
import time
from datetime import timedelta
from io import BytesIO

import cv2
import pyautogui
import requests
from PIL import Image
from pyshortcuts import make_shortcut

from windrecorder import __version__, file_utils
from windrecorder.config import config


# 启动定时执行线程
class RepeatingTimer(threading.Thread):
    def __init__(self, interval, function):
        threading.Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            time.sleep(self.interval)
            self.function()

    def stop(self):
        self.running = False


# 获得屏幕分辨率
def get_screen_resolution():
    return pyautogui.size()


# 将输入的文件（ %Y-%m-%d_%H-%M-%S str）时间转为时间戳秒数
def date_to_seconds(date_str):
    # 这里我们先定义了时间格式,然后设置一个epoch基准时间为1970年1月1日。使用strptime()将输入的字符串解析为datetime对象,然后计算这个时间和epoch时间的时间差,转换为秒数返回。
    format = "%Y-%m-%d_%H-%M-%S"
    # epoch = datetime.datetime(2000, 1, 1)
    epoch = datetime.datetime(1970, 1, 1)
    target_date = datetime.datetime.strptime(date_str, format)
    time_delta = target_date - epoch
    return int(time_delta.total_seconds())


# 将输入的文件（ %Y-%m-%d_%H-%M-%S str）时间转为datetime
def date_to_datetime(date_str):
    datetime_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
    return datetime_obj


# 将时间戳秒数格式化为时间 %Y-%m-%d_%H-%M-%S
def seconds_to_date(seconds):
    # start_time = 946684800
    start_time = 0
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    return dt.strftime("%Y-%m-%d_%H-%M-%S")

    # 旧实现
    # current_seconds = seconds + 946684800 - 28800  # 2000/1/1 00:00:00 的秒数，减去八小时
    # time_struct = time.localtime(current_seconds)
    # return time.strftime("%Y-%m-%d_%H-%M-%S", time_struct)


# 将时间戳秒数格式化为时间 %Y-%m-%d_%H-%M-%S（更容易看些，只能用在展示
def seconds_to_date_goodlook_formart(seconds):
    start_time = 0
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    # todo: 这里时间格式需要封为统一的可配置项
    return dt.strftime("%Y/%m/%d   %H:%M:%S")


# 将时间戳秒数转为datetime格式
def seconds_to_datetime(seconds):
    # start_time = 946684800
    start_time = 0
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    return dt


# 将时间戳秒数格式化为时间 %H-%M-%S （当天）
def seconds_to_date_dayHMS(seconds):
    start_time = 0
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    return dt.strftime("%H:%M:%S")


# 将时间戳秒数转为24.小数格式
def seconds_to_24numfloat(seconds):
    dt = seconds_to_datetime(seconds)
    hour = dt.hour
    minute = dt.minute
    minute_decimal = minute / 60
    time_float = hour + minute_decimal
    return round(time_float, 4)


# 将datetime转为时间戳秒数格式
def datetime_to_seconds(dt):
    # epoch = datetime.datetime(2000, 1, 1)
    epoch = datetime.datetime(1970, 1, 1)
    target_date = dt
    time_delta = target_date - epoch
    return int(time_delta.total_seconds())


# 将datatime转为24.格式
def datetime_to_24numfloat(dt):
    hour = dt.hour
    minute = dt.minute
    minute_decimal = minute / 60
    time_float = hour + minute_decimal
    return round(time_float, 2)


# 将datetime输入的时间转为  %Y-%m-%d_%H-%M-%S str
def datetime_to_dateStr(dt):
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


# 将datetime输入的时间转为  %Y-%m-%d str
def datetime_to_dateDayStr(dt):
    return dt.strftime("%Y-%m-%d")


# 将输入的秒数格式化为 1h2m3s str
def convert_seconds_to_hhmmss(seconds):
    seconds = int(round(seconds))
    td = timedelta(seconds=seconds)

    hours = td.seconds // 3600
    minutes = (td.seconds // 60) % 60
    seconds = td.seconds % 60

    time_str = ""
    if hours > 0:
        time_str += str(hours) + "h"
    if minutes > 0 or hours > 0:
        time_str += str(minutes).zfill(2) + "m"
    time_str += str(seconds).zfill(2) + "s"

    return time_str


# 将整个视频文件名中的YYYY-MM-DD_HH-MM-SS转换为1970时间戳
def calc_vid_name_to_timestamp(filename):
    pattern = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
    match = re.search(pattern, filename)
    if match:
        return date_to_seconds(match.group(1))
    else:
        return None


# 将只有天的datetime和只有日期的datetime合为完整的datetime
def merge_date_day_datetime_together(date, today):
    dt = datetime.datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=today.hour,
        minute=today.minute,
        second=today.second,
    )
    return dt


# 将完整的datetime只保留当日时间的datetime.time
def set_full_datetime_to_day_time(dt):
    return dt.timetz()
    # datetime.timetz()方法保留时分秒保留时区信息(如果原datetime包含时区信息), 返回一个只包含时分秒的datetime.time对象。


# 将完整的datetime只保留年月的datetime
def set_full_datetime_to_YYYY_MM(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


# 将完整的datetime只保留年月日的datetime
def set_full_datetime_to_YYYY_MM_DD(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


# 将输入的不完整的datetime补齐为默认年月日时分秒的datetime
def complete_datetime(dt):
    if isinstance(dt, datetime.date):
        # 如果是 date 类型,先转换为 datetime
        dt = datetime.datetime(dt.year, dt.month, dt.day)

    if dt.year == 1900 and dt.month == 1 and dt.day == 1:
        # 日期缺失,使用当前日期
        dt = dt.replace(
            year=datetime.datetime.now().year,
            month=datetime.datetime.now().month,
            day=datetime.datetime.now().day,
        )

    if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
        # 时间缺失,使用当前时间
        dt = dt.replace(
            hour=datetime.datetime.now().hour,
            minute=datetime.datetime.now().minute,
            second=datetime.datetime.now().second,
        )

    return dt


# 通过输入dt中视频名与时间戳计算相对的视频定位时间戳，以
def get_video_timestamp_by_filename_and_abs_timestamp(videofile_name: str, videofile_time: int):
    # videofile_name like 2023-09-08_17-23-50.mp4
    videofile_name = videofile_name[:19]  # 确保只截取到str时间部分
    # vidfilename = os.path.splitext(videofile_name)[0]
    vid_timestamp = videofile_time - date_to_seconds(videofile_name)
    return vid_timestamp


# 查询一个月有几天
def get_days_in_month(year, month):
    # 函数返回一个元组，其中包含该月的第一天是星期几（0表示星期一，1表示星期二，以此类推）和该月的总天数。
    _, num_days = calendar.monthrange(year, month)
    return num_days


# 结束录屏服务进程
def kill_recording():
    try:
        with open(config.record_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())
        check_result = subprocess.run(
            ["taskkill", "/pid", str(check_pid), "-t", "-f"],
            stdout=subprocess.PIPE,
            text=True,
        )
        print(f"utils: The screen recording process has ended. {check_result.stdout}")
    except FileNotFoundError:
        print("utils: Unable to find process lock.")


# 通过数据库内项目计算视频对应时间戳
def calc_vid_inside_time(df, num):
    fulltime = df.iloc[num]["videofile_time"]
    vidfilename = os.path.splitext(df.iloc[num]["videofile_name"])[0]
    # 用记录时的总时间减去视频文件时间（开始记录的时间）即可得到相对的时间
    vidfilename = vidfilename.replace("-INDEX", "")
    vidfilename = vidfilename.replace("-ERROR", "")
    vid_timestamp = fulltime - date_to_seconds(vidfilename)
    print(f"utils: video file fulltime:{fulltime}\n" f" vidfilename:{vidfilename}\n" f" vid_timestamp:{vid_timestamp}\n")
    return vid_timestamp


# 估计索引时间
def estimate_indexing_time():
    count, nocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir)
    record_minutes = int(config.record_seconds) / 60
    ocr_cost_time_table = {"Windows.Media.Ocr.Cli": 5, "ChineseOCR_lite_onnx": 25}
    ocr_cost_time = ocr_cost_time_table[config.ocr_engine]
    estimate_time = int(nocred_count) * int(round(record_minutes)) * int(ocr_cost_time)
    estimate_time_str = convert_seconds_to_hhmmss(estimate_time)
    return estimate_time_str


# 将列表转换为以逗号分隔的字符串
def list_to_string(lst):
    return ", ".join(lst)


# 将字符串转换为列表
def string_to_list(string):
    string = string.replace("，", ",")
    string = string.replace("、", ",")
    split_list = [item.strip() for item in string.split(",")]
    return split_list


# 判断字符串是否包含列表内的元素
def is_str_contain_list_word(string, list_items):
    string = string.lower()
    for item in list_items:
        item = item.lower()
        if item in string:
            return True
    return False


# 乱码清洗策略
def clean_dirty_text(text):
    text = wrap_text_by_symbol(text)
    text = merge_short_lines(text)

    return text


# 移除少于数个字符的行
def delete_short_lines(text, less_than=6):
    lines = text.split("\n")  # 将文本按行分割成列表
    filtered_lines = [line for line in lines if len(line) >= less_than]  # 仅保留长度大于等于6的行
    adjusted_text = "\n".join(filtered_lines)  # 将过滤后的行重新连接成字符串
    return adjusted_text


# 合并少于数个字符的行
def merge_short_lines(text, less_than=20):
    lines = re.split(r"[\n\r]+", text)
    # lines = text.split('\n')
    merged_lines = [lines[0]]

    for line in lines[1:]:
        if len(line) <= less_than:
            merged_lines[-1] += line
        else:
            merged_lines.append(line)

    merged_text = "\n".join(merged_lines)
    return merged_text


# 根据符号进行换行
def wrap_text_by_symbol(text):
    symbol_list = ["。", "！", "？", "），", "）。", "，", "．"]
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    for symbol in symbol_list:
        text = text.replace(symbol, symbol + "\n")  # 将符号替换为换行符+符号

    # 使用正则表达式匹配中文字符之间的空格，并移除
    pattern = re.compile(r"([\u4e00-\u9fa5]+)\s+([\u4e00-\u9fa5]+)")
    text = re.sub(pattern, r"\1\2", text)

    return text


# 去除所有的换行
def wrap_text_by_remove_break(text):
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    # 使用正则表达式匹配中文字符之间的空格，并移除
    pattern = re.compile(r"([\u4e00-\u9fa5]+)\s+([\u4e00-\u9fa5]+)")
    text = re.sub(pattern, r"\1\2", text)
    return text


# 获得base64输入图片的宽高
def get_image_dimensions(base64_image):
    # 解码Base64图像数据
    image_data = base64.b64decode(base64_image)

    # 将图像数据加载到PIL图像对象中
    image = Image.open(BytesIO(image_data))

    # 获取图像的宽度和高度
    width, height = image.size

    # 返回宽度和高度
    return width, height


# 图片路径转base64
def image_to_base64(image_path):
    # 使用cv2加载图像，包括透明通道
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    # 将图像转换为PNG格式
    _, encoded_image = cv2.imencode(".png", image)  # 返回一个元组 (retval, buffer)。retval 表示编码的结果，buffer 是包含图像数据的字节对象。

    # 将图像数据编码为base64字符串
    base64_image = base64.b64encode(encoded_image.tobytes()).decode("utf-8")

    return base64_image


def resize_image_as_base64(img: Image.Image, target_width=config.thumbnail_generation_size_width):
    """
    将图片缩小到等比例、宽度为70px的thumbnail，并返回base64
    """
    # 计算缩放比例
    target_height = int((float(img.size[1]) * float(target_width) / float(img.size[0])))

    img = img.resize((target_width, target_height))
    output_buffer = BytesIO()
    img.save(output_buffer, format="JPEG", quality=config.thumbnail_generation_jpg_quality, optimize=True)
    img_b64 = base64.b64encode(output_buffer.getvalue()).decode("utf-8")

    return img_b64


# 检查db是否是有合法的、正在维护中的锁（超过一定时间则解锁）
def is_maintain_lock_valid(timeout=datetime.timedelta(minutes=16)):
    if os.path.exists(config.maintain_lock_path):
        with open(config.maintain_lock_path, "r", encoding="utf-8") as f:
            last_maintain_locktime = date_to_datetime(f.read())
        if datetime.datetime.now() - last_maintain_locktime > timeout:
            return False
        else:
            return True
    else:
        return False


# 从词库中获取一个随机词语
def get_random_word_from_lexicon():
    directory = "config\\random_lexicon"
    file_list = [filename for filename in os.listdir(directory) if filename.endswith(".txt")]
    words = []

    # 随机读取一个文件后从中抽取词
    filename = random.choice(file_list)
    file_path = os.path.join(directory, filename)
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            word = line.strip()
            if word:
                words.append(word)

    if not words:
        return None

    random_word = random.choice(words)
    return random_word


def get_github_version(
    url="https://raw.githubusercontent.com/yuka-friends/Windrecorder/main/windrecorder/__init__.py",
):
    response = requests.get(url)
    exec(response.text)
    version = __version__
    return version


# 获得当前版本号
def get_current_version():
    local_version = __version__
    return local_version


def get_new_version_if_available():
    remote_version = get_github_version()
    current_version = get_current_version()
    remote_list = remote_version.split(".")
    current_list = current_version.split(".")
    for i, j in zip(remote_list, current_list):
        try:
            if int(i) > int(j):
                return remote_version
        except ValueError:
            if i.split("b") > j.split("b"):
                return remote_version
    return None


# 输入cmd命令，返回结果回显内容
def get_cmd_tool_echo(command):
    print(f"command: {command}")
    proc = subprocess.run(command, capture_output=True)
    encodings_try = ["gbk", "utf-8"]  # 强制兼容
    for enc in encodings_try:
        try:
            text = proc.stdout.decode(enc)
            if text is None or text == "":
                pass
            break
        except UnicodeDecodeError:
            pass

    text = str(text.encode("utf-8").decode("utf-8"))
    return text


# 将list打印为列表项
def print_numbered_list(lst):
    for i, item in enumerate(lst, 1):
        print(f"{i}. {item}")


# 获取系统支持的ocr语言
def get_os_support_lang():
    command = ["ocr_lib\\Windows.Media.Ocr.Cli.exe", "-s"]
    text = get_cmd_tool_echo(command)
    lines = text.replace("\r", "").split("\n")  # 将字符串按行分割为列表
    extracted_lines = lines[1:-1]  # 获取第二行开始的所有行
    return extracted_lines


with open("config\\src\\languages.json", encoding="utf-8") as f:
    d_lang = json.load(f)


def get_text(text_key):
    return d_lang[config.lang].get(text_key, "")


# 查找db字典中最早一项的key值
def get_earliest_datetime_key(dictionary):
    if not dictionary:
        return None

    earliest_datetime = None
    earliest_key = None

    for key, value in dictionary.items():
        if isinstance(value, datetime.datetime):
            if earliest_datetime is None or value < earliest_datetime:
                earliest_datetime = value
                earliest_key = key

    return earliest_key


# 查找db字典中最晚一项的key值
def get_lastest_datetime_key(dictionary):
    if not dictionary:
        return None

    latest_datetime = None
    latest_key = None

    for key, value in dictionary.items():
        if isinstance(value, datetime.datetime):
            if latest_datetime is None or value > latest_datetime:
                latest_datetime = value
                latest_key = key

    return latest_key


# 从db文件名提取YYYY-MM的datatime
def extract_date_from_db_filename(db_file_name, user_name=config.user_name):
    prefix = user_name + "_"

    if db_file_name.startswith(prefix):
        db_file_name = db_file_name[len(prefix) :]

    db_file_name = db_file_name[:7]
    # if db_file_name.endswith(suffix):
    # db_file_name = db_file_name[:-(len(suffix))]

    db_file_name_datetime = datetime.datetime.strptime(db_file_name, "%Y-%m")
    db_file_name_datetime = set_full_datetime_to_YYYY_MM(db_file_name_datetime)
    return db_file_name_datetime


# 从备份的db文件名提取datetime
def extract_datetime_from_db_backup_filename(db_file_name, user_name=config.user_name):
    try:
        db_file_name_extract = db_file_name[-22:-3]
        db_file_name_extract_datetime = date_to_datetime(db_file_name_extract)
        return db_file_name_extract_datetime
    except (IndexError, ValueError):
        return None


# 判断是否已锁屏
def is_screen_locked():
    return ctypes.windll.User32.GetForegroundWindow() == 0


# 判断是否正在休眠
def is_system_awake():
    try:
        return ctypes.windll.User32.GetLastInputInfo() == 0
    except Exception:
        return True


# 检查开机启动项中是否已存在某快捷方式
def is_file_already_in_startup(filename):
    startup_folder = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
    shortcut_path = os.path.join(startup_folder, filename)
    if os.path.exists(shortcut_path):
        return True
    else:
        return False


# 将应用设置为开机启动
def change_startup_shortcut(is_create=True):
    startup_folder = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
    shortcut_path = os.path.join(startup_folder, "start_app.bat.lnk")

    if is_create:
        # 创建快捷方式
        if not os.path.exists(shortcut_path):
            current_dir = os.getcwd()
            bat_path = os.path.join(current_dir, "start_app.bat")
            make_shortcut(bat_path, folder=startup_folder)
            print("record: The shortcut has been created and added to the startup items")
    else:
        # 移除快捷方式
        if os.path.exists(shortcut_path):
            print("record: Shortcut already exists")
            os.remove(shortcut_path)
            print("record: Delete shortcut")


def is_win11():
    return sys.getwindowsversion().build >= 22000


def get_windows_edition():
    return platform.win32_edition()
