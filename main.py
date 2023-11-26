import pystray
from PIL import Image, ImageDraw


def create_image(width, height, color1, color2):
    # Generate an image and draw a pattern
    image = Image.new("RGB", (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
    dc.rectangle((0, height // 2, width // 2, height), fill=color2)

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
    icon.notify("I'm up")


def main():
    # In order for the icon to be displayed, you must provide an icon
    pystray.Icon(
        "Windrecorder",
        create_image(64, 64, "black", "white"),
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: "close webui" if webui_running else "open webui", openCloseWebui),
            pystray.MenuItem(
                "goto localhost:8901", openWebui, visible=lambda item: webui_running, enabled=False, default=True
            ),
            pystray.MenuItem(lambda item: "stop recording" if recording_running else "start recording", startStopRecording),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(lambda item: "update" if checkUpdate() else "latest", update, enabled=lambda item: checkUpdate()),
            pystray.MenuItem("exit", lambda icon, item: icon.stop()),
        ),
    ).run(setup=setup)


if __name__ == "__main__":
    main()
