# Set workspace to Windrecorder dir
import datetime
import os
import subprocess
import sys
from os import getpid

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder import file_utils, utils  # noqa: E402
from windrecorder.config import config  # noqa: E402
from windrecorder.exceptions import LockExistsException  # noqa: E402
from windrecorder.lock import FileLock  # noqa: E402

if config.img_embed_module_install:
    try:
        from windrecorder import img_embed_manager
    except ModuleNotFoundError:
        config.set_and_save_config("img_embed_module_install", False)
        print("Img Embedding Module seems not installed, please install first.")
        sys.exit()
else:
    print("Img Embedding Module seems not installed, please install first.")
    sys.exit()

subprocess.run("title Embedding Img for existing video files", shell=True)

videos_filepath = file_utils.get_file_path_list(config.record_videos_dir)
videos_filepath_filter = [item for item in videos_filepath if "-IMGEMB" not in item]
videos_filepath_filter_num = len(videos_filepath_filter)

per_video_embedding_time = (
    datetime.timedelta(minutes=2) * config.record_seconds / 900
)  # 在使用 cuda 的情况下，每 900s 视频需要 2 分钟完成索引。其中拆 iframe 占了大部分时间
eta_process_all_video = videos_filepath_filter_num * per_video_embedding_time


def main():
    while True:
        subprocess.run("cls", shell=True)
        if img_embed_manager.is_cuda_available:
            print("√ Your device support CUDA acceleration.")
        else:
            print("X Your device seems not support CUDA acceleration, embedding performance might be slow.")

        text_intro = f"""

本脚本可以将你未进行图像嵌入索引的历史视频进行索引。索引完成后，你可以使用自然语言描述来查找对应图像画面。
This script can index your no image embedding historical videos. After indexed, you can use natural language descriptions to find corresponding images in video files.

--------------------------------------------------------------------

约有 {videos_filepath_filter_num} 个视频未图像嵌入索引，索引所有视频预估用时：{utils.convert_seconds_to_hhmmss(eta_process_all_video.seconds)}

- 若要索引全部视频文件，请输入 Y 后回车确认。
- 若只想先索引部分视频，请输入数字后回车确认（应小于 {videos_filepath_filter_num} ）。每个视频的索引用时预估{utils.convert_seconds_to_hhmmss(per_video_embedding_time.seconds)}，同时将会从最新的视频开始、向旧视频进行索引。

提示: 索引过程中，可以随时关闭终端窗口来中止索引。别担心，已索引的进度都会被保存，下次会继续进度。

There are approximately {videos_filepath_filter_num} videos without image embedding index. Estimated time to index all videos: {utils.convert_seconds_to_hhmmss(eta_process_all_video.seconds)}

- To index all video files, please enter Y and press Enter to confirm.
- If you only want to index some videos first, please enter the number and press Enter to confirm (should be less than {videos_filepath_filter_num}). The indexing time of each video is estimated {utils.convert_seconds_to_hhmmss(per_video_embedding_time.seconds)}, and indexing will start from the latest video to the old video.

Tip: During the indexing process, you can close the terminal window at any time to abort the indexing. Don't worry, all indexed progress will be saved and progress will continue next time.

        """
        print(text_intro)
        user_input = input("> ")
        if user_input.lower() == "y":
            img_embed_manager.all_videofile_do_img_embedding_routine(video_queue_count=videos_filepath_filter_num)
            break
        try:
            val = int(user_input)
            if 0 < val < videos_filepath_filter_num:
                img_embed_manager.all_videofile_do_img_embedding_routine(video_queue_count=val)
                break
        except ValueError:
            pass

    subprocess.run("cls", shell=True)
    print("指定的选项下视频已索引完成，你可以在 webui 使用自然语言描述来查找对应图像画面。")


while True:
    try:
        img_emb_lock = FileLock(config.img_emb_lock_path, str(getpid()), timeout_s=None)
        break
    except LockExistsException:
        with open(config.img_emb_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())

        tray_is_running = utils.is_process_running(check_pid, compare_process_name="python.exe")
        if tray_is_running:
            subprocess.run("cls", shell=True)
            print(
                "Warring: Seems another img embedding indexing process is running.\n If not, please try to delete cache/lock/LOCK_FILE_IMG_EMB.MD and try again.\n"
            )
            print(f"PID: {check_pid}")
            sys.exit()
        else:
            try:
                os.remove(config.img_emb_lock_path)
            except FileNotFoundError:
                pass

with img_emb_lock:
    main()
