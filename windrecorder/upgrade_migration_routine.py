# 本脚本用于在用户升级后，清理早期版本的旧设定
import os

import windrecorder.utils as utils


def main():
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
