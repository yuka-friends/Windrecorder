import os
import shutil
import subprocess
import time

import pandas as pd
from send2trash import send2trash

from windrecorder.config import config
from windrecorder.logger import get_logger
from windrecorder.utils import is_process_running

logger = get_logger(__name__)


# 检测是否正在录屏
def is_recording():
    try:
        with open(config.record_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())
    except FileNotFoundError:
        logger.error("record: Screen recording service file lock does not exist.")
        return False

    return is_process_running(check_pid, "python.exe")


# 获取录屏时目标缩放分辨率策略
def get_scale_screen_res_strategy(origin_width=1920, origin_height=1080):
    target_scale_width = origin_width
    target_scale_height = origin_height

    if origin_height > 1500 and config.record_screen_enable_half_res_while_hidpi:  # 高分屏缩放至四分之一策略
        target_scale_width = int(origin_width / 2)
        target_scale_height = int(origin_height / 2)

    return target_scale_width, target_scale_height


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
    encoder_default = config.compress_preset["x264"]["cpu"]["encoder"]
    crf_flag_default = config.compress_preset["x264"]["cpu"]["crf_flag"]
    crf_default = 39
    try:
        encoder = config.compress_preset[config.compress_encoder][config.compress_accelerator]["encoder"]
        crf_flag = config.compress_preset[config.compress_encoder][config.compress_accelerator]["crf_flag"]
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
        return

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
    for encoder_name, encoder in config.compress_preset.items():
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
