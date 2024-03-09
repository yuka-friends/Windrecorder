import datetime
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from os import getpid
from subprocess import Popen

import pygetwindow
import pystray
import requests
import win32con
import win32gui
from PIL import Image
from streamlit.file_util import get_streamlit_file_path

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
os.chdir(PROJECT_ROOT)

from windrecorder import file_utils, flag_mark_note, utils, win_ui  # NOQA: E402
from windrecorder.config import config  # NOQA: E402
from windrecorder.exceptions import LockExistsException  # NOQA: E402
from windrecorder.lock import FileLock  # NOQA: E402
from windrecorder.utils import get_text as _t  # NOQA: E402

# 定义存储标准输出的日志文件路径
WEBUI_STDOUT_PATH = os.path.join(config.log_dir, "webui.log")
WEBUI_STDERR_PATH = os.path.join(config.log_dir, "webui.err")
RECORDING_STDOUT_PATH = os.path.join(config.log_dir, "recording.log")
RECORDING_STDERR_PATH = os.path.join(config.log_dir, "recording.err")

STREAMLIT_LOCAL_URL_REGEX = re.compile("Local URL: (.+)")  # 正则表达式，从 Streamlit 的标准输出中提取 webui_local_url
STREAMLIT_NETWORK_URL_REGEX = re.compile("Network URL: (.+)")
STREAMLIT_OPEN_TIMEOUT = 10  # Streamlit 启动的超时时间，单位为秒
RECORDING_STOP_TIMEOUT = 5  # 停止录制的超时时间，单位为秒

streamlit_process: Popen | None = None  # 存储 Streamlit 进程的实例，表示是否正在运行 Streamlit Web UI。初始值为 None，表示没有正在运行的进程。
recording_process: Popen | None = None  # 存储录制进程的实例，表示是否正在进行屏幕录制。初始值为 None，表示没有正在运行的录制进程。
webui_local_url = ""
webui_network_url = ""


def get_tray_icon(state="recording"):
    IMAGE_STATE = {"recording": "icon-tray.png", "record_pause": "icon-tray-pause.png"}
    image = Image.open(os.path.join("__assets__", IMAGE_STATE[state]))
    image = image.convert("RGBA")
    return image


def update(icon: pystray.Icon, item: pystray.MenuItem):
    webbrowser.open(os.path.join(PROJECT_ROOT, "install_update.bat"))
    on_exit(icon=icon, item=item)


file_utils.ensure_dir("cache")
file_utils.ensure_dir(config.log_dir)
file_utils.ensure_dir(config.lock_file_dir)
file_utils.ensure_dir(config.maintain_lock_path)

file_utils.empty_directory(config.maintain_lock_path)


# 调用浏览器打开 web ui
def open_webui(icon: pystray.Icon, item: pystray.MenuItem):
    webbrowser.open(webui_local_url)


# 调用浏览器打开更新日记
def open_web_changelog(icon: pystray.Icon, item: pystray.MenuItem):
    webbrowser.open("https://github.com/yuka-friends/Windrecorder/blob/main/CHANGELOG.md")


def setup(icon: pystray.Icon):
    icon.visible = True
    if config.start_recording_on_startup:
        icon.notify(message=_t("tray_notify_text"), title=_t("tray_notify_title"))
    else:
        icon.notify(message=_t("tray_notify_text_start_without_record"), title=_t("tray_notify_title_record_pause"))


# 启动/停止 webui 服务
def start_stop_webui(icon: pystray.Icon, item: pystray.MenuItem):
    global streamlit_process, webui_local_url, webui_network_url
    if streamlit_process:
        streamlit_process.kill()
        streamlit_process = None
    else:
        with open(WEBUI_STDOUT_PATH, "w", encoding="utf-8") as out, open(WEBUI_STDERR_PATH, "w", encoding="utf-8") as err:
            streamlit_process = Popen(
                [sys.executable, "-u", "-m", "streamlit", "run", "webui.py"],
                stdout=out,
                stderr=err,
                encoding="utf-8",
                cwd=PROJECT_ROOT,
            )
        time_spent = 0  # 记录启动服务以来已等待的时间
        while time_spent < STREAMLIT_OPEN_TIMEOUT:
            # 从标准输出中寻找 streamlit 启动的地址
            with open(WEBUI_STDOUT_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            m = STREAMLIT_NETWORK_URL_REGEX.search(content)
            if m:
                webui_network_url = m[1]
            m = STREAMLIT_LOCAL_URL_REGEX.search(content)
            if m:
                webui_local_url = m[1]
                break

            # 若找不到匹配结果，等待后重试
            time.sleep(1)
            time_spent += 1
        else:
            # 启动 webui 超时，停止服务
            streamlit_process.kill()
            streamlit_process = None
            icon.notify(
                f"Webui started timeout, check '{config.log_dir}' for more information. (It takes more than {STREAMLIT_OPEN_TIMEOUT} seconds to launch.)"
            )


# 开始/停止录制
def start_stop_recording(icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None):
    global recording_process

    if recording_process:
        # 如果已有进程在录制，则发送 CTRL_BREAK_EVENT 信号停止录制
        recording_process.send_signal(signal.CTRL_BREAK_EVENT)
        try:
            # 等待录制进程停止，最长等待 RECORDING_STOP_TIMEOUT 秒
            recording_process.wait(RECORDING_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            # 如果超时仍未停止，向用户发送通知，并强制终止进程
            if icon:
                icon.notify("Failed to exit the recording service gracefully. Killing it.")
            recording_process.kill()
        recording_process = None  # 清空录制进程变量
        if icon is not None:
            icon.icon = get_tray_icon(state="record_pause")
            icon.title = _t("tray_tip_record_pause")
            icon.notify(message=_t("tray_notify_text_start_without_record"), title=_t("tray_notify_title_record_pause"))
    else:
        # 如果录制进程不存在，则启动录制进程
        with open(RECORDING_STDOUT_PATH, "w", encoding="utf-8") as out, open(
            RECORDING_STDERR_PATH, "w", encoding="utf-8"
        ) as err:
            recording_process = Popen(
                [sys.executable, "-u", "record_screen.py"],
                stdout=out,
                stderr=err,
                encoding="utf-8",
                cwd=PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        if icon is not None:
            icon.icon = get_tray_icon(state="recording")
            icon.title = _t("tray_tip_record")
            icon.notify(message=_t("tray_notify_text"), title=_t("tray_notify_title"))


# 记录当下的时间标记
def create_timestamp_flag_mark_note(icon: pystray.Icon | None = None, item: pystray.MenuItem | None = None):
    datetime_created = datetime.datetime.now()
    flag_mark_note.add_new_flag_record_from_tray(datetime_created=datetime_created)
    app = flag_mark_note.Flag_mark_window(datetime_input=datetime_created)
    app.update()
    app.textbox.focus_set()  # 将光标定位到输入框
    app.mainloop()  # 启动备注记录弹窗


# 生成系统托盘菜单
def menu_callback():
    try:
        # 获取可用的新版本（如果有）
        new_version = utils.get_new_version_if_available()
    except requests.ConnectionError:
        new_version = None
    current_version = utils.get_current_version()  # 获取当前版本

    # 返回生成的菜单项列表
    return (
        # 记录当下的时间标记
        pystray.MenuItem(
            lambda item: _t("tray_add_flag_mark_note_for_now"),
            create_timestamp_flag_mark_note,
            enabled=recording_process,
        ),
        # 分隔线
        pystray.Menu.SEPARATOR,
        # 开始或停止 Web UI
        pystray.MenuItem(
            lambda item: _t("tray_webui_exit") if streamlit_process else _t("tray_webui_start"), start_stop_webui
        ),
        # 使用浏览器打开 Web UI
        pystray.MenuItem(
            lambda item: _t("tray_webui_address").format(address_port=webui_local_url),
            open_webui,
            visible=lambda item: streamlit_process,
            default=True,
        ),
        # 局域网 URL 显示
        pystray.MenuItem(
            lambda item: _t("tray_webui_address_network").format(address_port=webui_network_url),
            None,
            visible=lambda item: bool(webui_network_url) and streamlit_process,
            enabled=False,
        ),
        # 开始或停止录制选项
        pystray.MenuItem(
            lambda item: _t("tray_record_stop") if recording_process else _t("tray_record_start"), start_stop_recording
        ),
        # 分隔线
        pystray.Menu.SEPARATOR,
        # 更新选项
        pystray.MenuItem(
            lambda item: (
                _t("tray_update_cta").format(version=new_version)
                if new_version is not None
                else _t("tray_version_info").format(version=current_version)
            ),
            update,
            enabled=lambda item: new_version is not None,
        ),
        # 查看更新日志
        pystray.MenuItem(
            _t("tray_updatelog"),
            open_web_changelog,
            visible=lambda item: new_version is not None,
        ),
        # 退出选项
        pystray.MenuItem(_t("tray_exit"), on_exit),
    )


# 处理退出操作
def on_exit(icon: pystray.Icon, item: pystray.MenuItem):
    # 如果存在 Web UI 进程，则强制终止它
    if streamlit_process:
        streamlit_process.kill()

    # 如果存在录制进程，则发送 CTRL_BREAK_EVENT 信号停止录制
    if recording_process:
        recording_process.send_signal(signal.CTRL_BREAK_EVENT)
        # 超时未停止进程则强行终止
        try:
            recording_process.wait(RECORDING_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            recording_process.kill()

    # 停止系统托盘图标
    icon.stop()


def interrupt_start():
    win_ui.show_popup(_t("tray_text_already_run"), "Windrecorder is already running.", "information")
    sys.exit()


def interrupt_start_no_ffmpeg_and_ffprobe(reason):
    win_ui.show_popup(reason, "Missing dependencies", "information")
    sys.exit()


def hide_cli_window():
    # 隐藏该 CLI 窗口
    subprocess.run("cls", shell=True)
    print()

    timeout_count = 10
    for i in range(timeout_count):
        print(f"   Trying to hide CLI window... ({i}/{timeout_count})")
        title = str(pygetwindow.getActiveWindowTitle())
        if "Windrecorder" in title:
            hide_CLI = win32gui.GetForegroundWindow()
            win32gui.ShowWindow(hide_CLI, win32con.SW_HIDE)
            break
        time.sleep(1)
    print("\n   Hide CLI window fail. Please minimize this window manually.")


def main():
    # 启动时加锁，防止重复启动
    while True:
        try:
            tray_lock = FileLock(config.tray_lock_path, str(getpid()), timeout_s=None)
            break
        except LockExistsException:
            with open(config.tray_lock_path, encoding="utf-8") as f:
                check_pid = int(f.read())

            tray_is_running = utils.is_process_running(check_pid, compare_process_name="python.exe")
            if tray_is_running:
                interrupt_start()
            else:
                try:
                    os.remove(config.tray_lock_path)
                except FileNotFoundError:
                    pass

    with tray_lock:
        thread_hide_cli_window = threading.Thread(target=hide_cli_window)
        thread_hide_cli_window.start()

        ff_available, ff_callback = utils.check_ffmpeg_and_ffprobe()
        if not ff_available:
            interrupt_start_no_ffmpeg_and_ffprobe(ff_callback)

        credential_path = get_streamlit_file_path("credentials.toml")
        if not os.path.exists(credential_path):
            os.makedirs(os.path.dirname(credential_path), exist_ok=True)
            shutil.copyfile(os.path.join(PROJECT_ROOT, ".streamlit\\credentials.toml"), credential_path)

        tray_icon_init = get_tray_icon(state="record_pause")
        tray_title_init = _t("tray_tip_record_pause")
        if config.start_recording_on_startup:
            start_stop_recording()
            tray_icon_init = get_tray_icon(state="recording")
            tray_title_init = _t("tray_tip_record")

        pystray.Icon(
            "Windrecorder",
            tray_icon_init,
            title=tray_title_init,
            menu=pystray.Menu(menu_callback),
        ).run(setup=setup)


if __name__ == "__main__":
    main()
