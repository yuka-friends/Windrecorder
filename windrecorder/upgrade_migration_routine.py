# 本脚本用于在用户升级后，清理更改早期版本的旧设定
import os
import shutil

from windrecorder import file_utils, utils
from windrecorder.config import config


def main():
    # - 0.0.5 更新操作
    # 如果原先用户开机启动中存在 start_record.bat，替换创建为新的 start_app.bat
    print("- 0.0.5 update routine")
    startup_folder = os.path.join(
        os.getenv("APPDATA"),
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
    )
    if utils.is_file_already_in_startup("start_record.bat.lnk"):
        os.remove(os.path.join(startup_folder, "start_record.bat.lnk"))
        utils.change_startup_shortcut(is_create=True)
        print("recreated 'start_record.bat.lnk' in Startup.")

    # - 0.0.9 更新操作
    print("- 0.0.9 update routine")
    # 调整目录，移除数据库错误表示法
    config.set_and_save_config("db_path", "db")
    config.set_and_save_config("vdb_img_path", "db_imgemb")
    # 将所有之前的用户数据移动到 userdata 下
    file_utils.ensure_dir(config.userdata_dir)

    move_filepath_list = [
        "videos",
        "db",
        "db_imgemb",
        "result_lightbox",
        "result_timeline",
        "result_wintitle",
        "result_wordcloud",
    ]

    for filepath in move_filepath_list:
        if os.path.exists(filepath):
            if os.path.exists(os.path.join(config.userdata_dir, filepath)):
                print(f"Preserving both legacy and current {filepath}; destination already exists.")
                continue
            print(f"moving {filepath}")
            shutil.move(filepath, config.userdata_dir)
    if os.path.exists("config\\config_user.json") and not os.path.exists(
        os.path.join(config.userdata_dir, "config_user.json")
    ):
        print("migrate user config")
        shutil.move("config\\config_user.json", config.userdata_dir)
    # Keep remaining legacy files: they may contain user customizations.

    # - 0.0.12 更新操作
    print("- 0.0.12 update routine")
    # 为所有 -ERROR 视频文件添加重试次数标签
    for root, dirs, files in os.walk(config.record_videos_dir_ud):
        for file in files:
            if "-ERROR." in file:
                src = os.path.join(root, file)
                dst = src.replace("-ERROR.", "-ERROR1.")
                try:
                    os.rename(src, dst)
                    print(f"renamed {src} to {dst}")
                except (FileNotFoundError, PermissionError, OSError) as error:
                    print(f"Error occurred while trying to rename file {src}: ", error)
