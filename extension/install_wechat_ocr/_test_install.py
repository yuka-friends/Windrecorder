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
    support_ocr_lst = config.support_ocr_lst
    if "WeChatOCR" not in support_ocr_lst:
        support_ocr_lst.append("WeChatOCR")
        config.set_and_save_config("support_ocr_lst", support_ocr_lst)


try:
    # TEST

    from windrecorder import ocr_manager

    res = ocr_manager.ocr_benchmark(print_process=True)
    print()
    ocr_manager.format_print_benchmark(res)
    print()

    print("Install succeed! 安装成功！")
    set_config_module_install(True)


except Exception as e:
    print(f"Install failed. 安装失败: {e}")
    set_config_module_install(False)
