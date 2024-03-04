# 本脚本用于在用户升级后，清理更改早期版本的旧设定
import os
import shutil

from windrecorder import file_utils, utils
from windrecorder.config import config


def main():
    # - 0.0.9 更新操作
    print("- 0.0.9")
    # 调整目录，移除数据库错误表示法
    config.set_and_save_config("db_path", "db")
    config.set_and_save_config("vdb_img_path", "db_imgemb")
    # 将所有之前的用户数据移动到 userdata 下
    file_utils.ensure_dir(config.userdata_dir)

    if os.path.exists("userdata\\db"):
        if file_utils.get_dir_size("userdata\\db") < 1024 * 1024:
            shutil.rmtree("userdata\\db")

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
            print(f"moving {filepath}")
            shutil.move(filepath, config.userdata_dir)
    if os.path.exists("config\\config_user.json"):
        shutil.move("config\\config_user.json", config.userdata_dir)
    if os.path.exists("config"):
        shutil.rmtree("config")

    # - 0.0.5 更新操作
    # 如果原先用户开机启动中存在 start_record.bat，替换创建为新的 start_app.bat
    print("- 0.0.5")
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
