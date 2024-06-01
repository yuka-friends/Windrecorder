# Set workspace to Windrecorder dir
import os
import re
import subprocess
import sys

from send2trash import send2trash

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402

# ------------------------------------------------------------


def remove_vid_imgemb_tag():
    for root, dirs, files in os.walk(config.record_videos_dir_ud):
        for file in files:
            # 若文件名中包含 "-IMGEMB"，则移除该部分
            if "-IMGEMB" in file:
                new_file = re.sub("-IMGEMB", "", file)
                os.rename(os.path.join(root, file), os.path.join(root, new_file))
                print(f"rename {file} to {new_file}")


while True:
    subprocess.run("cls", shell=True)
    print(
        """
    This wizard is used to roll back and remove the data indexed by the previous image embedding model
    so that the data can be re-indexed by the new model to improve the search quality.

    The script will:
        1. Remove the existing vector database under userdata/db_imgemb;
        2. Remove the video files tag marked as "-IMGEMB-";
    Please rest assured that this operation will not affect the recorded data and OCR database.

    本向导用于回滚移除先前图像嵌入模型所索引的数据，以便由新模型对数据重新嵌入索引，从而提升搜索质量。

    脚本将：
        1. 移除 userdata/db_imgemb 下已有的向量数据库；
        2. 移除标记为“已嵌入索引”的视频文件标签；

    请放心，该操作不会影响已录制的数据和 OCR 数据库。

    Enter Y and press Enter to start the rollback operation.
    输入 Y 后回车以开始回滚操作。

    ================================================================================
    """
    )
    user_input = input("    Please enter the options and press Enter: ")
    if user_input.lower() == "y":
        break


print()
if os.path.exists(config.vdb_img_path_ud):
    print(f"Recycling {config.vdb_img_path_ud}...")
    try:
        send2trash(config.vdb_img_path_ud)
    except FileNotFoundError:
        pass
print(f"Removing video IMGEMB tag at {config.record_videos_dir_ud}...")
remove_vid_imgemb_tag()
