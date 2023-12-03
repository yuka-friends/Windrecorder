import os
import re
import signal
import subprocess
import sys
import time
import webbrowser
from subprocess import Popen

import pystray
import requests
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
os.chdir(PROJECT_ROOT)

from windrecorder import file_utils, utils  # NOQA: E402
from windrecorder.config import config  # NOQA: E402
from windrecorder.utils import get_text as _t  # NOQA: E402

WEBUI_STDOUT_PATH = os.path.join(config.log_dir, "webui.log")
WEBUI_STDERR_PATH = os.path.join(config.log_dir, "webui.err")
RECORDING_STDOUT_PATH = os.path.join(config.log_dir, "recording.log")
RECORDING_STDERR_PATH = os.path.join(config.log_dir, "recording.err")

STREAMLIT_URL_REGEX = re.compile("Local URL: (.+)")
STREAMLIT_OPEN_TIMEOUT = 10
RECORDING_STOP_TIMEOUT = 5

streamlit_process: Popen | None = None
recording_process: Popen | None = None
webui_url = ""


def get_tray_icon():
    image = Image.open("__assets__\\icon-tray.png")
    image = image.convert("RGBA")
    return image


def update():
    pass


file_utils.ensure_dir("cache")
file_utils.ensure_dir(config.log_dir)


def open_webui(icon: pystray.Icon, item: pystray.MenuItem):
    webbrowser.open(webui_url)


def setup(icon: pystray.Icon):
    icon.visible = True
    if config.start_recording_on_startup:
        start_stop_recording(icon)
    icon.notify(message=_t("tray_notify_text"), title=_t("tray_notify_title"))


def start_stop_webui(icon: pystray.Icon, item: pystray.MenuItem):
    global streamlit_process, webui_url
    if streamlit_process:
        streamlit_process.kill()
        streamlit_process = None
    else:
        with open(WEBUI_STDOUT_PATH, "w", encoding="utf-8") as out, open(WEBUI_STDERR_PATH, "w", encoding="utf-8") as err:
            streamlit_process = Popen(
                [sys.executable, "-m", "streamlit", "run", "webui.py"],
                stdout=out,
                stderr=err,
                encoding="utf-8",
                cwd=PROJECT_ROOT,
            )
        time_spent = 0
        while time_spent < STREAMLIT_OPEN_TIMEOUT:
            with open(WEBUI_STDOUT_PATH, "r", encoding="utf-8") as f:
                m = STREAMLIT_URL_REGEX.search(f.read())
            if m:
                webui_url = m[1]
                break
            time.sleep(1)
            time_spent += 1
        else:
            streamlit_process.kill()
            streamlit_process = None
            icon.notify(f"Webui takes more than {STREAMLIT_OPEN_TIMEOUT} seconds to launch!")


def start_stop_recording(icon: pystray.Icon, item: pystray.MenuItem | None = None):
    global recording_process
    if recording_process:
        recording_process.send_signal(signal.CTRL_BREAK_EVENT)
        try:
            recording_process.wait(RECORDING_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            icon.notify("Failed to exit the recording service gracefully. Killing it.")
            recording_process.kill()
        recording_process = None
    else:
        with open(RECORDING_STDOUT_PATH, "w", encoding="utf-8") as out, open(
            RECORDING_STDERR_PATH, "w", encoding="utf-8"
        ) as err:
            recording_process = Popen(
                [sys.executable, "record_screen.py"],
                stdout=out,
                stderr=err,
                encoding="utf-8",
                cwd=PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )


def menu_callback():
    try:
        new_version = utils.get_new_version_if_available()
    except requests.ConnectionError:
        new_version = None
    current_version = utils.get_current_version()

    return (
        pystray.MenuItem(
            lambda item: _t("tray_webui_exit") if streamlit_process else _t("tray_webui_start"), start_stop_webui
        ),
        pystray.MenuItem(
            lambda item: _t("tray_webui_address").format(address_port=webui_url),
            open_webui,
            visible=lambda item: streamlit_process,
            default=True,
        ),
        pystray.MenuItem(
            lambda item: _t("tray_record_stop") if recording_process else _t("tray_record_start"), start_stop_recording
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda item: (
                _t("tray_update_cta").format(version=new_version)
                if new_version is not None
                else _t("tray_version_info").format(version=current_version)
            ),
            update,
            enabled=lambda item: new_version is not None,
        ),
        pystray.MenuItem(_t("tray_exit"), on_exit),
    )


def on_exit(icon: pystray.Icon, item: pystray.MenuItem):
    if streamlit_process:
        streamlit_process.kill()
    if recording_process:
        recording_process.send_signal(signal.CTRL_BREAK_EVENT)
        try:
            recording_process.wait(RECORDING_STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            recording_process.kill()
    icon.stop()


def main():
    pystray.Icon(
        "Windrecorder",
        get_tray_icon(),
        menu=pystray.Menu(menu_callback),
    ).run(setup=setup)


if __name__ == "__main__":
    main()
