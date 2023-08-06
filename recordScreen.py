import subprocess
import datetime
import time
import os
from os import getpid
import json
import utils

ffmpeg_path = 'ffmpeg' 

with open('config.json') as f:
    config = json.load(f)
print("config.json:")
print(config)


def record_screen(output_dir=config["record_videos_dir"],screen_res=config["record_screen_res"],target_res=config["target_screen_res"],gap_time=config["record_gap_time"]):
    """
    用ffmpeg持续录制屏幕,每15分钟保存一个视频文件
    """
    
    while True:
        # 构建输出文件名 
        now = datetime.datetime.now()
        out_name = now.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
        out_path = output_dir + "/" + out_name

        if not os.path.exists(output_dir):
           os.mkdir(output_dir)

        # ffmpeg_cmd = [ffmpeg_path, '-f', 'gdigrab', '-video_size', '3840x2160',
        #       '-framerate', '1', '-i', 'desktop', 
        #       '-vf', 'scale=1920:1080', 
        #       '-c:v', 'libx265', '-b:v', '300k', '-minrate', '100k', '-bufsize', '800k',
        #       '-bf','7','-g', '300','-keyint_min', '120',
        #       '-t', str(gap_time), out_path]
        
        ffmpeg_cmd = [ffmpeg_path, '-f', 'gdigrab', '-video_size', screen_res,
              '-framerate', '2', '-i', 'desktop', 
              '-vf', target_res, 
              '-c:v', 'libx264', '-b:v', '200k',
              '-bf','8','-g', '600','-sc_threshold', '10',
              '-t', str(gap_time), out_path]
        
        # 执行命令        
        try:
            # 添加服务监测信息
            with open("lock_file_record", 'w') as f:
                f.write(str(getpid()))

            subprocess.run(ffmpeg_cmd, check=True)
        except subprocess.CalledProcessError as ex:
            print(f"{ex.cmd} failed with return code {ex.returncode}")
        
        # gaptime秒后继续 
        time.sleep(gap_time + 2)


# 使用方法:
# import recordScreen 
# recordScreen.record_screen()

record_screen()