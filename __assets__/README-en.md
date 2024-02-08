![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Personal Memory Search Engine</h1>
<p align="center"> An Open Source Mac App <a href="https://www.rewind.ai/">Rewind</a>’s alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">简体中文</a></p>

---

This is a tool that can continuously record screen images and retrieve relevant memories at any time through keyword searches and other methods.

**All its capabilities (recording, recognition processing, storage, rewind, etc.) run completely locally, without the need for an Internet connection, without uploading any data, and only do what should be done. **

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-en.jpg)

**Windrecorder currently does:**
- Record the screen stably and continuously with a smaller file size. Only index the changed scenes and update the OCR text, page title and other information to the database; automatically maintain the database, clean and compress the video when no one is using the computer;
- Complete webui interface, which can review the screen, conduct OCR/image semantics and other queries;
- Provide data summaries such as activity statistics, word clouds, timelines, light boxes, scatter plots, etc.;
- Supports multiple languages. Currently built-in: Simplified Chinese, English, and Japanese. Welcome to contribute multilingual translations and help us improve copywriting quality.
- _coming soon... pay attention to our PR :)_

---

> [!WARNING]
> This project is still in the early stages of development, and you may encounter some minor problems in experience and use. If you encounter it, you are welcome to submit issue feedback, follow updates, and initiate discussions in the [Discussions discussion area](https://github.com/yuka-friends/Windrecorder/discussions).
>
> 🤯 **If you are good at Python/client front-end direction and are interested in the project, you are welcome to submit an issue/PR/PR review to participate in the construction, in [Dissuasions](https://github.com/yuka-friends/Windrecorder /discussions) Check out the Roadmap and discussions! **

> [!IMPORTANT]
> Due to minor coding errors, versions prior to `0.0.5` may not be able to detect updates properly or upgrade through install_update.bat. If so, please enter `cmd` in the path box of the `Windrecorder` root directory to open the command line, and enter `git pull` to update. 🙇‍♀️

# 🦝 Installation

- Download [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) and extract `ffmpeg.exe` and `ffprobe.exe` in the bin directory to `C :\Windows\System32` (or other directories located in PATH)

- Install [Git](https://git-scm.com/download/win) and just take the next step;

- Install [Python](https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe), make sure to check `Add python.exe to PATH` when installing
     - **Notice! Currently, python 3.12** is not supported. It is recommended to use python 3.11, which is the version pointed to by the link above.

- In the file manager, navigate to the directory where you want to install this tool (it is recommended to place it in a partition with sufficient space), and download the tool through the terminal command `git clone https://github.com/yuka-friends/Windrecorder`;

     - You can open the folder you want to install, enter `cmd` in the path bar and press Enter, you can locate the current directory in the terminal, paste the above command and press Enter to execute;

- Open `install_update.bat` in the directory to install and configure the tool. If everything goes well, you can start using it!


# 🦝 How to use

- Open `start_app.bat` in the directory, the tool will run in the system tray and be used through the right-click menu;
- All data (video, database, statistical information) will be stored in the same directory as Windrecorder. If you want to copy or move the tool location (for example, if you change the computer), you only need to delete `.venv` in the directory after the move, and re-run `install_update.bat` to install the virtual environment and use it;

> [!TIP]
> Best practice: Set up auto-start in webui to record everything without any fuss.
>
> **Recording will be automatically paused when there is no change in the picture or the screen is sleeping. When the computer is idle and no one is using it, the tool will automatically maintain the database, compress, and clean up expired videos. **
>
> _Just set it and forget it! _


# 🦝 How it works
![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/how-it-work-sc.jpg)

When recording is started, the Wind Capture Recorder will record 15 minutes of video segment by segment, and the video segments will be indexed after the recording is completed (therefore, there may be a 15-minute delay in querying the data). When the screen does not change or the computer enters the lock screen, recording will be automatically paused and idle maintenance will be performed (compressing and cleaning videos, image embedding recognition, etc.) until the user comes back and continues to operate the computer.

| Video recording size                                                                                                                | SQlite database size (month) |
|-------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| Per Hour: 2~100 Mb (depends on screen change\number of monitors)                                                                    | About 160 Mb                 |
| Per Month: 10~20 Gb (depends on screen time)  Different video compression presets can compress these data to 0.1~0.7 times the size |                              |

> In the future, the recording method may be improved to reduce ffmpeg usage and eliminate the need to wait for traceback.


# 🦝 Q&A | Frequently Asked Questions

Q: Failed to open webui from tray

- A: It may be a bug caused by streamlit triggering mailbox collection when it is first started. You can execute the following command on the command line in the directory and press Enter to skip the mailbox collection during the first run. After closing the command line, you can use it normally.
```
poetry shell
streamlit run webui.py
```

Q: There is no data in the recent period when opening webui.

- A: When the tool is indexing data, webui will not create the latest temporary database file.
Solution: Try to wait for a while, wait for the tool indexing to complete, refresh the webui interface, or delete the database file with the suffix _TEMP_READ.db in the db directory and refresh it (if there is a database file damage prompt, don’t worry, it may be The tool is still in the index, please try refreshing/removing it after some time). This strategy will be fixed and refactored in the future. [#26](https://github.com/yuka-friends/Windrecorder/issues/26)

Q: When opening webui, it prompts: `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'`

- A: Usually occurs when accessing the webui for the first time, while the tool is still indexing data.
Solution: After the tool background indexing is completed, delete the corresponding database file with the suffix _TEMP_READ.db in the db folder and refresh it.

Q: The mouse flashes during recording

- A: Windows historical issues, you can try [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg ) method to solve🤔. (IMO it might okay if you get used to it and don’t care about it

Q: Windows.Media.Ocr.Cli OCR is not available/the recognition rate is too low

- A1: Check whether the language pack/input method of the target language has been added to the system: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr

- A2: The default policy of earlier versions will treat screen resolutions with a height greater than 1500 as "high DPI/high resolution screens", and their recorded video resolution will be reduced to a quarter of the original. For example, on a 3840x2160 4k monitor, the resolution of the recorded video will be 1920x1080, which may lead to a decrease in OCR recognition accuracy. If you use smaller fonts or scaling on a high-resolution screen, you can turn off this option in Recording and Video Storage, and set the number of days to keep the original video before compressing it to a smaller value. value, thereby compressing the video volume some time after the video OCR index.

- A3: Windows.Media.Ocr.Cli may have poor recognition rate for smaller text. You can improve the recall hit rate during search by turning on the "similar glyph search" option in the settings.

# 🧡
Help has been introduced for these projects:

- https://github.com/DayBreak-u/chineseocr_lite

- https://github.com/zh-h/Windows.Media.Ocr.Cli


---

🧡 Like this tool? Welcome to Youtube and streaming music platforms to listen to [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) gentle music, thank you!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing