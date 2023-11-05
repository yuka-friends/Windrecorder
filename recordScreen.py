import ctypes
import datetime

# https://steam.oxxostudio.tw/category/python/library/threading.html
import os
import subprocess
import threading
import time
from os import getpid

import numpy as np
import pyautogui

import windrecorder.maintainManager as maintainManager
import windrecorder.record as record
import windrecorder.utils as utils
import windrecorder.wordcloud as wordcloud
from windrecorder import file_utils
from windrecorder.config import config

if config.release_ver:
    ffmpeg_path = "env\\ffmpeg.exe"
else:
    ffmpeg_path = "ffmpeg"
video_path = config.record_videos_dir
user32 = ctypes.windll.User32

# 全局状态变量
monitor_change_rank = 0
last_screenshot_array = None
idle_maintain_time_gap = datetime.timedelta(hours=8)  # 与上次闲时维护至少相隔
lock_idle_maintaining = False  # 维护中的锁

last_idle_maintain_time = datetime.datetime.now()

try:
    # 读取之前闲时维护的时间
    with open(config.last_idle_maintain_file_path, "r", encoding="utf-8") as f:
        time_read = f.read()
        last_idle_maintain_time = datetime.datetime.strptime(time_read, "%Y-%m-%d_%H-%M-%S")
except FileNotFoundError:
    file_utils.check_and_create_folder("cache")
    with open(config.last_idle_maintain_file_path, "w", encoding="utf-8") as f:
        f.write(last_idle_maintain_time.strftime("%Y-%m-%d_%H-%M-%S"))


# 判断是否已锁屏
def is_screen_locked():
    return user32.GetForegroundWindow() == 0


# 判断是否正在休眠
def is_system_awake():
    try:
        return user32.GetLastInputInfo() == 0
    except Exception:
        return True


# 录制完成后索引单个刚录制好的视频文件
def index_video_data(video_saved_dir, vid_file_name):
    print("- Windrecorder -\n---Indexing OCR data\n---")
    if not utils.is_maintain_lock_file_valid():
        full_path = os.path.join(video_saved_dir, vid_file_name)
        if os.path.exists(full_path):
            print(f"--{full_path} existed. Start ocr processing.")
            # 添加维护标识
            utils.add_maintain_lock_file("make")

            maintainManager.ocr_process_single_video(video_saved_dir, vid_file_name, "cache\\i_frames")

            # 移除维护标识
            utils.add_maintain_lock_file("del")


# 录制屏幕
def record_screen(
    output_dir=config.record_videos_dir,
    target_res=config.target_screen_res,
    record_time=config.record_seconds,
):
    """
    用ffmpeg持续录制屏幕,每15分钟保存一个视频文件
    """
    # 构建输出文件名
    now = datetime.datetime.now()
    video_out_name = now.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
    output_dir_with_date = now.strftime("%Y-%m")  # 将视频存储在日期月份子目录下
    video_saved_dir = os.path.join(output_dir, output_dir_with_date)
    file_utils.check_and_create_folder(video_saved_dir)
    out_path = os.path.join(video_saved_dir, video_out_name)

    file_utils.check_and_create_folder(output_dir)

    # 获取屏幕分辨率并根据策略决定缩放
    screen_width, screen_height = utils.get_screen_resolution()
    target_scale_width, target_scale_height = record.get_scale_screen_res_strategy(
        origin_width=screen_width, origin_height=screen_height
    )
    print(f"Origin screen resolution: {screen_width}x{screen_height}, Resized to {target_scale_width}x{target_scale_height}.")

    ffmpeg_cmd = [
        ffmpeg_path,
        "-f",
        "gdigrab",
        "-video_size",
        f"{screen_width}x{screen_height}",
        "-framerate",
        "2",
        "-i",
        "desktop",
        "-vf",
        f"scale={target_scale_width}:{target_scale_height}",
        # 默认使用编码成 h264 格式
        "-c:v",
        "libx264",
        # 默认码率为 200kbps
        "-b:v",
        "200k",
        "-bf",
        "8",
        "-g",
        "600",
        "-sc_threshold",
        "10",
        "-t",
        str(record_time),
        out_path,
    ]

    # 执行命令
    try:
        # 添加服务监测信息
        file_utils.check_and_create_folder("cache")
        with open(config.record_lock_path, "w", encoding="utf-8") as f:
            f.write(str(getpid()))
        print("Windrecorder: Start Recording via FFmpeg")
        # 运行ffmpeg
        subprocess.run(ffmpeg_cmd, check=True)
        return video_saved_dir, video_out_name
    except subprocess.CalledProcessError as ex:
        print(f"Windrecorder: {ex.cmd} failed with return code {ex.returncode}")
        return video_saved_dir, video_out_name


# 持续录制屏幕的主要线程
def continuously_record_screen(screentime_detect_stop_event):
    global last_idle_maintain_time

    while not continuously_stop_event.is_set():
        # 主循环过程
        if monitor_change_rank > config.screentime_not_change_to_pause_record:
            print("Windrecorder: Screen content not updated, stop recording.")
            subprocess.run("color 60", shell=True)  # 设定背景色为不活动

            # 算算是否该进入维护了（与上次维护时间相比）
            timegap_between_last_idle_maintain = datetime.datetime.now() - last_idle_maintain_time
            if timegap_between_last_idle_maintain > idle_maintain_time_gap and not lock_idle_maintaining:  # 超时且无锁情况下
                print(
                    f"Windrecorder: It is separated by {timegap_between_last_idle_maintain} from the last maintenance, enter idle maintenance."
                )
                thread_idle_maintain = threading.Thread(target=idle_maintain_process)
                thread_idle_maintain.daemon = True  # 设置为守护线程
                thread_idle_maintain.start()

                # 更新维护时间
                last_idle_maintain_time = datetime.datetime.now()  # 本次闲时维护时间
                with open(config.last_idle_maintain_file_path, "w", encoding="utf-8") as f:
                    f.write(str(last_idle_maintain_time.strftime("%Y-%m-%d_%H-%M-%S")))

            time.sleep(10)
        else:
            subprocess.run("color 2f", shell=True)  # 设定背景色为活动
            video_saved_dir, video_out_name = record_screen()  # 录制屏幕
            screentime_detect_stop_event.wait(2)

            # 自动索引策略
            if config.OCR_index_strategy == 1:
                print(f"Windrecorder: Starting Indexing video data: '{video_out_name}'")
                thread_index_video_data = threading.Thread(
                    target=index_video_data,
                    args=(
                        video_saved_dir,
                        video_out_name,
                    ),
                )
                thread_index_video_data.daemon = True  # 设置为守护线程
                thread_index_video_data.start()

            screentime_detect_stop_event.wait(2)


# 闲时维护的操作流程
def idle_maintain_process():
    global lock_idle_maintaining
    lock_idle_maintaining = True
    # 维护之前退出没留下的视频
    if not utils.is_maintain_lock_file_valid():
        thread_maintain_last_time = threading.Thread(target=maintainManager.maintain_manager_main)
        thread_maintain_last_time.start()
    # 清理过时视频
    maintainManager.remove_outdated_videofiles()
    # 压缩过期视频
    maintainManager.compress_outdated_videofiles()
    # 生成随机词表
    wordcloud.generate_all_word_lexicon_by_month()

    lock_idle_maintaining = False


# 测试ffmpeg是否存在可用
def test_ffmpeg():
    try:
        subprocess.run([ffmpeg_path, "-version"])
    except FileNotFoundError:
        print("Error: ffmpeg is not installed! Please ensure ffmpeg is in the PATH.")
        exit(1)


# 每隔一段截图对比是否屏幕内容缺少变化
def monitor_compare_screenshot(screentime_detect_stop_event):
    while not screentime_detect_stop_event.is_set():
        if is_screen_locked() or not is_system_awake():
            print("Windrecorder: Screen locked / System not awaked")
        else:
            try:
                global monitor_change_rank
                global last_screenshot_array
                similarity = None

                while True:
                    screenshot = pyautogui.screenshot()
                    screenshot_array = np.array(screenshot)

                    if last_screenshot_array is not None:
                        similarity = maintainManager.compare_image_similarity_np(last_screenshot_array, screenshot_array)

                        if similarity > 0.9:  # 对比检测阈值
                            monitor_change_rank += 0.5
                        else:
                            monitor_change_rank = 0

                    last_screenshot_array = screenshot_array.copy()
                    print(f"Windrecorder: monitor_change_rank:{monitor_change_rank}, similarity:{similarity}")
                    time.sleep(30)
            except Exception as e:
                print("Windrecorder: Error occurred:", str(e))
                if "batchDistance" in str(e):  # 如果是抓不到画面导致出错，可以认为是进入了休眠等情况
                    monitor_change_rank += 0.5
                else:
                    monitor_change_rank = 0

        screentime_detect_stop_event.wait(5)


if __name__ == "__main__":
    subprocess.run("color 60", shell=True)  # 设定背景色为不活动

    if record.is_recording():
        print("Windrecorder: Another screen record service is running.")
        exit(1)

    test_ffmpeg()
    print(f"Windrecorder: config.OCR_index_strategy: {config.OCR_index_strategy}")

    # 维护之前退出没留下的视频
    if not utils.is_maintain_lock_file_valid():
        thread_maintain_last_time = threading.Thread(target=maintainManager.maintain_manager_main)
        thread_maintain_last_time.start()

    # 屏幕内容多长时间不变则暂停录制
    print(f"Windrecorder: config.screentime_not_change_to_pause_record: {config.screentime_not_change_to_pause_record}")
    screentime_detect_stop_event = threading.Event()  # 使用事件对象来检测检测函数是否意外被终止
    if config.screentime_not_change_to_pause_record > 0:  # 是否使用屏幕不变检测
        thread_monitor_compare_screenshot = threading.Thread(
            target=monitor_compare_screenshot, args=(screentime_detect_stop_event,)
        )
        thread_monitor_compare_screenshot.start()
    else:
        monitor_change_rank = -1

    # 录屏的线程
    continuously_stop_event = threading.Event()
    thread_continuously_record_screen = threading.Thread(
        target=continuously_record_screen, args=(screentime_detect_stop_event,)
    )
    thread_continuously_record_screen.start()

    while True:
        # # 主循环过程
        # if monitor_change_rank > config.screentime_not_change_to_pause_record:
        #     print("屏幕内容没有更新，停止录屏中。进入闲时维护")
        #     time.sleep(10)
        # else:
        #     video_saved_dir, video_out_name = record_screen() # 录制屏幕
        #     time.sleep(2) # 歇口气
        #     # 自动索引策略
        #     if config.OCR_index_strategy == 1:
        #         print(f"-Starting Indexing video data: '{video_out_name}'")
        #         thread_index_video_data = threading.Thread(target=index_video_data,args=(video_saved_dir,video_out_name,))
        #         thread_index_video_data.daemon = True  # 设置为守护线程
        #         thread_index_video_data.start()
        #     time.sleep(2) # 再歇

        # 如果屏幕重复画面检测线程意外出错，重启它
        if not thread_monitor_compare_screenshot.is_alive() and config.screentime_not_change_to_pause_record > 0:
            thread_monitor_compare_screenshot = threading.Thread(
                target=monitor_compare_screenshot, args=(screentime_detect_stop_event,)
            )
            thread_monitor_compare_screenshot.start()

        # 如果屏幕录制线程意外出错，重启它
        if not thread_continuously_record_screen.is_alive():
            thread_continuously_record_screen = threading.Thread(
                target=continuously_record_screen, args=(screentime_detect_stop_event,)
            )
            thread_continuously_record_screen.start()

        time.sleep(30)
