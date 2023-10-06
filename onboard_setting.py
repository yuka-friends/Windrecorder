import subprocess
import json
import time

from windrecorder.config import config
import windrecorder.maintainManager as maintainManager
import windrecorder.utils as utils
import windrecorder.record as record

allstep = 4


# 读取i18n
with open("config\\src\\languages.json", encoding='utf-8') as f:
    d_lang = json.load(f)

def divider():
    print("\n--------------------------------------------------------------------\n")

def print_header(step = 1, toast=""):
    global allstep
    subprocess.run('cls', shell=True)
    print("Weclome to Windrecorder | 欢迎使用捕风记录仪\n")
    print("Thanks for downloading! This Quick Wizard will help you set it up. \n感谢下载使用！本向导将协助你完成基础配置项。")
    divider()
    print(step, "/", allstep, toast)
    print("\n")

# 欢迎寒暄
subprocess.run('color 06', shell=True)



# 设置语言
while(True):
    print_header(step=1)
    print("First, please choose your interface language. (Enter the number option and press Enter to confirm.)")
    print("首先，请设置你的界面语言。（输入数字项后回车确认）")
    divider()
    print("1. English   2. 简体中文")
    input_lang_num = input('> ')

    if input_lang_num == '1':
        config.set_and_save_config('lang', 'en')
        lang = 'en'
        print("The interface language is set to English")
        break
    if input_lang_num == '2':
        config.set_and_save_config('lang', 'zh')
        lang = 'zh'
        print("界面语言已设定为：简体中文")
        break
    else:
        print("Unrecognized input item, please enter the corresponding numerical option and press Enter to confirm.\n无法识别的输入项，请输入对应的数字选项后回车确认。")
        divider()
        subprocess.run('pause', shell=True)

divider()
subprocess.run('pause', shell=True)





# 测试与设置 ocr 引擎
test_img_filepath = "__assets__\OCR_test_1080.png"
with open("__assets__\\OCR_test_1080_words.txt", encoding='utf-8') as f:
    ocr_text_refer = f.read()
    ocr_text_refer = utils.wrap_text_by_remove_break(ocr_text_refer)

# 测试COL
try:
    time_cost_col = time.time()
    ocr_result_col = maintainManager.ocr_image_col(test_img_filepath)
    time_cost_col = time.time() - time_cost_col
    ocr_result_col = utils.wrap_text_by_remove_break(ocr_result_col)
    _, ocr_correct_col = maintainManager.compare_strings(ocr_result_col, ocr_text_refer)

except Exception as e:
    print(e)

# 测试ms
try:
    time_cost_ms = time.time()
    ocr_result_ms = maintainManager.ocr_image_ms(test_img_filepath)
    time_cost_ms = time.time() - time_cost_ms
    ocr_result_ms = utils.wrap_text_by_remove_break(ocr_result_ms)
    _, ocr_correct_ms = maintainManager.compare_strings(ocr_result_ms, ocr_text_refer)

except Exception as e:
    print(e)




while(True):
    print_header(step=2)
    print("OCR 引擎测试情况：\n")

    if ocr_result_ms:
        print("- Windows.Media.Ocr.Cli")
        print("准确率：", ocr_correct_ms, "识别时间：", time_cost_ms, "索引15分钟视频约用时：", utils.convert_seconds_to_hhmmss(int(time_cost_ms*350)))

    print("")

    if ocr_result_col:
        print("- chineseocr_lite_onnx")
        print("准确率：", ocr_correct_col, "识别时间：", time_cost_col, "索引15分钟视频约用时：", utils.convert_seconds_to_hhmmss(int(time_cost_col*350)))
        

    divider()
    print("> 推荐使用系统自带的 Windows.Media.Ocr.Cli，具有更快的速度、更低的性能消耗。\n")
    print("请选择提取屏幕内容时的 OCR 引擎：")
    print("1. Windows.Media.Ocr.Cli（推荐 & 默认） \n2. chineseocr_lite_onnx")
    input_lang_num = input('> ')

    if input_lang_num == '2':
        config.set_and_save_config("ocr_engine", "chineseocr_lite_onnx")
        print("OCR 引擎使用：chineseocr_lite_onnx")
        break
    else:
        config.set_and_save_config("ocr_engine", "Windows.Media.Ocr.Cli")
        print("OCR 引擎使用：Windows.Media.Ocr.Cli")
        break

divider()
subprocess.run('pause', shell=True)



# 设置显示器
while(True):
    print_header(step=3)
    print("注意：由于 pyautogui 暂未官方支持多显示器，捕风记录仪将只记录 Windows 下设置的【主显示器】\n")
    
    monitor_width = utils.get_screen_resolution().width
    monitor_height = utils.get_screen_resolution().height
    scale_width, scale_height = record.get_scale_screen_res_strategy(origin_width=monitor_width, origin_height=monitor_height)
    
    print(f"当前检测到的主显示器分辨率为：{monitor_width}x{monitor_height}，将录制的视频分辨率为：{scale_width}x{scale_height}。")
    print("此项设定将在每次录屏时自动识别，无需额外选择与设定。")
    break

divider()
subprocess.run('pause', shell=True)




# 完成初始化设定
print_header(step=4)
print("恭喜！你已完成所有初始设定。别担心，你可以随时打开 start_webui.bat 来调整设置！\n\n现在，你可以打开目录下的 start_record.bat 来开始记录屏幕内容啦。\n通过打开目录下的 start_webui.bat 来索引你的数据、调整更多个性化选项。\n")
print("> 一起捕捉贮藏风一般掠过的、你的目之所见。")
print("> 遇到问题、想反馈建议？欢迎在 https://github.com/Antonoko/Windrecorder 提交 issue 与 PR。")
divider()