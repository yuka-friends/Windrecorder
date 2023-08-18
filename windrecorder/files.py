import os

# 将数据库的视频名加上-OCRED标志，使之能正常读取到
def add_OCRED_suffix(video_name):
    vidname = os.path.splitext(video_name)[0] + "-OCRED" + os.path.splitext(video_name)[1]
    return vidname


def get_videos_and_ocred_videos_count(folder_path):
    count = 0
    nocred_count = 0
    for filename in os.listdir(folder_path):
        count += 1
        if not filename.split('.')[0].endswith("-OCRED"):
            nocred_count += 1
    return count, nocred_count