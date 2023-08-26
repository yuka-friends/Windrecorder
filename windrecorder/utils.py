import os
import shutil
import json
import datetime
from datetime import timedelta
import subprocess
import time
import threading
import re

import pyautogui

import windrecorder.files as files
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

def empty_directory(path):
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)


# 统计文件夹大小
def get_dir_size(dir):
    size = 0
    for root, _, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size


# 获得屏幕分辨率
def get_screen_resolution():
    return pyautogui.size()


# 将输入的文件（ %Y-%m-%d_%H-%M-%S str）时间转为2000s秒数
def date_to_seconds(date_str):
    print("——将输入的文件时间转为2000s秒数")
    # 这里我们先定义了时间格式,然后设置一个epoch基准时间为2000年1月1日。使用strptime()将输入的字符串解析为datetime对象,然后计算这个时间和epoch时间的时间差,转换为秒数返回。
    format = "%Y-%m-%d_%H-%M-%S"
    epoch = datetime.datetime(2000, 1, 1)
    target_date = datetime.datetime.strptime(date_str, format)
    time_delta = target_date - epoch
    print(time_delta.total_seconds())
    return int(time_delta.total_seconds())


# 将2000s秒数格式化为时间 %Y-%m-%d_%H-%M-%S
def seconds_to_date(seconds):
    start_time = 946684800
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    # dt = dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
    return dt.strftime("%Y-%m-%d_%H-%M-%S")

    # 旧实现
    # current_seconds = seconds + 946684800 - 28800  # 2000/1/1 00:00:00 的秒数，减去八小时
    # time_struct = time.localtime(current_seconds)
    # return time.strftime("%Y-%m-%d_%H-%M-%S", time_struct)


# 将2000s秒数转为datetime格式
def seconds_to_datetime(seconds):
    start_time = 946684800
    dt = datetime.datetime.utcfromtimestamp(start_time + seconds)
    return dt


# 将2000s秒数转为24.格式
def seconds_to_24numfloat(seconds):
    dt = seconds_to_datetime(seconds)
    hour = dt.hour
    minute = dt.minute
    minute_decimal = minute / 60 
    time_float = hour + minute_decimal
    return round(time_float, 2)


# 将datetime转为2000s秒数格式
def datetime_to_seconds(dt):
    epoch = datetime.datetime(2000, 1, 1)
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


# 将输入的秒数格式化为 HH-MM-SS str
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


# 将只有天的datetime和只有日期的datetime合为完整的datetime
def merge_date_day_datetime_together(date,today):
    dt = datetime.datetime(
        year=date.year, 
        month=date.month, 
        day=date.day,
        hour=today.hour,
        minute=today.minute,
        second=today.second
    )
    return dt


# 将整个视频文件名中的YYYY-MM-DD_HH-MM-SS转换为2000s时间戳
def calc_vid_name_to_timestamp(filename):
    pattern = r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})'
    match = re.search(pattern, filename)
    if match:
        return date_to_seconds(match.group(1))
    else:
        return None


# 结束录屏服务进程
def kill_recording():
    with open("lock_file_record", encoding='utf-8') as f:
        check_pid = int(f.read())
    check_result = subprocess.run(['taskkill', '/pid', str(check_pid), '-t','-f'], stdout=subprocess.PIPE, text=True)
    # st.toast(f"已结束录屏进程，{check_result.stdout}")
    print(f"已结束录屏进程，{check_result.stdout}")


# 通过数据库内项目计算视频对应时间戳
def calc_vid_inside_time(df, num):
    fulltime = df.iloc[num]['videofile_time']
    vidfilename = os.path.splitext(df.iloc[num]['videofile_name'])[0]
    # 用记录时的总时间减去视频文件时间（开始记录的时间）即可得到相对的时间
    vid_timestamp = fulltime - date_to_seconds(vidfilename)
    print("fulltime:" + str(fulltime) + "\n vidfilename:" + str(vidfilename) + "\n vid_timestamp:" + str(vid_timestamp))
    return vid_timestamp


# 估计索引时间
def estimate_indexing_time():
    count, nocred_count = files.get_videos_and_ocred_videos_count(config.record_videos_dir)
    record_minutes = int(config.record_seconds)/60
    ocr_cost_time_table = {
        "Windows.Media.Ocr.Cli":15,
        "ChineseOCR_lite_onnx":25
    }
    ocr_cost_time = ocr_cost_time_table[config.ocr_engine]
    estimate_time = int(nocred_count) * int(round(record_minutes)) * int(ocr_cost_time)
    estimate_time_str = convert_seconds_to_hhmmss(estimate_time)
    return estimate_time_str