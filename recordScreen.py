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


async def index_video_data():
    maintainManager.maintain_manager_main() # 更新数据库



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
        out_name = now.strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
        out_path = os.path.join(output_dir, out_name)

        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        screen_width, screen_height = utils.get_screen_resolution()

        # ffmpeg_cmd = [ffmpeg_path, '-f', 'gdigrab', '-video_size', '3840x2160',
        #       '-framerate', '1', '-i', 'desktop', 
        #       '-vf', 'scale=1920:1080', 
        #       '-c:v', 'libx265', '-b:v', '300k', '-minrate', '100k', '-bufsize', '800k',
        #       '-bf','7','-g', '300','-keyint_min', '120',
        #       '-t', str(gap_time), out_path]

        ffmpeg_cmd = [
            ffmpeg_path,
            '-f', 'gdigrab',
            '-video_size', f"{screen_width}x{screen_height}",
            '-framerate', '2',
            '-i', 'desktop',
            '-vf', target_res,
            # 默认使用编码成 h254 格式
            '-c:v', 'libx264',
            # 默认码率为 200kbps
            '-b:v', '200k',
            '-bf', '8', '-g', '600', '-sc_threshold', '10',
            '-t', str(record_time), out_path
        ]

        # 执行命令        
        try:
            # 添加服务监测信息
            with open("lock_file_record", 'w', encoding='utf-8') as f:
                f.write(str(getpid()))

            subprocess.run(ffmpeg_cmd, check=True)
        except subprocess.CalledProcessError as ex:
            print(f"{ex.cmd} failed with return code {ex.returncode}")

        time.sleep(2)

        # 是否在录制完毕后索引
        if config.OCR_index_strategy == 1:
            asyncio.create_task(index_video_data())
            
        # 2 秒后继续
        time.sleep(2)



def test_ffmpeg():
    try:
        res = subprocess.run('ffmpeg -version')
    except Exception:
        print('Error: ffmpeg is not installed! Please ensure ffmpeg is in the PATH')
        exit(1)


if __name__ == '__main__':
    test_ffmpeg()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(record_screen())
    finally:
        loop.close()
