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
    if "PaddleOCR" not in support_ocr_lst:
        support_ocr_lst.append("PaddleOCR")
        config.set_and_save_config("support_ocr_lst", support_ocr_lst)


try:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    img_path = parent_parent_dir + "/__assets__/OCR_test_1080_zh-Hans-CN.png"
    result, elapse = engine(img_path)

    print("Install succeed! 安装成功！")
    set_config_module_install(True)

    from windrecorder import ocr_manager

    img_path = parent_parent_dir + "/__assets__/OCR_test_1080_zh-Hans-CN.png"
    ocr_manager.ocr_image_paddleocr(img_path, force_initialize=True)

    res = ocr_manager.ocr_benchmark(print_process=True)
    ocr_manager.format_print_benchmark(res)

    print(
        "After restarting windrecorder, you can see the option of the third-party OCR engine. After configuration, restart windrecorder to using it."
    )
    print("重启 windrecorder 后即可看到第三方 OCR 引擎选项。配置完成后重启 windrecorder 以应用。")

    # import paddle
    # from paddleocr import PaddleOCR

    # paddle.utils.run_check()

    # # Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
    # # 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
    # ocr = PaddleOCR(
    #     use_angle_cls=False,
    #     lang="ch",
    #     det_limit_side_len=int(config.ocr_short_size),
    #     enable_mkldnn=True,
    #     show_log=True,
    # )
    # img_path = parent_parent_dir + "/__assets__/OCR_test_1080_zh-Hans-CN.png"
    # result = ocr.ocr(img_path, cls=False)

    # # 显示结果
    # # print(result)
    # result = result[0]
    # txts = [line[1][0] for line in result]
    # print(txts)


except Exception as e:
    print(f"Install failed. 安装失败: {e}")
    set_config_module_install(False)
