# Set workspace to Windrecorder dir
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402


def set_config_module_uninstall():
    support_ocr_lst = config.support_ocr_lst
    if "PaddleOCR" in support_ocr_lst:
        support_ocr_lst.remove("PaddleOCR")
        config.set_and_save_config("support_ocr_lst", support_ocr_lst)


try:
    set_config_module_uninstall()
    print("Uninstall success. 卸载成功")

except Exception as e:
    print(f"Uninstall failed. 卸载失败: {e}")
