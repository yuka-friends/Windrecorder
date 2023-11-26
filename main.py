import pystray
from PIL import Image, ImageDraw

from windrecorder.utils import get_text as _t


def create_pattern_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image


def get_tray_icon():
    image = Image.open("__assets__\\icon-tray.png")
    image = image.convert("RGBA")
    return image


def checkUpdate():
    return False


def update():
    pass


webui_running = False


def openCloseWebui(icon: pystray.Icon, item: pystray.MenuItem):
    global webui_running
    webui_running = not webui_running


recording_running = False


def startStopRecording(icon: pystray.Icon, item: pystray.MenuItem):
    global recording_running
    recording_running = not recording_running


def openWebui(icon: pystray.Icon, item: pystray.MenuItem):
    pass


def setup(icon: pystray.Icon):
    icon.visible = True
    icon.notify(message=_t("tray_notify_text"), title=_t("tray_notify_title"))


def main():
    # In order for the icon to be displayed, you must provide an icon
    pystray.Icon(
        "Windrecorder",
        get_tray_icon(),
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: _t("tray_webui_exit") if webui_running else _t("tray_webui_start"), openCloseWebui),
            pystray.MenuItem(
                _t("tray_webui_address").format(address_port="地址+端口占位符"),
                openWebui,
                visible=lambda item: webui_running,
                enabled=False,
                default=True,
            ),
            pystray.MenuItem(
                lambda item: _t("tray_record_stop") if recording_running else _t("tray_record_start"), startStopRecording
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: _t("tray_update_cta").format(version="版本信息占位符")
                if checkUpdate()
                else _t("tray_version_info").format(version="版本信息占位符"),
                update,
                enabled=lambda item: checkUpdate(),
            ),
            pystray.MenuItem(_t("tray_exit"), lambda icon, item: icon.stop()),
        ),
    ).run(setup=setup)


if __name__ == "__main__":
    main()
