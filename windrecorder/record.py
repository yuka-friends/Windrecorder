import datetime
import os
import random
import shutil
import subprocess
import time

import cv2
import mss
import numpy as np
import pandas as pd
import pygetwindow
from PIL import Image, ImageDraw
from send2trash import send2trash

from windrecorder import file_utils, utils
from windrecorder.config import (
    CONFIG_RECORD_PRESET,
    CONFIG_VIDEO_COMPRESS_PRESET,
    config,
)
from windrecorder.const import (
    DATAFRAME_COLUMN_NAMES,
    DATE_FORMAT,
    DATETIME_FORMAT,
    MINIMUM_NUMBER_OF_IMAGES_REQUIRED_FOR_A_VIDEO,
    OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID,
    OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID_WITHOUT_IMGEMB,
    SCREENSHOT_CACHE_FILEPATH,
    SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME,
    SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME,
)
from windrecorder.db_manager import db_manager
from windrecorder.logger import get_logger
from windrecorder.ocr_manager import (
    compare_image_similarity_np,
    compare_strings,
    ocr_image,
)
from windrecorder.record_wintitle import (
    get_current_wintitle,
    get_foreground_deep_linking,
)

logger = get_logger(__name__)


# 录制屏幕
def record_screen_via_ffmpeg(
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
    output_dir_with_date = now.strftime(DATE_FORMAT)  # 将视频存储在日期月份子目录下
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
    cmd = f"ffmpeg -hwaccel auto -i {video_path} -vf scale={target_width}:{target_height} -c:v {encoder} {crf_flag} {crf} -pix_fmt yuv420p {output_path}"

    logger.info(f"[compress_video_CLI] {cmd=}")
    subprocess.call(cmd, shell=True)


# 压缩视频分辨率到输入倍率
def compress_video_resolution(video_path, scale_factor, custom_output_name=None):
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
        if custom_output_name:
            output_newname = custom_output_name
        else:
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


# 检查视频文件夹中所有文件的日期，对超出储存时限的文件进行压缩操作(todo)
def compress_outdated_videofiles(video_queue_batch=30):
    if config.vid_compress_day == 0:
        return None

    video_process_count = 0

    today_datetime = datetime.datetime.today()
    days_to_subtract = config.vid_compress_day
    start_datetime = datetime.datetime(2000, 1, 1, 0, 0, 1)
    end_datetime = today_datetime - datetime.timedelta(days=days_to_subtract)

    video_filepath_list = file_utils.get_file_path_list(config.record_videos_dir_ud)
    video_filepath_list_outdate = file_utils.get_videofile_path_list_by_time_range(
        video_filepath_list, start_datetime, end_datetime
    )
    logger.info(f"file to compress {video_filepath_list_outdate}")

    if len(video_filepath_list_outdate) > 0:
        for item in video_filepath_list_outdate:
            if "-COMPRESS" not in item and "-OCRED" in item and "-ERROR" not in item:
                logger.info(f"compressing {item}, {video_process_count=}, {video_queue_batch=}")
                try:
                    compress_video_resolution(item, config.video_compress_rate)
                    send2trash(item)
                    video_process_count += 1
                except subprocess.CalledProcessError as e:
                    logger.error(f"{item} seems invalid, error: {e}")
                    os.rename(item, item.replace("-OCRED", "-OCRED-ERROR"))
                except Exception as e:
                    logger.error(f"{item} compress fail, error: {e}")
                if video_process_count > video_queue_batch:
                    break
        logger.info("All compress tasks done!")


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
            video_saved_dir, video_out_name = record_screen_via_ffmpeg(
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
    """流程：持续地截图录制"""

    def _crop_ocr_image(image_filepath):
        if len(config.ocr_image_crop_URBL) >= 4:
            ocr_image_crop_URBL = config.ocr_image_crop_URBL
        else:
            ocr_image_crop_URBL = [6, 6, 6, 3]
        image = Image.open(image_filepath)
        draw = ImageDraw.Draw(image)
        img_width, img_height = image.size

        # 计算涂黑的区域
        top_black = (
            0,
            0,
            img_width,
            int(img_height * (ocr_image_crop_URBL[0] / 100)),
        )
        bottom_black = (
            0,
            int(img_height * (1 - (ocr_image_crop_URBL[2] / 100))),
            img_width,
            img_height,
        )
        left_black = (
            0,
            0,
            int(img_width * (ocr_image_crop_URBL[3] / 100)),
            img_height,
        )
        right_black = (
            int(img_width * (1 - (ocr_image_crop_URBL[1] / 100))),
            0,
            img_width,
            img_height,
        )
        draw.rectangle(top_black, fill="black")
        draw.rectangle(bottom_black, fill="black")
        draw.rectangle(left_black, fill="black")
        draw.rectangle(right_black, fill="black")
        screenshot_cropped_saved_filepath = image_filepath.replace(".png", "_cropped.png")
        image.save(screenshot_cropped_saved_filepath)
        return screenshot_cropped_saved_filepath

    time_counter = 0
    screenshot_previous = None
    ocr_res_previous = ""
    start_record = False
    saved_dir_name = None
    saved_dir_filepath = None
    screen_lock_interrupt_counter = 0
    screen_lock_interrupt_timeout = 3
    tmp_db_json = {"data": []}
    tmp_db_json_all_files = {"data": []}
    last_execute_time = time.time()

    logger.info(f"start new screenshot record: {config.record_seconds=}, {config.screenshot_interval_second}")
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
        datetime_unix_timestamp_record = utils.dtstr_to_seconds(
            datetime_str_record
        )  # ignore timezone convert walkaround FIXME
        screenshot_saved_filename = datetime_str_record + ".png"

        # if screen lock or system sleep
        if utils.is_screen_locked():
            screen_lock_interrupt_counter += 1
            logger.info(f"screen locked, {screen_lock_interrupt_counter=}")
            continue
        if not utils.is_system_awake():
            logger.info("system sleep, recording break")
            break
        if screen_lock_interrupt_counter > screen_lock_interrupt_timeout:
            logger.info(
                f"screen locked {screen_lock_interrupt_counter=} longer than timeout {screen_lock_interrupt_timeout=}, recording stopped"
            )
            break

        # skip custom rule
        if utils.is_str_contain_list_word(win_title, config.exclude_words):
            logger.info(f"wintitle {win_title} contains exclude words {config.exclude_words}")
            continue

        # get deep linking
        deep_linking = ""
        if config.record_deep_linking:
            deep_linking = get_foreground_deep_linking(win_title)

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
            try:
                img_similarity = compare_image_similarity_np(np.array(screenshot_previous), np.array(screenshot_current))
                if img_similarity > config.screenshot_compare_similarity:
                    logger.debug(f"img_similarity {img_similarity} higher than config, continue")
                    continue
            except Exception as e:
                logger.error(
                    f"compare img_similarity fail:{e}, {np.array(screenshot_previous).shape=}, {np.array(screenshot_previous).dtype=}, {np.array(screenshot_current).shape=}, {np.array(screenshot_current).dtype=}"
                )
                continue
            logger.debug(f"img_similarity {img_similarity} lower than config")

        if str(np.array(screenshot_current).dtype) == "uint8":
            screenshot_previous = screenshot_current

        # start record init
        if not start_record:
            # init behavior
            time_counter = 0  # reset time counter for a full video recording
            saved_dir_name = datetime.datetime.now().strftime(DATETIME_FORMAT)
            saved_dir_filepath = os.path.join(SCREENSHOT_CACHE_FILEPATH, saved_dir_name)
            file_utils.ensure_dir(saved_dir_filepath)
            tmp_json_db_filepath = os.path.join(
                SCREENSHOT_CACHE_FILEPATH, saved_dir_name, SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME
            )
            tmp_db_json_all_files_filepath = os.path.join(
                SCREENSHOT_CACHE_FILEPATH, saved_dir_name, SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME
            )
            start_record = True

        # store img file
        screenshot_saved_filepath = os.path.join(SCREENSHOT_CACHE_FILEPATH, saved_dir_name, screenshot_saved_filename)
        mss.tools.to_png(screenshot_current.rgb, screenshot_current.size, output=screenshot_saved_filepath)
        screenshot_cropped_saved_filepath = _crop_ocr_image(screenshot_saved_filepath)
        tmp_db_json_all_files["data"].append(
            {
                "vid_file_name": saved_dir_name + ".mp4",
                "img_file_name": screenshot_saved_filepath,
                "datetime_str_record": datetime_str_record,
            }
        )  # Used to count all file information that will be converted to video
        file_utils.save_dict_as_json_to_path(tmp_db_json_all_files, tmp_db_json_all_files_filepath)
        logger.info(f"saved screenshot to {screenshot_saved_filepath}")

        # compare OCR result similarity
        ocr_res_current = ocr_image(screenshot_cropped_saved_filepath)
        logger.debug(f"{ocr_res_current=}")
        if ocr_res_current is None:
            continue
        if len(ocr_res_current) < 5:
            continue
        is_ocr_res_over_threshold_similarity, _ = compare_strings(
            ocr_res_previous, ocr_res_current, threshold=config.ocr_compare_similarity * 100
        )
        if is_ocr_res_over_threshold_similarity:
            logger.debug("ocr res overlaps with the previous, skip")
            continue

        # OCR index cache store
        if config.index_reduce_same_content_at_different_time:
            # deduplication res before
            for v in tmp_db_json["data"]:
                is_ocr_res_over_threshold_similarity, _ = compare_strings(
                    v["ocr_text"], ocr_res_current, threshold=config.ocr_compare_similarity_in_table * 100
                )
                if is_ocr_res_over_threshold_similarity:
                    continue

        # presistent data
        logger.info("ocr res writing")
        ocr_res_previous = ocr_res_current
        tmp_db_json["data"].append(
            {
                "vid_file_name": saved_dir_name + ".mp4",
                "img_file_name": screenshot_saved_filepath,
                "ocr_text": ocr_res_current,
                "win_title": win_title,
                "deep_linking": deep_linking,
                "videofile_time": datetime_unix_timestamp_record,
                "datetime_str_record": datetime_str_record,
                "thumbnail": utils.resize_image_as_base64_as_thumbnail_via_filepath(screenshot_saved_filepath),
            }
        )  # Used to index to sqlite db
        file_utils.save_dict_as_json_to_path(tmp_db_json, tmp_json_db_filepath)

    # persistent submit to db
    submit_data_to_sqlite_db_process(saved_dir_filepath)

    return saved_dir_filepath


def submit_data_to_sqlite_db_process(saved_dir_filepath):
    """流程：将已索引的 tmp json 提交到 sqlite db"""
    logger.info(f"submitting {saved_dir_filepath} to db")
    try:
        # verification data
        tmp_db_json = file_utils.read_json_as_dict_from_path(
            os.path.join(saved_dir_filepath, SCREENSHOT_CACHE_FILEPATH_TMP_DB_NAME)
        )
        if tmp_db_json is None:
            logger.info("tmp_db_json is None")
            return None
        if len(tmp_db_json["data"]) < 5:
            logger.info("tmp_db_json records not enough")
            try:
                if len(file_utils.get_file_path_list(saved_dir_filepath)) < 10:
                    send2trash(saved_dir_filepath)
                else:
                    os.rename(saved_dir_filepath, saved_dir_filepath + "-DISCARD")
            except Exception as e:
                logger.error(f"discard incomplete cache fail: {e}")
            return None
        # convert tmp_db_json to dataframe
        dataframe_all = pd.DataFrame(columns=DATAFRAME_COLUMN_NAMES)
        for v in tmp_db_json["data"]:
            # deep linking update
            _deep_linking = ""
            if "deep_linking" in v.keys():
                _deep_linking = v["deep_linking"]

            dataframe_all.loc[len(dataframe_all.index)] = [
                v["vid_file_name"],
                v["img_file_name"],
                v["videofile_time"],
                v["ocr_text"],
                True,
                False,
                v["thumbnail"],
                v["win_title"],
                _deep_linking,
            ]
        db_manager.db_add_dataframe_to_db_process(dataframe_all)
        os.makedirs(os.path.join(saved_dir_filepath, "-SUBMIT"), exist_ok=True)
    except Exception as e:
        logger.error(f"submitting to db fail: {e}")


def convert_screenshots_dir_into_video_process(saved_dir_filepath):
    """流程：将缓存的截图文件夹转换为视频"""
    try:
        if saved_dir_filepath is None:
            logger.error("saved_dir_filepath is None")
            return
        output_video_filepath, is_garbage_data_should_be_clean = make_screenshots_into_video_via_dir_path(saved_dir_filepath)
        if output_video_filepath:
            output_video_filepath_compress = compress_video_resolution(
                output_video_filepath,
                1,
                custom_output_name=os.path.basename(output_video_filepath).replace("-NOTCOMPRESS", ""),
            )
            if os.path.exists(output_video_filepath_compress):
                send2trash(output_video_filepath)
            os.rename(saved_dir_filepath, saved_dir_filepath + "-VIDEO")
            return saved_dir_filepath + "-VIDEO"
        if is_garbage_data_should_be_clean:
            os.rename(saved_dir_filepath, saved_dir_filepath + "-DISCARD")
            return saved_dir_filepath + "-DISCARD"
        return saved_dir_filepath
    except Exception as e:
        logger.error(e)


def index_cache_screenshots_dir_process():
    """流程：索引所有未转换为视频、未提交到数据库的文件夹截图"""

    def _len_db_all_json_data(dir_path):
        tmp_db_json_filepath = os.path.join(dir_path, SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME)
        tmp_db_json_datalist = file_utils.read_json_as_dict_from_path(tmp_db_json_filepath)
        if tmp_db_json_datalist is None:
            return 0
        if "data" not in tmp_db_json_datalist.keys():
            return 0
        tmp_db_json_datalist = tmp_db_json_datalist["data"]
        return len(tmp_db_json_datalist)

    dir_lst = file_utils.get_screenshots_cache_dir_lst()
    for dir_path in dir_lst:
        if not os.path.exists(os.path.join(dir_path, "-SUBMIT")) and "-DISCARD" not in dir_path:
            logger.info(f"{dir_path} not submit to db, submiting...")
            submit_data_to_sqlite_db_process(dir_path)
        if "-VIDEO" not in dir_path and os.path.exists(os.path.join(dir_path, "-SUBMIT")):
            logger.info(f"{dir_path} not convert to video, converting...")
            convert_screenshots_dir_into_video_process(dir_path)
        elif (
            _len_db_all_json_data(dir_path) < MINIMUM_NUMBER_OF_IMAGES_REQUIRED_FOR_A_VIDEO
            or len(file_utils.get_file_path_list_first_level(dir_path)) < MINIMUM_NUMBER_OF_IMAGES_REQUIRED_FOR_A_VIDEO + 2
        ):
            logger.info(f"{dir_path} not enough data, marked as DISCARD.")
            os.rename(dir_path, dir_path + "-DISCARD")


def clean_cache_screenshots_dir_process():
    """流程：清理已转换为视频、已经完成图像嵌入的文件夹（若安装开启了图像嵌入），超出存储日期范围的文件夹（区分开启与无开启图像嵌入）"""
    outdate_day = OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID
    if config.enable_img_embed_search and config.img_embed_module_install:
        outdate_day = OUTDATE_DAY_TO_DELETE_SCREENSHOTS_CACHE_CONVERTED_TO_VID_WITHOUT_IMGEMB
    dir_lst = file_utils.get_screenshots_cache_dir_lst()
    video_lst = file_utils.get_file_path_list(config.record_videos_dir_ud)
    for dir_path in dir_lst:
        if "-VIDEO" in dir_path and "-IMGEMB" in dir_path:
            send2trash(dir_path)
        elif "-VIDEO" in dir_path or any(os.path.basename(dir_path)[:19] in word for word in video_lst):
            if datetime.datetime.now() - utils.dtstr_to_datetime(os.path.basename(dir_path)[:19]) > datetime.timedelta(
                days=outdate_day
            ):
                send2trash(dir_path)
        elif not os.path.exists(os.path.join(dir_path, SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME)):
            send2trash(dir_path)
        elif "-DISCARD" in dir_path:
            send2trash(dir_path)


def get_screenshot_foreground_window():
    fg_window = pygetwindow.getActiveWindow()
    if fg_window:
        left, top, right, bottom = fg_window.left, fg_window.top, fg_window.right, fg_window.bottom

        with mss.mss() as sct:
            monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
            sct_img = sct.grab(monitor)
            return sct_img


def get_screenshot_single_display(display_index: int):
    if display_index > utils.get_display_count():
        logger.info("config display index larger than existed displays number")
        display_index = 1

    with mss.mss() as sct:
        sct_img = sct.grab(sct.monitors[display_index])
        return sct_img


def get_screenshot_full_range():
    with mss.mss() as sct:
        sct_img = sct.grab(sct.monitors[0])
        return sct_img


def convert_screenshots_dir_into_same_size_to_cache(
    src_folder, canvas_color=utils.hex_to_rgb(config.foreground_window_video_background_color)
):
    """
    遍历src_folder中的所有图片，找出最大的图片尺寸，
    然后将每张图片居中放到这样大小的指定颜色空画布上，
    并保存到dest_folder中。
    :param src_folder: 源文件夹路径
    :param canvas_color: 画布颜色
    """

    def check_are_image_sizes_same(directory):
        """
        检查指定目录下所有图片文件是否都具有相同的尺寸大小。
        Returns:
            bool: 如果所有图片尺寸相同返回True，否则返回False。
            tuple: 返回第一张图片的尺寸(width, height)。如果目录为空或无图片文件，则返回(None, None)。
        """
        image_files = [
            f
            for f in os.listdir(directory)
            if f.endswith((".png", ".jpg", ".jpeg")) and "_cropped" not in f and "_error" not in f
        ]

        if not image_files:
            logger.debug(f"No image files were found in {directory}.")
            return True, (None, None)

        first_image = os.path.join(directory, image_files[0])
        reference_size = Image.open(first_image).size

        for image_file in image_files[1:]:
            image_path = os.path.join(directory, image_file)
            image_size = Image.open(image_path).size

            if image_size != reference_size:
                logger.debug(
                    f"The size {image_size} of {image_file} is different from the size {reference_size} of {image_files[0]}."
                )
                return False, reference_size

        return True, reference_size

    check_are_screenshots_sizes_same, _ = check_are_image_sizes_same(src_folder)
    if check_are_screenshots_sizes_same:
        logger.debug("screenshots got same size")
        return

    logger.debug("uniform screenshots size...")
    # 查找最大的图片尺寸
    max_width, max_height = 0, 0
    for img_name in os.listdir(src_folder):
        if not img_name.lower().endswith((".png", ".jpg", ".jpeg")) or "_cropped" in img_name or "_error" in img_name:
            continue
        img_path = os.path.join(src_folder, img_name)
        with Image.open(img_path) as img:
            width, height = img.size
            max_width, max_height = max(max_width, width), max(max_height, height)

    # 调整图片大小并保存
    for img_name in os.listdir(src_folder):
        if not img_name.lower().endswith((".png", ".jpg", ".jpeg")) or "_cropped" in img_name or "_error" in img_name:
            continue
        img_path = os.path.join(src_folder, img_name)
        logger.debug(f"process screenshots size: {img_path}")
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                new_img = Image.new("RGB", (max_width, max_height), color=canvas_color)
                x = (max_width - width) // 2
                y = (max_height - height) // 2
                new_img.paste(img, (x, y))
                new_img.save(img_path)
        except Exception as e:
            logger.error(f"resize fail {img_path}: {e}")
            os.rename(img_path, img_path + "_error")


def make_screenshots_into_video_via_dir_path(saved_dir_filepath):
    """
    将文件夹中的截图合并为视频，根据文件夹中的临时数据库
    return filepath(str), is_garbage_data_should_be_clean(bool)
    """

    def calc_screenshot_filepath_to_unix_timestamp(screenshot_filepath):
        return utils.dtstr_to_seconds(os.path.basename(screenshot_filepath).split(".")[0])

    def calc_screenshot_time_to_video_time(tmp_db_json_datalist: list):
        pic_timestamp_mapping = []  # second: screenshot filepath
        sec_base_unix_timestamp = calc_screenshot_filepath_to_unix_timestamp(tmp_db_json_datalist[0]["img_file_name"])

        for i, v in enumerate(tmp_db_json_datalist):
            if not os.path.exists(v["img_file_name"]):
                continue
            res = {
                "timestamp": calc_screenshot_filepath_to_unix_timestamp(v["img_file_name"]) - sec_base_unix_timestamp,
                "screenshot_saved_filepath": v["img_file_name"],
            }
            pic_timestamp_mapping.append(res)

        res_buffer = {
            "timestamp": calc_screenshot_filepath_to_unix_timestamp(tmp_db_json_datalist[-1]["img_file_name"])
            - sec_base_unix_timestamp
            + 2,
            "screenshot_saved_filepath": tmp_db_json_datalist[-1]["img_file_name"],
        }
        pic_timestamp_mapping.append(res_buffer)

        logger.debug(f"{pic_timestamp_mapping=}")
        return pic_timestamp_mapping

    def create_video_from_images(tmp_db_json_datalist, output_video):
        logger.info(f"converting screenshots into video {output_video}...")
        pic_timestamp_mapping = calc_screenshot_time_to_video_time(tmp_db_json_datalist)

        # 假定所有图片大小相同，获取第一张图片的尺寸来设置视频的分辨率
        frame = cv2.imread(pic_timestamp_mapping[0]["screenshot_saved_filepath"])
        height, width, layers = frame.shape
        video = cv2.VideoWriter(output_video, cv2.VideoWriter_fourcc(*"mp4v"), 1, (width, height))

        prev_time = 0
        for v in pic_timestamp_mapping:
            seconds = v["timestamp"]
            duration = seconds - prev_time
            prev_time = seconds

            logger.debug(f"writing frame: {v['screenshot_saved_filepath']}, {duration=}")
            frame = cv2.imread(v["screenshot_saved_filepath"])
            for j in range(duration):  # 根据持续时间重复帧
                video.write(frame)

        cv2.destroyAllWindows()
        video.release()

    # main
    # read temp database
    tmp_db_json_filepath = os.path.join(saved_dir_filepath, SCREENSHOT_CACHE_FILEPATH_TMP_DB_ALL_FILES_NAME)
    if not os.path.exists(tmp_db_json_filepath):
        logger.error(f"{tmp_db_json_filepath} not existed")
        return None, False
    tmp_db_json_datalist = file_utils.read_json_as_dict_from_path(tmp_db_json_filepath)
    if tmp_db_json_datalist is None:
        logger.info(f"{tmp_db_json_filepath} not have data")
        return None, True
    if "data" not in tmp_db_json_datalist.keys():
        logger.info(f"{tmp_db_json_filepath} not have data")
        return None, True
    tmp_db_json_datalist = tmp_db_json_datalist["data"]
    if len(tmp_db_json_datalist) < MINIMUM_NUMBER_OF_IMAGES_REQUIRED_FOR_A_VIDEO:
        logger.info(f"{tmp_db_json_filepath} not have enough data")
        return None, True
    output_video_filepath = os.path.join(
        config.record_videos_dir_ud,
        utils.dtstr_to_datetime(tmp_db_json_datalist[0]["vid_file_name"].replace(".mp4", "")).strftime(DATE_FORMAT),
        tmp_db_json_datalist[0]["vid_file_name"].replace(".mp4", "-SCREENSHOTS-OCRED-NOTCOMPRESS.mp4"),
    )
    file_utils.ensure_dir(os.path.dirname(output_video_filepath))
    # uniform screenshots
    try:
        convert_screenshots_dir_into_same_size_to_cache(saved_dir_filepath)
    except Exception as e:
        logger.error(f"convert screenshots to uniform size fail {saved_dir_filepath}: {e}")
        return None, False
    # make video
    try:
        create_video_from_images(tmp_db_json_datalist, output_video_filepath)
    except Exception as e:
        logger.error(f"convert screenshots to video fail {output_video_filepath}: {e}")
        return None, False
    logger.info(f"converted screenshots to video: {output_video_filepath}")
    return output_video_filepath, False


def try_empty_cache_dir_in_idle_routine():
    """在空闲时清理缓存文件夹"""
    try:
        if random.randint(1, 30) == 1:
            file_utils.empty_directory("cache")
    except Exception as e:
        logger.warning(f"empty cache dir fail: {e}")
