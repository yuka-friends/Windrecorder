# Set workspace to Windrecorder dir
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402


def set_config_module_install():
    support_ocr_lst = config.support_ocr_lst
    if "WeChatOCR" not in support_ocr_lst:
        support_ocr_lst.append("WeChatOCR")
        config.set_and_save_config("support_ocr_lst", support_ocr_lst)


try:
    if not os.path.exists("ocr_lib\\wxocr-binary"):
        print(
            """
   没有找到 ocr_lib\\wxocr-binary 路径，请检查网络连接并重试。或者在 ocr_lib 文件夹下执行指令（git clone https://github.com/Antonoko/wxocr-binary）手动下载。
   The ocr_lib\\wxocr-binary path is not found. Please check the network connection and try again. Or execute the command (git clone https://github.com/Antonoko/wxocr-binary) in the ocr_lib folder to download manually.
"""
        )
        raise Exception("ocr_lib\\wxocr-binary not found.")
    from windrecorder import ocr_manager

    img_path = parent_parent_dir + "/__assets__/OCR_test_1080_zh-Hans-CN.png"
    ocr_manager.ocr_image_wechatocr(img_path, force_initialize=True)

    print("Install succeed! 安装成功！")
    set_config_module_install()

    from windrecorder import ocr_manager

    res = ocr_manager.ocr_benchmark(print_process=True)
    print()
    ocr_manager.format_print_benchmark(res)
    print()

    print(
        "After restarting windrecorder, you can see the option of the third-party OCR engine. After configuration, restart windrecorder to using it."
    )
    print("重启 windrecorder 后即可看到第三方 OCR 引擎选项。配置完成后重启 windrecorder 以应用。")


except Exception as e:
    print(f"Install failed. 安装失败: {e}")
