import os
import subprocess
import sys
from os import getpid

from windrecorder import img_embed_manager, record, utils, win_ui
from windrecorder.config import config  # NOQA: E402
from windrecorder.exceptions import LockExistsException  # NOQA: E402
from windrecorder.lock import FileLock  # NOQA: E402


def convert_process():
    print("\n正在将截图缓存合成为视频...\nCombining screenshot cache into video...")
    record.index_cache_screenshots_dir_process()

    if config.enable_img_embed_search and config.img_embed_module_install:
        print("\n正在将嵌入视频图片向量...\nEmbedding video image vector...")
        img_embed_manager.all_videofile_do_img_embedding_routine(video_queue_batch=1000)

    print("\n清理已转换的缓存...\nCleaning converted cache...")
    record.clean_cache_screenshots_dir_process()


def main():
    while True:
        subprocess.run("cls", shell=True)

        text_intro = """

此脚本可以将尚未转换为视频的缓存截图文件转换为视频（适用于 灵活截图模式 下、积攒了许多闲时没来得及被转换为视频的截图缓存时，进行的手动操作）。
This script can convert cached screenshot files that have not yet been converted to videos into videos (applicable to manual operations in Flexible Screenshot Mode when there are many cached screenshots that have not been converted to videos in time).

--------------------------------------------------------------------

- 若要合并全部视频文件，请输入 Y 后回车确认。
- If you want to converted all video files, please enter Y and press Enter to confirm.

        """
        print(text_intro)
        user_input = input("> ")
        if user_input.lower() == "y":
            convert_process()
            break

    # subprocess.run("cls", shell=True)
    print()
    print("已将所有缓存截图转换为了视频。\nAll cached screenshots have been converted to videos.\n")


def interrupt_start():
    win_ui.show_popup(
        "Windrecorder appears to be running, please close it to continue.", "Windrecorder is already running.", "information"
    )
    sys.exit()


while True:
    try:
        tray_lock = FileLock(config.tray_lock_path, str(getpid()), timeout_s=None)
        break
    except LockExistsException:
        with open(config.tray_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())

        tray_is_running = utils.is_process_running(check_pid, compare_process_name="python.exe")
        if tray_is_running:
            interrupt_start()
        else:
            try:
                os.remove(config.tray_lock_path)
            except FileNotFoundError:
                pass

with tray_lock:
    main()
