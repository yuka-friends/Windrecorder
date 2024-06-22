import datetime
import os
import shutil
import subprocess
import time

import mss
import numpy as np
import pandas as pd
import pygetwindow
from send2trash import send2trash

from windrecorder import file_utils, utils
from windrecorder.config import (
    CONFIG_RECORD_PRESET,
    CONFIG_VIDEO_COMPRESS_PRESET,
    config,
)
from windrecorder.const import DATETIME_FORMAT, SCREENSHOT_CACHE_FILEPATH
from windrecorder.logger import get_logger
from windrecorder.ocr_manager import (
    compare_image_similarity_np,
    compare_strings,
    ocr_image,
)
from windrecorder.record_wintitle import get_current_wintitle

logger = get_logger(__name__)


# 录制屏幕
def record_screen(
    output_dir=config.record_videos_dir_ud,
    record_time=config.record_seconds,
    framerate=config.record_framerate,
    encoder_preset_name=config.record_encoder,
):
    """
    用ffmpeg持续录制屏幕,默认每15分钟保存一个视频文件
    """
    # 构建输出文件名
    now = datetime.datetime.now()
    video_out_name = now.strftime(DATETIME_FORMAT) + ".mp4"
    output_dir_with_date = now.strftime("%Y-%m")  # 将视频存储在日期月份子目录下
    video_saved_dir = os.path.join(output_dir, output_dir_with_date)
    file_utils.ensure_dir(video_saved_dir)
    out_path = os.path.join(video_saved_dir, video_out_name)

    def _replace_value_in_args(lst, bitrate_displays_factor):
        for i in range(len(lst)):
            if lst[i] == "CRF_NUM":
                lst[i] = f"{config.record_crf}"
            elif lst[i] == "BITRATE":
                lst[i] = f"{bitrate_displays_factor}k"
        return lst

    display_info = utils.get_display_info()
    pix_fmt_args = ["-pix_fmt", "yuv420p"]

    record_range_args = []
    if config.multi_display_record_strategy == "single" and len(display_info) > 1:  # 当有多台显示器、且选择仅录制其中一台时
        record_encoder_args = _replace_value_in_args(
            CONFIG_RECORD_PRESET[encoder_preset_name]["ffmpeg_cmd"], config.record_bitrate
        )
        if config.record_single_display_index > len(display_info):
            logger.warning("display index not detected, reset record_single_display_index to default index 1")
            config.set_and_save_config("record_single_display_index", 1)
        else:
            record_range_args = [
                "-video_size",
                f"{display_info[config.record_single_display_index]['width']}x{display_info[config.record_single_display_index]['height']}",
                "-offset_x",
                f"{display_info[config.record_single_display_index]['left']}",
                "-offset_y",
                f"{display_info[config.record_single_display_index]['top']}",
            ]
    else:
        record_encoder_args = _replace_value_in_args(
            CONFIG_RECORD_PRESET[encoder_preset_name]["ffmpeg_cmd"], int(config.record_bitrate) * (len(display_info) - 1)
        )

    ffmpeg_cmd = [
        config.ffmpeg_path,
        "-hwaccel",
        "auto",
        "-f",
        "gdigrab",
        "-framerate",
        f"{framerate}",
        *record_range_args,
        "-i",
        "desktop",
        *record_encoder_args,
        *pix_fmt_args,
        "-t",
        str(record_time),
        out_path,
    ]

    # 执行命令
    try:
        logger.info(f"record_screen: ffmpeg cmd: {ffmpeg_cmd}")
        # 运行ffmpeg
        subprocess.run(ffmpeg_cmd, check=True)
        return video_saved_dir, video_out_name
    except subprocess.CalledProcessError as ex:
        logger.error(f"Windrecorder: {ex.cmd} failed with return code {ex.returncode}")
        return video_saved_dir, video_out_name
        # FIXME 报错录制失败时给用户反馈


# 检测是否正在录屏
def is_recording():
    try:
        with open(config.record_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())
    except FileNotFoundError:
        logger.error("record: Screen recording service file lock does not exist.")
        return False

    return utils.is_process_running(check_pid, "python.exe")


# 获取视频的原始分辨率
def get_video_res(video_path):
    cmd = f"{config.ffprobe_path} -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 {video_path}"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    width, height = map(int, output.split(","))
    return width, height


# 压缩视频 CLI
def compress_video_CLI(video_path, target_width, target_height, encoder, crf_flag, crf, output_path):
    cmd = f"ffmpeg -i {video_path} -vf scale={target_width}:{target_height} -c:v {encoder} {crf_flag} {crf} -pix_fmt yuv420p {output_path}"

    logger.info(f"[compress_video_CLI] {cmd=}")
    subprocess.call(cmd, shell=True)


# 压缩视频分辨率到输入倍率
def compress_video_resolution(video_path, scale_factor):
    scale_factor = float(scale_factor)

    # 获取视频的原始分辨率
    width, height = get_video_res(video_path)

    # 计算压缩视频的目标分辨率
    target_width = int(width * scale_factor)
    target_height = int(height * scale_factor)

    # 获取编码器和加速器
    encoder_default = CONFIG_VIDEO_COMPRESS_PRESET["x264"]["cpu"]["encoder"]
    crf_flag_default = CONFIG_VIDEO_COMPRESS_PRESET["x264"]["cpu"]["crf_flag"]
    crf_default = 39
    try:
        encoder = CONFIG_VIDEO_COMPRESS_PRESET[config.compress_encoder][config.compress_accelerator]["encoder"]
        crf_flag = CONFIG_VIDEO_COMPRESS_PRESET[config.compress_encoder][config.compress_accelerator]["crf_flag"]
        crf = int(config.compress_quality)
    except KeyError:
        logger.error("Fail to get video compress config correctly. Fallback to default preset.")
        encoder = encoder_default
        crf_flag = crf_flag_default
        crf = crf_default

    # 执行压缩流程
    def encode_video(encoder=encoder, crf_flag=crf_flag, crf=crf):
        # 处理压缩视频路径
        if "-OCRED" in os.path.basename(video_path):
            output_newname = os.path.basename(video_path).replace("-OCRED", "-COMPRESS-OCRED")
        else:  # 其他用途下的压缩用（如测试）
            output_newname = f"compressed_{encoder}_{crf}_{os.path.basename(video_path)}"
        output_path = os.path.join(os.path.dirname(video_path), output_newname)

        # 如果输出目的已存在，将其移至回收站
        if os.path.exists(output_path):
            send2trash(output_path)

        compress_video_CLI(
            video_path=video_path,
            target_width=target_width,
            target_height=target_height,
            encoder=encoder,
            crf_flag=crf_flag,
            crf=crf,
            output_path=output_path,
        )

        return output_path

    # 如果系统不支持编码、导致输出的文件不正常或无输出，fallback 到默认参数
    output_path = encode_video()
    if os.path.exists(output_path):
        if os.stat(output_path).st_size < 1024:
            logger.warning("Parameter not supported, fallback to default setting.")
            send2trash(output_path)  # 清理空文件
            output_path = encode_video(encoder=encoder_default, crf_flag=crf_flag_default, crf=crf_default)
    else:
        logger.warning("Parameter not supported, fallback to default setting.")
        output_path = encode_video(encoder=encoder_default, crf_flag=crf_flag_default, crf=crf_default)

    return output_path


# 测试所有的压制参数，由 webui 指定缩放系数与 crf 压缩质量
def encode_preset_benchmark_test(scale_factor, crf):
    scale_factor = float(scale_factor)
    # 准备测试视频
    test_video_filepath = "__assets__\\test_video_compress.mp4"
    if not os.path.exists(test_video_filepath):
        logger.error("test_video_filepath not found.")
        return None

    # 准备测试环境
    test_env_folder = "cache\\encode_preset_benchmark_test"
    if os.path.exists(test_env_folder):
        shutil.rmtree(test_env_folder)
    os.makedirs(test_env_folder)

    # 执行测试压缩
    def encode_test_video(video_path, encoder, crf_flag):
        # 获取视频的原始分辨率
        width, height = get_video_res(video_path)

        # 计算压缩视频的目标分辨率
        target_width = int(width * scale_factor)
        target_height = int(height * scale_factor)

        output_newname = f"compressed_{encoder}_{crf}_{os.path.basename(video_path)}"
        output_path = os.path.join(test_env_folder, output_newname)

        compress_video_CLI(
            video_path=video_path,
            target_width=target_width,
            target_height=target_height,
            encoder=encoder,
            crf_flag=crf_flag,
            crf=crf,
            output_path=output_path,
        )

        return output_path

    # 检查是否压制成功
    def check_encode_result(filepath):
        if os.path.exists(filepath):
            if os.stat(filepath).st_size < 1024:
                return False
            return True
        else:
            return False

    origin_video_filesize = os.stat(test_video_filepath).st_size
    df_result = pd.DataFrame(columns=["encoder", "accelerator", "support", "compress_ratio", "compress_time"])

    # 测试所有参数预设
    for encoder_name, encoder in CONFIG_VIDEO_COMPRESS_PRESET.items():
        logger.info(f"Testing {encoder}")
        for encode_accelerator_name, encode_accelerator in encoder.items():
            logger.info(f"Testing {encode_accelerator}")
            time_cost = time.time()
            videofile_output_path = encode_test_video(
                video_path=test_video_filepath, encoder=encode_accelerator["encoder"], crf_flag=encode_accelerator["crf_flag"]
            )
            time_cost = time.time() - time_cost

            if check_encode_result(videofile_output_path):
                # 压制成功
                compress_video_filesize = os.stat(videofile_output_path).st_size
                compress_ratio = compress_video_filesize / origin_video_filesize
                df_result.loc[len(df_result)] = [
                    encoder_name,
                    encode_accelerator_name,
                    True,
                    format(compress_ratio, ".2f"),
                    format(time_cost, ".2f"),
                ]
            else:
                # 压制失败
                df_result.loc[len(df_result)] = [encoder_name, encode_accelerator_name, False, 0, 0]

    return df_result


# 测试所有的录制参数，由 webui 指定缩放系数与 crf 压缩质量
def record_encode_preset_benchmark_test():
    test_env_folder = "cache\\record_preset_benchmark_test"
    if os.path.exists(test_env_folder):
        shutil.rmtree(test_env_folder)
    os.makedirs(test_env_folder)

    df_result = pd.DataFrame(columns=["encoder preset", "support"])

    for encoder_preset_name in CONFIG_RECORD_PRESET.keys():
        logger.info(f"Testing {encoder_preset_name}")
        support_res = False
        try:
            video_saved_dir, video_out_name = record_screen(
                output_dir=test_env_folder, record_time=2, framerate=30, encoder_preset_name=encoder_preset_name
            )
            output_path = os.path.join(video_saved_dir, video_out_name)
            if os.path.exists(output_path):
                if os.stat(output_path).st_size < 1024:
                    support_res = False
                else:
                    support_res = True
            else:
                support_res = False
        except Exception:
            support_res = False

        df_result.loc[len(df_result)] = [
            encoder_preset_name,
            support_res,
        ]

    return df_result


def record_screen_via_screenshot_process():
    time_counter = 0
    screenshot_previous = None
    ocr_res_previous = ""
    start_record = False
    saved_dir_name = None
    tmp_db_json = {}
    last_execute_time = time.time()

    logger.debug(f"{config.record_seconds=}")
    while time_counter < config.record_seconds:
        sleep_time_second = config.screenshot_interval_second - (time.time() - last_execute_time)
        if sleep_time_second < 1:
            sleep_time_second = 1
        time.sleep(sleep_time_second)
        time_counter += config.screenshot_interval_second
        logger.debug(f"{time_counter=}, {sleep_time_second=}")

        last_execute_time = time.time()
        win_title = get_current_wintitle()
        datetime_str_record = datetime.datetime.now().strftime(DATETIME_FORMAT)
        datetime_unix_timestamp_record = int(time.time())
        screenshot_saved_filename = datetime_str_record + ".png"

        # skip custom rule
        if utils.is_str_contain_list_word(win_title, config.exclude_words):
            logger.debug(f"wintitle {win_title} contains exclude words {config.exclude_words}")
            continue

        # screenshot implement
        try:
            if config.record_screenshot_method_capture_foreground_window_only:
                logger.debug("capture_foreground_window_only")
                screenshot_current = get_screenshot_foreground_window()
            else:
                if config.multi_display_record_strategy == "single":
                    logger.debug("capture_single_display_window")
                    screenshot_current = get_screenshot_single_display(config.record_single_display_index)
                else:
                    logger.debug("capture_full_range_display")
                    screenshot_current = get_screenshot_full_range()
        except Exception as e:
            logger.error(f"capture screenshot error: {e}")
            continue

        # compare screenshots similarity
        if screenshot_previous is not None:
            img_similarity = compare_image_similarity_np(np.array(screenshot_previous), np.array(screenshot_current))
            if img_similarity > config.screenshot_compare_similarity:
                logger.debug(f"img_similarity {img_similarity} higher than config, continue")
                continue
            logger.debug(f"img_similarity {img_similarity} lower than config")
        screenshot_previous = screenshot_current

        if not start_record:
            # init behavior
            saved_dir_name = datetime.datetime.now().strftime(DATETIME_FORMAT)
            file_utils.ensure_dir(os.path.join(SCREENSHOT_CACHE_FILEPATH, saved_dir_name))
            tmp_json_db_filepath = os.path.join(SCREENSHOT_CACHE_FILEPATH, saved_dir_name, "tmp_db.json")
            start_record = True

        # store img file
        screenshot_saved_filepath = os.path.join(SCREENSHOT_CACHE_FILEPATH, saved_dir_name, screenshot_saved_filename)
        mss.tools.to_png(screenshot_current.rgb, screenshot_current.size, output=screenshot_saved_filepath)
        logger.info(f"saved screenshot to {screenshot_saved_filepath}")

        # compare OCR result similarity
        ocr_res_current = ocr_image(screenshot_saved_filepath)
        is_ocr_res_over_threshold_similarity, _ = compare_strings(
            ocr_res_previous, ocr_res_current, threshold=config.ocr_compare_similarity * 100
        )
        if is_ocr_res_over_threshold_similarity:
            logger.debug("ocr res overlaps with the previous, skip")
            continue

        # OCR index cache store
        if config.index_reduce_same_content_at_different_time:
            # deduplication res before
            for k, v in tmp_db_json.items():
                is_ocr_res_over_threshold_similarity, _ = compare_strings(
                    v["ocr_text"], ocr_res_current, threshold=config.ocr_compare_similarity_in_table * 100
                )
                if is_ocr_res_over_threshold_similarity:
                    continue

        logger.info("ocr res writing")
        ocr_res_previous = ocr_res_current
        tmp_db_json[screenshot_saved_filepath] = {
            "ocr_text": ocr_res_current,
            "win_title": win_title,
            "videofile_time": datetime_unix_timestamp_record,
        }
        file_utils.save_dict_as_json_to_path(tmp_db_json, tmp_json_db_filepath)

    # verification data

    # convert to video startegy
    if not config.convert_screenshots_to_vid_while_only_when_idle_or_plugged_in:
        pass

    # persistent writing to db


def get_screenshot_foreground_window():
    fg_window = pygetwindow.getActiveWindow()
    if fg_window:
        left, top, right, bottom = fg_window.left, fg_window.top, fg_window.right, fg_window.bottom

        with mss.mss() as sct:
            monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
            sct_img = sct.grab(monitor)
            return sct_img


def get_screenshot_single_display(display_index: int):
    if display_index > len(utils.get_display_count()):
        logger.info("config display index larger than existed displays number")
        display_index = 1
    # wip


def get_screenshot_full_range():
    # wip
    pass


def make_screenshots_into_video():
    # feasibility check
    pass
