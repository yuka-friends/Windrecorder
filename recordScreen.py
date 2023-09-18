import subprocess
import datetime
import time
import threading
# https://steam.oxxostudio.tw/category/python/library/threading.html
import os
from os import getpid
import json

import pyautogui
import numpy as np

import windrecorder.maintainManager as maintainManager
import windrecorder.utils as utils
from windrecorder.config import config
import windrecorder.files as files

ffmpeg_path = 'ffmpeg'
video_path = config.record_videos_dir


# 索引文件
def index_video_data(vid_file_name):
    print("---\n---Indexing OCR data\n---")
    full_path = os.path.join(video_path,vid_file_name)
    if os.path.exists(full_path):
        print(f"--{full_path} existed. Start ocr processing.")
        maintainManager.ocr_process_single_video(video_path, vid_file_name, "i_frames")


# 录制屏幕
def record_screen(
        output_dir=config.record_videos_dir,
        target_res=config.target_screen_res,
        record_time=config.record_seconds
):
    """
    用ffmpeg持续录制屏幕,每15分钟保存一个视频文件
    """
    # 构建输出文件名 
    now = datetime.datetime.now()
    video_out_name = now.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
    out_path = os.path.join(output_dir, video_out_name)

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    screen_width, screen_height = utils.get_screen_resolution()

    ffmpeg_cmd = [
        ffmpeg_path,
        '-f', 'gdigrab',
        '-video_size', f"{screen_width}x{screen_height}",
        '-framerate', '2',
        '-i', 'desktop',
        '-vf', target_res,
        # 默认使用编码成 h264 格式
        '-c:v', 'libx264',
        # 默认码率为 200kbps
        '-b:v', '200k',
        '-bf', '8', '-g', '600', '-sc_threshold', '10',
        '-t', str(record_time), out_path
    ]

    # 执行命令        
    try:
        # 添加服务监测信息
        with open("LOCK_FILE_RECORD.MD", 'w', encoding='utf-8') as f:
            f.write(str(getpid()))
        print("---Start Recording via FFmpeg")
        # 运行ffmpeg
        subprocess.run(ffmpeg_cmd, check=True)
        return video_out_name
    except subprocess.CalledProcessError as ex:
        print(f"{ex.cmd} failed with return code {ex.returncode}")


# 测试ffmpeg是否存在可用
def test_ffmpeg():
    try:
        res = subprocess.run('ffmpeg -version')
    except Exception:
        print('Error: ffmpeg is not installed! Please ensure ffmpeg is in the PATH')
        exit(1)


monitor_change_rank = 0
last_screenshot_array = None
# 每隔一段截图对比是否屏幕内容缺少变化
def monitor_compare_screenshot():
    global monitor_change_rank
    global last_screenshot_array
    similarity = None

    while(True):
        screenshot = pyautogui.screenshot()
        screenshot_array = np.array(screenshot)

        if last_screenshot_array is not None:
            similarity = maintainManager.compare_image_similarity_np(last_screenshot_array,screenshot_array)

            if similarity > 0.93:
                monitor_change_rank += 0.5
            else:
                monitor_change_rank = 0

        last_screenshot_array = screenshot_array.copy()
        print(f"----monitor_change_rank:{monitor_change_rank},similarity:{similarity}")
        time.sleep(30)



if __name__ == '__main__':
    test_ffmpeg()
    print(f"-config.OCR_index_strategy: {config.OCR_index_strategy}")
    # 维护之前退出没留下的视频
    thread_maintain_last_time = threading.Thread(target=maintainManager.maintain_manager_main)
    thread_maintain_last_time.start()

    # 屏幕内容多长时间不变则暂停录制
    print(f"-config.screentime_not_change_to_pause_record:{config.screentime_not_change_to_pause_record}")
    if config.screentime_not_change_to_pause_record >0:
        thread_monitor_compare_screenshot = threading.Thread(target=monitor_compare_screenshot)
        thread_monitor_compare_screenshot.start()
    else:
        monitor_change_rank = -1


    while(True):
        # 主循环过程
        if monitor_change_rank > config.screentime_not_change_to_pause_record:
            print("屏幕内容没有更新，停止录屏中。进入闲时维护")
            time.sleep(10)
        else:
            video_out_name = record_screen() # 录制屏幕
            time.sleep(2) # 歇口气
            # 自动索引策略
            if config.OCR_index_strategy == 1:
                print(f"-Starting Indexing video data: '{video_out_name}'")
                thread_index_video_data = threading.Thread(target=index_video_data,args=(video_out_name,))
                thread_index_video_data.daemon = True  # 设置为守护线程
                thread_index_video_data.start()
            time.sleep(2) # 再歇
        
