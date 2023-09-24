import os
import time
import datetime

from windrecorder.config import config
import windrecorder.files as files
import windrecorder.utils as utils

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
        print(f"已创建文件夹：{folder_name}")
    else:
        print(f"文件夹已存在：{folder_name}")


# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def add_OCRED_suffix(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 输入一个视频文件名，返回其%Y-%m的年月信息作为子文件夹
def convert_vid_filename_as_YYYY_MM(vid_filename):
  return vid_filename[:7]
      

# 查询videos文件夹下的文件数量、未被ocr的文件数量
def get_videos_and_ocred_videos_count(folder_path):
    count = 0
    nocred_count = 0

    for root,dirs,files in os.walk(folder_path):
        for file in files:
          count += 1
          if not file.split('.')[0].endswith("-OCRED"):
            nocred_count += 1

    return count, nocred_count


# 遍历XXX文件夹下有无文件中包含入参str的文件名
def find_filename_in_dir(dir,search_str):
  dir = 'videos'
  check_and_create_folder(dir)
  
  for filename in os.listdir(dir):
    if search_str in filename:
      return True
      
  return False


# 检查视频文件是否存在
def check_video_exist_in_videos_dir(video_name):
  videofile_path_month_dir = files.convert_vid_filename_as_YYYY_MM(video_name)
  video_path = os.path.join(config.record_videos_dir,videofile_path_month_dir, video_name) 
  ocred_video_name = os.path.splitext(video_name)[0] + '-OCRED' + os.path.splitext(video_name)[1]
  ocred_path = os.path.join(config.record_videos_dir,videofile_path_month_dir, ocred_video_name)

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
def is_file_modified_recently(file_path,time_gap=30):
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



# 从db文件名提取YYYY-MM
def extract_date_from_db_filename(db_file_name, user_name = config.user_name):
  prefix = user_name + "_"
  suffix = "_wind.db"

  if db_file_name.startswith(prefix):
     db_file_name = db_file_name[len(prefix):]

  if db_file_name.endswith(suffix):
     db_file_name = db_file_name[:-(len(suffix))]

  db_file_name_datetime = datetime.datetime.strptime(db_file_name,"%Y-%m")
  db_file_name_datetime = utils.set_full_datetime_to_YYYY_MM_DD(db_file_name_datetime)
  return db_file_name_datetime


# 取得db文件夹下的完整数据库路径列表
def get_db_file_path_dict(db_dir=config.db_path, user_name = config.user_name):
  check_and_create_folder(db_dir)

  db_list = os.listdir(db_dir)
  if len(db_list) == 0:
     # 目录为空
     return None
  else:
    # 去除非当前用户的内容
    for file in db_list:
       if not file.startswith(user_name):
          db_list.remove(file)

    db_list_datetime = [extract_date_from_db_filename(file) for file in db_list]

    db_list, db_list_datetime = zip(*sorted(zip(db_list, db_list_datetime),key=lambda x:x[1]))

    items = zip(db_list, db_list_datetime)   # 使用zip将两个列表打包成元组的列表
    db_dict = dict(items)   # 将zip结果转换为字典
    # return list(db_list),list(db_list_datetime)
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
def get_db_filepath_by_datetime(dt, db_dir=config.db_path, user_name = config.user_name):
   filename = user_name + "_" + dt.strftime("%Y-%m") + "_wind.db"
   filepath = os.path.join(db_dir,filename)
   return filepath

