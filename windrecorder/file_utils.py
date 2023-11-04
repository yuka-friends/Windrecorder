import datetime
import os
import time

import pandas as pd

import windrecorder.utils as utils
from windrecorder import file_utils
from windrecorder.config import config


# 检查目录是否存在，若无则创建
def check_and_create_folder(folder_name):
    # 获取当前工作目录
    current_directory = os.getcwd()

    # 拼接文件夹路径
    folder_path = os.path.join(current_directory, folder_name)

    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        # 创建文件夹
        os.makedirs(folder_path)
        print(f"files: created folder {folder_name}")
    else:
        print(f"files: folder existed:{folder_name}")


# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def add_OCRED_suffix(video_name):
    video_name = video_name.replace("-INDEX", "")
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 将数据库的视频名加上-COMPRESS-OCRED标志，使之能正常读取到
def add_COMPRESS_OCRED_suffix(video_name):
    vidname = os.path.splitext(video_name)[0] + "-COMPRESS-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 输入一个视频文件名，返回其%Y-%m的年月信息作为子文件夹
def convert_vid_filename_as_YYYY_MM(vid_filename):
    return vid_filename[:7]


# 查询videos文件夹下的文件数量、未被ocr的文件数量
def get_videos_and_ocred_videos_count(folder_path):
    count = 0
    nocred_count = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            count += 1
            if not file.split(".")[0].endswith("-OCRED"):
                if not file.split(".")[0].endswith("-ERROR"):
                    nocred_count += 1

    return count, nocred_count


# 遍历XXX文件夹下有无文件中包含入参str的文件名
def find_filename_in_dir(dir, search_str):
    dir = "videos"
    check_and_create_folder(dir)

    for filename in os.listdir(dir):
        if search_str in filename:
            return True

    return False


# 检查视频文件是否存在
def check_video_exist_in_videos_dir(video_name):
    videofile_path_month_dir = file_utils.convert_vid_filename_as_YYYY_MM(video_name)
    video_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, video_name)
    ocred_video_name = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    ocred_path = os.path.join(config.record_videos_dir, videofile_path_month_dir, ocred_video_name)

    if os.path.exists(video_path):
        return video_name
    elif os.path.exists(ocred_path):
        return ocred_video_name
    else:
        return None


# 统计文件夹大小
def get_dir_size(dir):
    size = 0
    for root, _, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size


# 查询文件的修改时间是否超过一定间隔
def is_file_modified_recently(file_path, time_gap=30):
    # time_gap 为 minutes
    # 获取文件的修改时间戳
    modified_timestamp = os.path.getmtime(file_path)

    # 获取当前时间戳
    current_timestamp = time.time()

    # 计算时间差（以分钟为单位）
    time_diff_minutes = (current_timestamp - modified_timestamp) / 60

    # 判断时间差是否超过30分钟
    if time_diff_minutes > time_gap:
        return False
    else:
        return True


# 对比A文件是否比B文件新（新的文件时间戳大 -> 结果为正）
def is_fileA_modified_newer_than_fileB(file_path_A, file_path_B):
    # time_gap 为 minutes
    # 获取文件的修改时间戳
    modified_timestamp_A = os.path.getmtime(file_path_A)
    modified_timestamp_B = os.path.getmtime(file_path_B)

    # 计算时间差
    time_diff_minutes = (modified_timestamp_A - modified_timestamp_B) / 60

    if time_diff_minutes > 0:
        return True, time_diff_minutes
    else:
        return False, time_diff_minutes


# 取得文件夹下所有文件名并返回文件名列表、完整文件目录列表
def get_file_path_list(dir):
    if os.path.exists(dir):
        filepath_list = []
        for root, dirs, files in os.walk(dir):
            for file in files:
                file_path = os.path.join(root, file)
                filepath_list.append(file_path)

    return filepath_list


# 取得文件夹下的第一级文件名列表
def get_file_path_list_first_level(dir):
    file_names = []
    for filename in os.listdir(dir):
        if os.path.isfile(os.path.join(dir, filename)):
            file_names.append(filename)
    return file_names


# 根据已有的文件列表，返回指定时间段的视频文件夹内、已索引了的视频路径列表（包括未压缩的与已压缩的）
def get_videofile_path_list_by_time_range(filepath_list, start_datetime=None, end_datetime=None):
    filepath_list_daterange = []
    for filepath in filepath_list:
        if filepath.endswith("-OCRED.mp4"):
            if start_datetime is None or end_datetime is None:  # 如果不指定时间段，返回所有结果
                filepath_list_daterange.append(filepath)
            else:
                filename_extract_date = os.path.basename(filepath)[:18]
                file_datetime = utils.date_to_datetime(filename_extract_date)
                if start_datetime <= file_datetime <= end_datetime:
                    filepath_list_daterange.append(filepath)

    return filepath_list_daterange


# 根据已有的视频文件夹路径列表，生成对应datetime的词典
def get_videofile_path_dict_datetime(filepath_list):
    result_dict = {}
    for filepath in filepath_list:
        filename = os.path.basename(filepath)[:18]
        datetime_value = utils.date_to_datetime(filename)
        result_dict[filepath] = datetime_value
    return result_dict


# 从db文件名提取YYYY-MM的datatime
def extract_date_from_db_filename(db_file_name, user_name=config.user_name):
    prefix = user_name + "_"

    if db_file_name.startswith(prefix):
        db_file_name = db_file_name[len(prefix) :]

    db_file_name = db_file_name[:7]
    # if db_file_name.endswith(suffix):
    # db_file_name = db_file_name[:-(len(suffix))]

    db_file_name_datetime = datetime.datetime.strptime(db_file_name, "%Y-%m")
    db_file_name_datetime = utils.set_full_datetime_to_YYYY_MM(db_file_name_datetime)
    return db_file_name_datetime


# 从备份的db文件名提取datetime
def extract_datetime_from_db_backup_filename(db_file_name, user_name=config.user_name):
    try:
        db_file_name_extract = db_file_name[-22:-3]
        db_file_name_extract_datetime = utils.date_to_datetime(db_file_name_extract)
        return db_file_name_extract_datetime
    except (IndexError, ValueError):
        return None


# 取得数据库文件夹下的完整数据库路径列表
def get_db_file_path_dict(db_dir=config.db_path, user_name=config.user_name):
    check_and_create_folder(db_dir)

    db_list = os.listdir(db_dir)
    if len(db_list) == 0:
        # 目录为空
        return None
    else:
        # 去除非当前用户且临时使用的内容
        for file in db_list:
            if not file.startswith(user_name) or file.endswith("_TEMP_READ.db"):
                db_list.remove(file)

        db_list_datetime = [extract_date_from_db_filename(file) for file in db_list]

        db_list, db_list_datetime = zip(*sorted(zip(db_list, db_list_datetime), key=lambda x: x[1]))

        items = zip(db_list, db_list_datetime)  # 使用zip将两个列表打包成元组的列表
        db_dict = dict(items)  # 将zip结果转换为字典
        return db_dict


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


# 根据datetime生成数据库带db路径的文件名
def get_db_filepath_by_datetime(dt, db_dir=config.db_path, user_name=config.user_name):
    filename = user_name + "_" + dt.strftime("%Y-%m") + "_wind.db"
    filepath = os.path.join(db_dir, filename)
    return filepath


# 将dataframe存储到csv文件
def save_dataframe_to_path(dataframe, file_path="cache/temp.csv"):
    """
    将DataFrame数据保存到指定路径

    参数:
    dataframe (pandas.DataFrame): 要保存的DataFrame数据
    file_path (str): 要保存到的文件路径 默认为cache

    返回:
    无
    """
    check_and_create_folder(os.path.dirname(file_path))
    dataframe.to_csv(file_path, index=False)  # 使用to_csv()方法将DataFrame保存为CSV文件（可根据需要选择其他文件格式）
    print("files: DataFrame has been saved at ", file_path)


# 从csv文件读取dataframe
def read_dataframe_from_path(file_path="cache/temp.csv"):
    """
    从指定路径读取数据到DataFrame

    参数:
    file_path (str): 要读取数据的文件路径 默认为cache

    返回:
    pandas.DataFrame: 读取到的DataFrame数据
    """
    check_and_create_folder(os.path.dirname(file_path))
    if len(os.path.dirname(file_path)) == 0:
        # 目录为空
        return None

    dataframe = pd.read_csv(file_path)  # 使用read_csv()方法读取CSV文件（可根据文件格式选择对应的读取方法）
    return dataframe
