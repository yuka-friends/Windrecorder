import subprocess
import datetime
import time
import os
from os import getpid
import json
import asyncio
import windrecorder.maintainManager as maintainManager

import windrecorder.utils as utils
from windrecorder.config import config

ffmpeg_path = 'ffmpeg'
video_path = config.record_videos_dir


# 索引文件线程
async def index_video_data(vid_file_name):
    print("---\n---Indexing OCR data\n---")
    full_path = os.path.join(video_path,vid_file_name)
    if os.path.exists(full_path):
        print(f"--{full_path} existed.")
        maintainManager.ocr_process_single_video(video_path, vid_file_name, "i_frames")


# 录制屏幕线程
async def record_screen(
        output_dir=config.record_videos_dir,
        target_res=config.target_screen_res,
        record_time=config.record_seconds
):
    """
    用ffmpeg持续录制屏幕,每15分钟保存一个视频文件
    """
    while True:
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
        except subprocess.CalledProcessError as ex:
            print(f"{ex.cmd} failed with return code {ex.returncode}")

        print("--Recorded. Prepare to indexing OCR data.")
        time.sleep(2)

        # 是否在录制完毕后索引
        if config.OCR_index_strategy == 1:
            print(f"-asyncio.create_task(index_video_data({video_out_name}))")
            asyncio.create_task(index_video_data(video_out_name))
            
        # 2 秒后继续
        time.sleep(2)



# 测试ffmpeg是否存在可用
def test_ffmpeg():
    try:
        res = subprocess.run('ffmpeg -version')
    except Exception:
        print('Error: ffmpeg is not installed! Please ensure ffmpeg is in the PATH')
        exit(1)



if __name__ == '__main__':
    test_ffmpeg()
    print(f"-config.OCR_index_strategy: {config.OCR_index_strategy}")

    asyncio.run(record_screen())

