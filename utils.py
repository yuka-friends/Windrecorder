import os
import shutil
import json
import datetime
from datetime import timedelta
import time

import pyautogui

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


# 更写 config.json
def config_set(name, value):
    with open('config.json', encoding='utf-8') as f:
        config = json.load(f)

    config[name] = value

    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_screen_resolution():
    return pyautogui.size()

# 将输入的文件时间转为2000s秒数
def date_to_seconds(date_str):
    print("——将输入的文件时间转为2000s秒数")
    # 这里我们先定义了时间格式,然后设置一个epoch基准时间为2000年1月1日。使用strptime()将输入的字符串解析为datetime对象,然后计算这个时间和epoch时间的时间差,转换为秒数返回。
    format = "%Y-%m-%d_%H-%M-%S"
    epoch = datetime.datetime(2000, 1, 1)
    target_date = datetime.datetime.strptime(date_str, format)
    time_delta = target_date - epoch
    print(time_delta.total_seconds())
    return int(time_delta.total_seconds())


# 将2000s秒数转为时间
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


# 将输入的秒数格式化为HH-MM-SS
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
