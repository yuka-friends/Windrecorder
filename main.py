import re
import sys
import time
import webbrowser
from subprocess import Popen
from typing import Optional

import pystray
import requests
from PIL import Image

from windrecorder import file_utils, utils
from windrecorder.utils import get_text as _t

STREAMLIT_URL_REGEX = re.compile("Local URL: (.+)")
streamlit_process: Optional[Popen] = None
webui_url = ""
STREAMLIT_OPEN_TIMEOUT = 10


def get_tray_icon():
    image = Image.open("__assets__\\icon-tray.png")
    image = image.convert("RGBA")
    return image


def update():
    pass


file_utils.check_and_create_folder("cache")


def startStopWebui(icon: pystray.Icon, item: pystray.MenuItem):
    global streamlit_process, webui_url
    if streamlit_process:
        streamlit_process.kill()
        streamlit_process = None
    else:
        with open("cache\\streamlit.log", "w") as out, open("cache\\streamlit.err", "w") as err:
            streamlit_process = Popen(
                [sys.executable, "-m", "streamlit", "run", "webui.py"], stdout=out, stderr=err, encoding="utf-8"
            )
        time_spent = 0
        while time_spent < STREAMLIT_OPEN_TIMEOUT:
            with open("cache\\streamlit.log", "r") as f:
                m = STREAMLIT_URL_REGEX.search(f.read())
            if m:
                webui_url = m[1]
                break
            time.sleep(1)
            time_spent += 1
        else:
            streamlit_process.kill()
            streamlit_process = None
            icon.notify(f"Streamlit takes more than {STREAMLIT_OPEN_TIMEOUT} seconds to launch!")


recording_running = False


def startStopRecording(icon: pystray.Icon, item: pystray.MenuItem):
    global recording_running
    recording_running = not recording_running


def openWebui(icon: pystray.Icon, item: pystray.MenuItem):
    webbrowser.open(webui_url)


def setup(icon: pystray.Icon):
    icon.visible = True
    icon.notify(message=_t("tray_notify_text"), title=_t("tray_notify_title"))


def menuCallback():
    try:
        new_version = utils.get_new_version_if_available()
    except requests.ConnectionError:
        new_version = None
    current_version = utils.get_current_version()

    return (
        pystray.MenuItem(lambda item: _t("tray_webui_exit") if streamlit_process else _t("tray_webui_start"), startStopWebui),
        pystray.MenuItem(
            lambda item: _t("tray_webui_address").format(address_port=webui_url),
            openWebui,
            visible=lambda item: streamlit_process,
            default=True,
        ),
        pystray.MenuItem(
            lambda item: _t("tray_record_stop") if recording_running else _t("tray_record_start"), startStopRecording
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
        pystray.MenuItem(_t("tray_exit"), lambda icon, item: icon.stop()),
    )


def main():
    # In order for the icon to be displayed, you must provide an icon
    pystray.Icon(
        "Windrecorder",
        get_tray_icon(),
        menu=pystray.Menu(menuCallback),
    ).run(setup=setup)


if __name__ == "__main__":
    main()
