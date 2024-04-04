# Set workspace to Windrecorder dir
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402


def set_config_module_install(state: bool):
    config.set_and_save_config("PaddleOCR_module_install", state)


# 检查是否能启用 cuda
try:
    import paddle

    paddle.utils.run_check()


except Exception as e:
    print(e)
    set_config_module_install(False)
