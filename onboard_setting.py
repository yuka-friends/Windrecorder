import getpass
import os
import subprocess
import sys
import time

from windrecorder import utils
from windrecorder.config import config

# ------------------------------------------------------------------


def check_is_running():
    if os.path.exists(config.tray_lock_path):
        with open(config.tray_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())

        tray_is_running = utils.is_process_running(check_pid, compare_process_name="python.exe")
        if tray_is_running:
            subprocess.run("cls", shell=True)
            print("Windrecorder seems to be running, please try to close it and retry.")
            print("捕风记录仪似乎正在运行，请尝试关闭后重试。")
            print()
            print(f"PID: {check_pid}")
            sys.exit()
        else:
            try:
                os.remove(config.tray_lock_path)
            except FileNotFoundError:
                pass


check_is_running()

# ------------------------------------------------------------------

import windrecorder.upgrade_migration_routine as upgrade_migration_routine  # NOQA: E402

# 清理早期版本的旧设定。需要在多余包被 import 进来被占用文件前处理。
try:
    upgrade_migration_routine.main()
except Exception as e:
    print(e)
    subprocess.run("pause", shell=True)

# ------------------------------------------------------------------

print("Loading onboard setting, please stand by...")

from windrecorder import file_utils, ocr_manager  # NOQA: E402
from windrecorder.utils import get_text as _t  # NOQA: E402

# 全部向导的步骤数
ALLSTEPS = 6
subprocess.run("color 06", shell=True)

# 清理缓存
if os.path.exists("cache"):
    try:
        file_utils.empty_directory("cache")
    except PermissionError:
        pass


# 画分割线的
def divider():
    print("\n--------------------------------------------------------------------\n")


# 画抬头的
def print_header(step=1, toast=""):
    subprocess.run("cls", shell=True)
    print("Weclome to Windrecorder | 欢迎使用捕风记录仪\n")
    print("Thanks for downloading! This Quick Wizard will help you set it up. \n感谢下载使用！本向导将协助你完成基础配置项。不用担心，所有选项之后都可以再次调整。")
    divider()
    print(step, "/", ALLSTEPS, toast)
    print("\n")


# 配置文件已有选项的指示器
def config_indicator(config_element, expect_result):
    if config_element == expect_result:
        return "   ← "
    else:
        return ""


# ========================================================


# 设置语言
def set_lang():
    while True:
        print_header(step=1)
        print("First, please choose your interface language. (Enter the number option and press Enter to confirm.)")
        print("首先，请设置你的界面语言。（输入数字项后回车确认）")
        divider()
        print(
            f"""
            1. English {config_indicator(config.lang,"en")}
            2. 简体中文 {config_indicator(config.lang,"sc")}
            3. 日本語 {config_indicator(config.lang,"ja")}
            """
        )
        input_lang_num = input("> ")

        if input_lang_num == "1":
            config.set_and_save_config("lang", "en")
            print("The interface language is set to English")
            break
        if input_lang_num == "2":
            config.set_and_save_config("lang", "sc")
            print("界面语言已设定为：简体中文")
            break
        if input_lang_num == "3":
            config.set_and_save_config("lang", "ja")
            print("インターフェース言語は日本語に設定されています。")
            break
        else:
            print(_t("qs_la_text_same_as_previous"))
            break


# 设置用户名
def set_username():
    while True:
        print_header(step=2)
        if config.user_name == "default":
            sys_username = getpass.getuser()  # 如果为默认用户名，获取当前系统的用户名
        else:
            sys_username = config.user_name  # 如果配置文件已有自定义用户名，读取之前的用户名
            print(_t("qs_un_use_current_name").format(sys_username=sys_username))
            break  # 如果已设定用户名，此项设置跳过以避免误操作

        print(_t("qs_un_set_your_username"))
        print(_t("qs_un_describe").format(sys_username=sys_username))
        divider()

        your_username = input("> ")

        if len(your_username) > 20:
            print(_t("qs_un_longer_than_expect"))
            divider()
            subprocess.run("pause", shell=True)
        elif len(your_username) == 0:
            print(_t("qs_un_use_current_name").format(sys_username=sys_username))
            config.set_and_save_config("user_name", sys_username)
            break
        else:
            print(_t("qs_un_use_custom_name").format(your_username=your_username))
            config.set_and_save_config("user_name", your_username)
            break


# 选择可ocr的语言
def set_ocr_lang():
    os_support_lang = utils.get_os_support_lang()

    if len(os_support_lang) > 1:  # 如果系统安装了超过一种语言
        while True:
            print_header(step=3)
            print(_t("qs_olang_intro"))
            utils.print_numbered_list(os_support_lang)
            divider()

            try:
                input_ocr_lang_num = int(input("> "))

                if 0 < input_ocr_lang_num <= len(os_support_lang):
                    config.set_and_save_config("ocr_lang", os_support_lang[input_ocr_lang_num - 1])
                    print(
                        _t("qs_olang_ocrlang_set_to"),
                        os_support_lang[input_ocr_lang_num - 1],
                    )
                    break

            except ValueError:
                print(_t("qs_olang_error"))
                subprocess.run("pause", shell=True)

    else:  # 如果系统只安装了一种语言，自动选择
        print_header(step=3)
        print(_t("qs_olang_one_choice_default_set").format(os_support_lang=os_support_lang[0]))
        config.set_and_save_config("ocr_lang", os_support_lang[0])


# 测试与设置 ocr 引擎
def set_ocr_engine():
    test_img_filepath = "__assets__\\OCR_test_1080_" + config.ocr_lang + ".png"  # 读取测试图像
    if not os.path.exists(test_img_filepath):
        test_img_filepath = "OCR_test_1080_en-US.png"  # fallback 读取为英文图像

    with open("__assets__\\OCR_test_1080_words_" + config.ocr_lang + ".txt", encoding="utf-8") as f:  # 读取比对参考文本
        ocr_text_refer = f.read()
        ocr_text_refer = utils.wrap_text_by_remove_break(ocr_text_refer)

    # 测试COL - 已废弃
    # try:
    #     time_cost_col = time.time()
    #     ocr_result_col = ocr_manager.ocr_image_col(test_img_filepath)
    #     time_cost_col = time.time() - time_cost_col
    #     ocr_result_col = utils.wrap_text_by_remove_break(ocr_result_col)
    #     _, ocr_correct_col = ocr_manager.compare_strings(ocr_result_col, ocr_text_refer)

    # except Exception as e:
    #     ocr_result_col = ""
    #     print(e)

    # 测试ms ocr
    time_cost_ms = time.time()
    ocr_result_ms = ocr_manager.ocr_image_ms(test_img_filepath)
    time_cost_ms = time.time() - time_cost_ms
    ocr_result_ms = utils.wrap_text_by_remove_break(ocr_result_ms)
    _, ocr_correct_ms = ocr_manager.compare_strings(ocr_result_ms, ocr_text_refer)

    while True:
        print_header(step=3)
        print(_t("qs_ocr_title"))

        if ocr_result_ms:
            print("- Windows.Media.Ocr.Cli   OCR languages: ", config.ocr_lang)
            print(
                _t("qs_ocr_result_describe").format(
                    accuracy=ocr_correct_ms,
                    timecost=time_cost_ms,
                    timecost_15=utils.convert_seconds_to_hhmmss(int(time_cost_ms * 350)),
                )
            )
            if ocr_correct_ms < 50:
                print(_t("qs_ocr_tips_low_accuracy"))

        break


def set_display():
    # 设置显示器录制选项
    display_count = utils.get_display_count()
    display_info = utils.get_display_info()
    display_info_formatted = utils.get_display_info_formatted()

    if display_count > 1:
        while True:
            print_header(step=4)
            print(_t("qs_mo_describe_all"))
            print(
                f"""
            1. {_t('qs_mo_option_all')} {config_indicator(config.multi_display_record_strategy,"all")}
            2. {_t('qs_mo_option_single')}  {config_indicator(config.multi_display_record_strategy,"single")}
            """
            )
            divider()

            record_strategy_num = input("> ")
            if record_strategy_num == "1":
                config.set_and_save_config("multi_display_record_strategy", "all")
                print(f"{_t('qs_mo_set_to')} {_t('qs_mo_option_all')}")
                break
            elif record_strategy_num == "2":
                config.set_and_save_config("multi_display_record_strategy", "single")
                break
            else:
                print("")

        while True:
            if record_strategy_num == "2":
                print_header(step=4)
                print(f"{_t('qs_mo_set_to')} {_t('qs_mo_describe_single')}")
                print(_t("qs_mo_choose_one_display"))
                utils.print_numbered_list(display_info_formatted)
                divider()

                try:
                    display_index = int(input("> "))
                    if 0 < display_index <= display_count:
                        config.set_and_save_config("record_single_display_index", display_index)
                        print(f"{_t('qs_mo_record_single')} {display_info_formatted[display_index-1]}")
                        break
                    else:
                        print(_t("qs_olang_error"))
                        subprocess.run("pause", shell=True)

                except ValueError:
                    print(_t("qs_olang_error"))
                    subprocess.run("pause", shell=True)
            else:
                break

    else:
        print_header(step=4)
        print(_t("qs_mo_describe_single").format(width=display_info[0]["width"], height=display_info[0]["height"]))
        print(_t("qs_mo_cta"))


def set_extension():
    # 扩展介绍
    while True:
        print_header(step=5)
        print(_t("qs_et_describe"))
        print()
        for key, value in file_utils.get_extension().items():
            print(f"   - {key}")
        break


def finish_setting():
    # 完成初始化设定
    print_header(step=6)
    print(_t("qs_end_describe"))
    print(_t("qs_end_slogan"))
    print(_t("qs_end_feedback"))


# ========================================================


def set_main():
    setting_step_functions = [set_lang, set_username, set_ocr_lang, set_ocr_engine, set_display, set_extension, finish_setting]
    for f in setting_step_functions:
        f()
        divider()
        subprocess.run("pause", shell=True)


if __name__ == "__main__":
    set_main()
