import base64
import calendar
import ctypes
import datetime
import json
import os
import random
import re
import socket
import subprocess
import threading
import time
from contextlib import closing
from ctypes import wintypes
from io import BytesIO

import cv2
import mss
import psutil
import requests
from PIL import Image
from pyshortcuts import make_shortcut

from windrecorder import __version__, file_utils
from windrecorder.config import config
from windrecorder.const import DATETIME_FORMAT
from windrecorder.logger import get_logger

logger = get_logger(__name__)


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
def get_display_resolution():  # FIXME: remove all methods
    with mss.mss() as mss_instance:
        return mss_instance.monitors[0]["width"], mss_instance.monitors[0]["height"]


# 获得屏幕数量
def get_display_count():
    with mss.mss() as mss_instance:
        return len(mss_instance.monitors) - 1


# 获得屏幕具体数值
def get_display_info():
    with mss.mss() as mss_instance:
        return mss_instance.monitors


# 根据mss返回的屏幕具体数值格式化显示器信息
def get_display_info_formatted():
    info = get_display_info()
    info_formatted = []
    index = 1
    for i in info[1:]:
        info_formatted.append(f"Display {index}: {i['width']}x{i['height']}")
        index += 1
    return info_formatted


# 获取视频文件信息
def get_vidfilepath_info(vid_filepath) -> dict:
    """
    获取视频文件信息

    常用：
    - duration（持续时长 秒）
    - width height

    当获取失败时，可能抛出错误：CalledProcessError: Command 'ffprobe' returned non-zero exit status 1.
    """
    result = subprocess.check_output(
        f'{config.ffprobe_path} -v quiet -show_streams -select_streams v:0 -of json "{vid_filepath}"', shell=True
    ).decode()

    fields = json.loads(result)["streams"][0]
    return fields


# 将输入的文件（ %Y-%m-%d_%H-%M-%S str）时间转为时间戳秒数
def dtstr_to_seconds(datetime_str):
    # 这里我们先定义了时间格式,然后设置一个epoch基准时间为1970年1月1日。使用strptime()将输入的字符串解析为datetime对象,然后计算这个时间和epoch时间的时间差,转换为秒数返回。
    format = DATETIME_FORMAT
    # epoch = datetime.datetime(2000, 1, 1)
    epoch = datetime.datetime(1970, 1, 1)
    target_date = datetime.datetime.strptime(datetime_str, format)
    time_delta = target_date - epoch
    return int(time_delta.total_seconds())


# 将输入的文件（ %Y-%m-%d_%H-%M-%S str）时间转为datetime
def dtstr_to_datetime(datetime_str):
    datetime_obj = datetime.datetime.strptime(datetime_str, DATETIME_FORMAT)
    return datetime_obj


# 将时间戳秒数格式化为时间 %Y-%m-%d_%H-%M-%S
def seconds_to_date(seconds):
    # start_time = 946684800
    start_time = 0
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    return dt.strftime(DATETIME_FORMAT)

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
    return dt.strftime(DATETIME_FORMAT)


# 将datetime输入的时间转为  %Y-%m-%d str
def datetime_to_dateDayStr(dt):
    return dt.strftime("%Y-%m-%d")


# 将输入的秒数格式化为 1h02m03s str
def convert_seconds_to_hhmmss(seconds, complete_with_zero=True):
    """
    将输入的秒数格式化为 1h02m03s str

    :param seconds: int
    :param complete_with_zero: bool 是否用 0 补齐 m s
    """
    seconds = int(round(seconds))
    # td = timedelta(seconds=seconds)

    hours = seconds // 3600
    minutes = (seconds // 60) % 60
    seconds = seconds % 60

    time_str = ""
    if hours > 0:
        time_str += str(hours) + "h"
    if complete_with_zero:  # 是否在开头补齐0
        if minutes > 0 or hours > 0:
            time_str += str(minutes).zfill(2) + "m"
        time_str += str(seconds).zfill(2) + "s"
    else:
        if minutes > 0 or hours > 0:
            time_str += str(minutes) + "m"
        time_str += str(seconds) + "s"

    return time_str


# 将整个视频文件名中的YYYY-MM-DD_HH-MM-SS转换为1970时间戳
def calc_vid_name_to_timestamp(filename):
    pattern = r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
    match = re.search(pattern, filename)
    if match:
        return dtstr_to_seconds(match.group(1))
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
    return datetime.datetime(year=dt.year, month=dt.month, day=1, hour=0, minute=0, second=0, microsecond=0)


# 将完整的datetime只保留年月日的datetime
def set_full_datetime_to_YYYY_MM_DD(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def get_datetime_in_day_range_pole_by_config_day_begin(dt: datetime.datetime, range="start"):
    """
    根据一天中的一个时间点 datetime，获取在 config.day_begin_minutes 下对应一天的开始/结束点

    param: dt 一天中的一个时间点
    param: range 指定为 start/end 获取开始与结束
    """
    if type(dt) is datetime.date:
        dt = datetime.datetime.combine(dt, datetime.datetime.min.time())

    day_begin_minutes = config.day_begin_minutes
    if range == "start":
        res = dt.replace(hour=day_begin_minutes // 60, minute=day_begin_minutes % 60, second=0, microsecond=0)
    if range == "end":
        _, month_days = calendar.monthrange(dt.year, dt.month)
        if dt.day == month_days:  # month last day
            res = dt.replace(
                month=dt.month + (1 if day_begin_minutes > 0 else 0),
                day=1 if day_begin_minutes > 0 else dt.day,
                hour=(23 + day_begin_minutes // 60) % 24,
                minute=(59 + day_begin_minutes % 60) % 60,
                second=59,
                microsecond=0,
            )
        else:
            res = dt.replace(
                day=dt.day + (1 if day_begin_minutes > 0 else 0),
                hour=(23 + day_begin_minutes // 60) % 24,
                minute=(59 + day_begin_minutes % 60) % 60,
                second=59,
                microsecond=0,
            )

    return res


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
    vid_timestamp = videofile_time - dtstr_to_seconds(videofile_name)
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
        logger.info(f"utils: The screen recording process has ended. {check_result.stdout}")
    except FileNotFoundError:
        logger.error("utils: Unable to find process lock.")


# 通过数据库内项目计算视频对应时间戳
def calc_vid_inside_time(df, num):
    fulltime = df.iloc[num]["videofile_time"]
    vidfilename = os.path.splitext(df.iloc[num]["videofile_name"])[0][:19]
    # 用记录时的总时间减去视频文件时间（开始记录的时间）即可得到相对的时间
    vid_timestamp = fulltime - dtstr_to_seconds(vidfilename)
    logger.info(f"utils: video file fulltime:{fulltime}\n" f" vidfilename:{vidfilename}\n" f" vid_timestamp:{vid_timestamp}\n")
    return vid_timestamp


# 估计索引时间
def estimate_indexing_time():
    count, nocred_count = file_utils.get_videos_and_ocred_videos_count(config.record_videos_dir_ud)
    record_minutes = int(config.record_seconds) / 60
    ocr_cost_time_table = {"Windows.Media.Ocr.Cli": 5, "ChineseOCR_lite_onnx": 25, "PaddleOCR": 25}
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
    string = str(string)
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


def resize_image_as_base64_as_thumbnail_via_filepath(img_path):
    """将图片缩小到等比例、宽度为70px的thumbnail，并返回base64"""
    img = Image.open(img_path)
    img_b64 = resize_image_as_base64(img)

    return img_b64


# 检查db是否是有合法的、正在维护中的锁（超过一定时间则解锁）
def is_maintain_lock_valid(timeout=datetime.timedelta(minutes=16)):
    if os.path.exists(config.maintain_lock_path):
        with open(config.maintain_lock_path, "r", encoding="utf-8") as f:
            last_maintain_locktime = dtstr_to_datetime(f.read())
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
    global_vars = {}
    exec(response.text, global_vars)
    version = global_vars["__version__"]
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
    logger.info(f"command: {command}")
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
def print_numbered_list(lst, indent=True):
    for i, item in enumerate(lst, 1):
        print_res = ""
        if indent:
            print_res += "    "
        print_res += f"{i}. {item}"
        print(print_res)


# 获取系统支持的ocr语言
def get_os_support_lang():
    command = ["ocr_lib\\Windows.Media.Ocr.Cli.exe", "-s"]
    text = get_cmd_tool_echo(command)
    lines = text.replace("\r", "").split("\n")  # 将字符串按行分割为列表
    extracted_lines = lines[1:-1]  # 获取第二行开始的所有行
    return extracted_lines


with open(os.path.join(config.config_src_dir, "languages.json"), encoding="utf-8") as f:
    d_lang = json.load(f)


def get_text(text_key):
    fallback_copy = f"({text_key}) not found in i18n, please feedback to contributors."
    if text_key in d_lang[config.lang]:
        return d_lang[config.lang].get(text_key, fallback_copy)
    else:
        if text_key in d_lang["en"]:
            return d_lang["en"].get(text_key, fallback_copy)
        else:
            return fallback_copy


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

    db_file_name_datetime = datetime.datetime.strptime(db_file_name, "%Y-%m")
    db_file_name_datetime = set_full_datetime_to_YYYY_MM(db_file_name_datetime)
    return db_file_name_datetime


# 从备份的db文件名提取datetime
def extract_datetime_from_db_backup_filename(db_file_name, user_name=config.user_name):
    try:
        db_file_name_extract = db_file_name[-22:-3]
        db_file_name_extract_datetime = dtstr_to_datetime(db_file_name_extract)
        return db_file_name_extract_datetime
    except (IndexError, ValueError):
        return None


# 判断是否已锁屏
def is_screen_locked():
    # return ctypes.windll.User32.GetForegroundWindow() == 0
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] == "LogonUI.exe":
            return True  # locked
    return False  # not lock


# 判断是否正在休眠
def is_system_awake():
    try:
        return ctypes.windll.User32.GetLastInputInfo() == 0
    except Exception:
        return True


# 查询 key 在有序的 dict 中的第几项
def find_key_position_in_dict(dictionary, key):
    keys = list(dictionary.keys())  # 获取字典的键列表
    position = keys.index(key) if key in keys else 0  # 查找键的位置，没有则返回 0
    return position


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
            logger.info("record: The shortcut has been created and added to the startup items")
    else:
        # 移除快捷方式
        if os.path.exists(shortcut_path):
            logger.info("record: Shortcut already exists")
            os.remove(shortcut_path)
            logger.info("record: Delete shortcut")


def is_process_running(pid, compare_process_name):
    """根据进程 PID 与名字比对检测进程是否存在"""
    pid = int(pid)
    try:
        # 确保 PID 与进程名一致
        process = psutil.Process(pid)
        return process.is_running() and process.name() == compare_process_name
    except psutil.NoSuchProcess:
        return False


def get_process_id(process_name):
    """通过进程名称获取进程 ID"""
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] == process_name:
            return proc.info["pid"]
    return None


def find_available_port():
    """找到最小可用于 web 服务的本地端口"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# 查找列表项中包含字符串的项
def find_strings_list_with_substring(string_list, substring):
    result = []
    for string in string_list:
        if substring in string:
            result.append(string)
    return result


def check_ffmpeg_and_ffprobe():
    """
    检查 ffmpeg 与 ffprobe 是否可用，返回(是否均可用:bool, 不可用原因:str)
    """
    available_ffmpeg = False
    available_ffprobe = False
    try:
        subprocess.check_output(f"{config.ffmpeg_path} -version", shell=True)
        available_ffmpeg = True
    except subprocess.CalledProcessError:
        logger.error("ffmpeg is not available.")
    except Exception as e:
        logger.error(f"Unexpected Error. {e}")

    try:
        subprocess.check_output(f"{config.ffprobe_path} -version", shell=True)
        available_ffprobe = True
    except subprocess.CalledProcessError:
        logger.error("ffprobe is not available.")
    except Exception as e:
        logger.error(f"Unexpected Error. {e}")

    if available_ffmpeg and available_ffprobe:
        return True, ""
    elif not available_ffmpeg and not available_ffprobe:
        return False, "FFmpeg and FFprobe are not available.\nPlease check the installation."
    elif not available_ffmpeg:
        return False, "FFmpeg is not available.\nPlease check the installation."
    elif not available_ffprobe:
        return False, "FFprobe is not available.\nPlease check the installation."
    return False, "Unexpected Error on checking ffmpeg and ffprobe available."


def ensure_list_divisible_by_num(lst, num: int):
    while len(lst) % num != 0:
        lst.append(0)
    return lst


def get_screenshot_of_display(display_index):
    """display_index start from 1"""
    with mss.mss() as sct:
        monitor = sct.monitors[display_index]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    return img


def hex_to_rgb(hex_color):
    """
    将十六进制颜色字符串转换为RGB元组。
    :param hex_color: 十六进制颜色字符串，例如"#FFFFFF"或"FFFFFF"
    :return: RGB元组，例如(255, 255, 255)
    """
    # 移除可能的'#'符号
    hex_color = hex_color.strip("#")
    # 按RGB三个部分分割并转换为整数
    rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return rgb


def is_power_plugged_in():
    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE),
            ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE),
            ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD),
            ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    GetSystemPowerStatus = ctypes.windll.kernel32.GetSystemPowerStatus
    GetSystemPowerStatus.argtypes = [ctypes.POINTER(SYSTEM_POWER_STATUS)]
    GetSystemPowerStatus.restype = wintypes.BOOL

    status = SYSTEM_POWER_STATUS()
    if GetSystemPowerStatus(ctypes.byref(status)):
        # 如果ACLineStatus为1，则表示笔记本电脑接入了电源
        if status.ACLineStatus == 1:
            return True
        else:
            return False
    else:
        # 如果获取电源状态失败，则假设为台式机，返回True
        return True
