import os

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
        print(f"已创建文件夹：{folder_name}")
    else:
        print(f"文件夹已存在：{folder_name}")


# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def add_OCRED_suffix(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


# 查询videos文件夹下的文件数量、未被ocr的文件数量
def get_videos_and_ocred_videos_count(folder_path):
    count = 0
    nocred_count = 0
    for filename in os.listdir(folder_path):
        count += 1
        if not filename.split('.')[0].endswith("-OCRED"):
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
  video_path = os.path.join(config.record_videos_dir, video_name) 
  ocred_video_name = os.path.splitext(video_name)[0] + '-OCRED' + os.path.splitext(video_name)[1]
  ocred_path = os.path.join(config.record_videos_dir, ocred_video_name)

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
