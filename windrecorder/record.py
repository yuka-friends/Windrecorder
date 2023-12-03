import os
import subprocess

from send2trash import send2trash

from windrecorder.config import config


# 检测是否正在录屏
def is_recording():
    try:
        with open(config.record_lock_path, encoding="utf-8") as f:
            check_pid = int(f.read())
    except FileNotFoundError:
        print("record: Screen recording service file lock does not exist.")
        return False

    check_result = subprocess.run(["tasklist"], stdout=subprocess.PIPE, text=True)
    check_output = check_result.stdout
    check_result = subprocess.run(
        ["findstr", str(check_pid)],
        input=check_output,
        stdout=subprocess.PIPE,
        text=True,
    )
    check_output = check_result.stdout
    if "python" in check_output:
        state_is_recording = True
        print(f"record: state_is_recording:{state_is_recording}")
        return True
    else:
        state_is_recording = False
        print(f"record: state_is_recording:{state_is_recording}")
        return False

    # 试图使用据说可以自动更新的组件来强制刷新状态
    # (https://towardsdatascience.com/creating-dynamic-dashboards-with-streamlit-747b98a68ab5)
    # placeholder.text(
    #     f"state_is_recording:{state_is_recording}")


# 用另外的线程虽然能持续检测到服务有没有运行，但是byd streamlit就是没法自动更新，state只能在主线程访问；
# 用了这个（https://github.com/streamlit/streamlit/issues/1326）讨论中的临时措施
# 虽然可以自动更新了，但还是无法动态更新页面
# 目的：让它可以自动检测服务是否在运行，并且在页面中更新显示状态
# timer_repeat_check_recording = RepeatingTimer(5, repeat_check_recording)
# add_script_run_ctx(timer_repeat_check_recording)
# timer_repeat_check_recording.start()


# 获取录屏时目标缩放分辨率策略
def get_scale_screen_res_strategy(origin_width=1920, origin_height=1080):
    target_scale_width = origin_width
    target_scale_height = origin_height

    if origin_height > 1500 and config.record_screen_enable_half_res_while_hidpi:  # 高分屏缩放至四分之一策略
        target_scale_width = int(origin_width / 2)
        target_scale_height = int(origin_height / 2)

    return target_scale_width, target_scale_height


# 压缩视频分辨率到输入倍率
def compress_video_resolution(video_path, scale_factor):
    scale_factor = float(scale_factor)

    # 获取视频的原始分辨率
    cmd = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 {video_path}"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    width, height = map(int, output.split(","))

    # 计算目标分辨率
    target_width = int(width * scale_factor)
    target_height = int(height * scale_factor)

    # 压缩视频分辨率
    # output_path = f'compressed_{target_width}x{target_height}.mp4'
    output_newname = os.path.basename(video_path).replace("-OCRED", "-COMPRESS-OCRED")
    output_path = os.path.join(os.path.dirname(video_path), output_newname)
    if os.path.exists(output_path):
        send2trash(output_path)
    cmd = f"ffmpeg -i {video_path} -vf scale={target_width}:{target_height} -c:v libx264 -crf 39 {output_path}"
    subprocess.call(cmd, shell=True)

    return output_path
