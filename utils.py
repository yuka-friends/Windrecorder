import os
import shutil
import json
import datetime
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
    current_seconds = seconds + 946684800 - 28800  # 2000/1/1 00:00:00 的秒数
    time_struct = time.localtime(current_seconds)
    return time.strftime("%Y-%m-%d_%H-%M-%S", time_struct)