import json
import os
import re
import shutil
import stat
import time
from json import JSONDecodeError
from pathlib import Path

import pandas as pd
from send2trash import send2trash

import windrecorder.utils as utils
from windrecorder.config import config
from windrecorder.const import (
    DATETIME_FORMAT_PATTERN,
    SCREENSHOT_CACHE_FILEPATH,
    SYSTEM_DIRS,
)
from windrecorder.logger import get_logger

logger = get_logger(__name__)


# 清空指定目录下的所有文件和子目录
def empty_directory(path):
    if len(path) == 0 or not os.path.exists(path):
        return
    with os.scandir(path) as it:
        for entry in it:
            print(f"cleaning: {entry.path}")
            try:
                if entry.is_dir():
                    shutil.rmtree(entry.path)
                else:
                    os.remove(entry.path)
            except Exception as e:
                logger.error(e)


# 检查目录是否存在，若无则创建
def ensure_dir(folder_name):
    # 获取当前工作目录
    current_directory = os.getcwd()

    # 拼接文件夹路径
    folder_path = os.path.join(current_directory, folder_name)

    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        # 创建文件夹
        os.makedirs(folder_path, exist_ok=True)
        logger.info(f"files: created folder {folder_name}")
    else:
        logger.debug(f"files: folder existed:{folder_name}")


# 输入一个视频文件名，返回其%Y-%m的年月信息作为子文件夹
def convert_vid_filename_as_YYYY_MM(vid_filename):
    return vid_filename[:7]


# 输入一个视频文件名，返回其完整的相对路径
def convert_vid_filename_as_vid_filepath(vid_filename):
    return os.path.join(config.record_videos_dir_ud, convert_vid_filename_as_YYYY_MM(vid_filename), vid_filename)


# 查询videos文件夹下的文件数量、未被ocr的文件数量
def get_videos_and_ocred_videos_count(folder_path):
    count = 0
    nocred_count = 0

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            count += 1
            if "-OCRED" not in file.split(".")[0]:
                if "-ERROR" not in file.split(".")[0]:
                    nocred_count += 1

    return count, nocred_count


# 遍历XXX文件夹下有无文件中包含入参str的文件名
def find_filename_in_dir(dir, search_str):
    if not os.path.isdir(dir):
        return False

    for filename in os.listdir(dir):
        if search_str in filename:
            return True

    return False


# 检查视频文件是否存在
def check_video_exist_in_videos_dir(video_name):
    try:
        exist_videofiles_list = os.listdir(
            os.path.join(config.record_videos_dir_ud, convert_vid_filename_as_YYYY_MM(video_name))
        )
        video_filename_list = utils.find_strings_list_with_substring(
            exist_videofiles_list, video_name.split(".")[0]
        )  # 获取文件夹列表中对应文件名
        if video_filename_list:
            return video_filename_list[0]
        else:
            return None
    except FileNotFoundError:
        return None


# 统计文件夹大小
def get_dir_size(dir):
    size = 0
    for root, _, files in os.walk(dir):
        size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
    return size


# 查询文件的修改时间是否超过一定间隔
def is_file_modified_recently(file_path, time_gap=30):
    """time_gap 为 minutes"""
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
    filepath_list = []
    if os.path.exists(dir):
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


# 取得文件夹下的第一级文件夹列表
def get_file_dir_list_first_level(dir):
    return [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]


# 根据已有的文件列表，返回指定时间段的视频文件夹内、已索引了的视频路径列表（包括未压缩的与已压缩的）
def get_videofile_path_list_by_time_range(filepath_list, start_datetime=None, end_datetime=None):
    filepath_list_daterange = []
    for filepath in filepath_list:
        if "-OCRED" in filepath:
            if start_datetime is None or end_datetime is None:  # 如果不指定时间段，返回所有结果
                filepath_list_daterange.append(filepath)
            else:
                filename_extract_date = os.path.basename(filepath)[:18]
                file_datetime = utils.dtstr_to_datetime(filename_extract_date)
                if start_datetime <= file_datetime <= end_datetime:
                    filepath_list_daterange.append(filepath)

    return filepath_list_daterange


def get_screenshots_cache_dir_lst(directory=SCREENSHOT_CACHE_FILEPATH):
    """获取所有合法的截图缓存文件夹目录"""
    pattern = DATETIME_FORMAT_PATTERN
    matching_folders = []
    for item in os.listdir(directory):
        folder_path = os.path.join(directory, item)
        if os.path.isdir(folder_path) and re.match(pattern, item):
            matching_folders.append(folder_path)
    return matching_folders


def get_screenshots_cache_dir_by_video_file_name(video_filename):
    """根据视频文件名获取其截图缓存文件夹目录"""
    cache_dir_lst = get_screenshots_cache_dir_lst()
    res_lst = [dir for dir in cache_dir_lst if video_filename[:19] in dir]
    if res_lst:
        return res_lst[0]
    else:
        return None


# 根据已有的视频文件夹路径列表，生成对应datetime的词典
def get_videofile_path_dict_datetime(filepath_list):
    result_dict = {}
    for filepath in filepath_list:
        filename = os.path.basename(filepath)[:18]
        datetime_value = utils.dtstr_to_datetime(filename)
        result_dict[filepath] = datetime_value
    return result_dict


# 根据datetime生成数据库带db路径的文件名
def get_db_filepath_by_datetime(dt, db_dir=config.db_path_ud, user_name=config.user_name):
    filename = user_name + "_" + dt.strftime("%Y-%m") + "_wind.db"
    filepath = os.path.join(db_dir, filename)
    return filepath


# 将dataframe存储到csv文件
def save_dataframe_to_path(dataframe, file_path="cache/temp.csv"):
    """
    将DataFrame数据保存到指定路径
    """
    ensure_dir(os.path.dirname(file_path))
    dataframe.to_csv(file_path, index=False)  # 使用to_csv()方法将DataFrame保存为CSV文件（可根据需要选择其他文件格式）
    logger.debug(f"files: DataFrame has been saved at {file_path}")


# 从csv文件读取dataframe
def read_dataframe_from_path(file_path="cache/temp.csv"):
    """
    从指定路径读取数据到DataFrame
    """
    if not os.path.exists(file_path):
        return None

    dataframe = pd.read_csv(file_path)  # 使用read_csv()方法读取CSV文件（可根据文件格式选择对应的读取方法）
    return dataframe


def save_dict_as_json_to_path(data: dict, filepath):
    """将 dict 保存到 json"""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"files: json has been saved at {filepath}")


def read_json_as_dict_from_path(filepath):
    """从 json 读取 dict"""
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except JSONDecodeError:
        return None


# 读取 extension 文件夹下所有插件名与对应 meta info
def get_extension(extension_filepath="extension"):
    dir_list = get_file_dir_list_first_level(extension_filepath)
    extension_dict = {}
    for dir in dir_list:
        try:
            with open(f"{extension_filepath}\\{dir}\\meta.json", encoding="utf-8") as file:
                data = json.load(file)
                extension_dict[data["extension_name"]] = data
        except Exception as e:
            logger.warning(str(e))
    return extension_dict


# 返回语言所有的近义词表，若无返回 None
def get_synonyms_vdb_txt_filepath(lang):
    vdb_filepath = os.path.join(config.config_src_dir, "synonyms", f"synonyms_{lang}.index")
    words_txt_filepath = os.path.join(config.config_src_dir, "synonyms", f"synonyms_{lang}.txt")
    if os.path.exists(vdb_filepath) and os.path.exists(words_txt_filepath):
        return vdb_filepath, words_txt_filepath
    else:
        return None, None


# 读取txt文件中每一行作为一个列表
def read_txt_as_list(file_path):
    with open(file_path, "r", encoding="utf8") as f:
        content_list = [line.strip() for line in f.readlines()]
    return content_list


# 尽可能安全地删除文件
def safe_delete(target_path):
    """
    安全删除文件或目录

    参数:
        target_path (str): 要删除的路径

    返回:
        tuple: (success: bool, message: str)
    """

    def is_root_directory(abs_path):
        """检查是否为根目录"""
        path_obj = Path(abs_path)
        return path_obj.parent == path_obj

    def is_system_sensitive(abs_path):
        """检查是否涉及系统敏感目录"""
        path_parts = Path(abs_path).parts
        return any(part.lower() in SYSTEM_DIRS for part in path_parts)

    def remove_readonly(func, path, _):
        """处理只读文件"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        # 规范化路径并解析符号链接
        abs_path = os.path.realpath(target_path)

        # 基础验证
        if not os.path.exists(abs_path):
            return False, "The target path does not exist"

        if is_root_directory(abs_path):
            return False, "Disable root directory deletion"

        if is_system_sensitive(abs_path):
            return False, "Involving system protection directories"

        # 用户重要目录保护（可选扩展）
        important_dirs = {
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
        }
        if Path(abs_path).resolve() in {Path(p).resolve() for p in important_dirs}:
            return False, "Important user directories"

        # 执行删除操作
        if os.path.isfile(abs_path):
            os.remove(abs_path)
        else:
            shutil.rmtree(abs_path, onerror=remove_readonly)

        # 二次验证确保已删除
        if os.path.exists(abs_path):
            return False, "Deletion operation not completed"

        return True, "Deleted successfully"

    except PermissionError as e:
        return False, f"Insufficient permissions: {str(e)}"
    except FileNotFoundError:
        return True, "The file no longer exists"  # 可能被其他进程删除
    except Exception as e:
        return False, f"Unknown error: {str(e)}"


# 删除文件入口
def delete_files_via_config(target_path):
    try:
        if config.recycle_deleted_files:
            logger.info(f"move file to recycle bin: {target_path}")
            send2trash(target_path)
        else:
            logger.info(f"delete file: {target_path}")
            operation_success, operation_expection = safe_delete(target_path)
            if not operation_success:
                raise Exception(operation_expection)
    except Exception as e:
        try:
            logger.warning(f"operation failed: {str(e)}, trying to move to recycle bin")
            send2trash(target_path)
        except Exception as e:
            logger.warning(e)
