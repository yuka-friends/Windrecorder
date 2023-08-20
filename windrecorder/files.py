import os

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
  
  for filename in os.listdir(dir):
    if search_str in filename:
      return True
      
  return False