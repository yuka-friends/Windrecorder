# Set workspace to Windrecorder dir
import os
import subprocess
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(parent_parent_dir)
os.chdir("..")
os.chdir("..")

from windrecorder.config import config  # noqa: E402

str_guide = """
  This guide will config Tesseract OCR as the optical text recognition engine for Wind
  Third-party OCR engines may consume more system resources when recognizing.

  本向导将为捕风记录仪配置 Tesseract OCR 作为光学文本识别引擎。
  第三方 OCR 引擎运行时可能会占用更高系统资源。

  First of all, please install Tesseract OCR and the required language packs according
  首先，请先根据目录下 README.MD 的操作指引，安装 Tesseract OCR 与所需语言包。

  After the installation is completed, please paste the installation directory (such a
  安装完成后，请将安装目录（如 C:\\Program Files\\Tesseract-OCR）粘贴至此，回车提交即可

  ================================================================================
"""
while True:
    subprocess.run("cls", shell=True)
    print(str_guide)
    input_path = input("> ")
    input_path_full = os.path.join(input_path, "tesseract.exe")
    if os.path.exists(input_path_full):
        config.set_and_save_config("TesseractOCR_filepath", input_path_full)
        break
    else:
        print("tesseract.exe not found under filepath. 给定目录下没有发现 tesseract.exe.")
        subprocess.run("pause", shell=True)


def set_config_module_install(state: bool):
    support_ocr_lst = config.support_ocr_lst
    if "TesseractOCR" not in support_ocr_lst:
        support_ocr_lst.append("TesseractOCR")
        config.set_and_save_config("support_ocr_lst", support_ocr_lst)


try:
    from windrecorder import ocr_manager

    img_path = parent_parent_dir + "/__assets__/OCR_test_1080_zh-Hans-CN.png"
    ocr_manager.ocr_image_TesseractOCR(img_path)

    print("Install succeed! 安装成功！")
    set_config_module_install(True)

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
    set_config_module_install(False)
