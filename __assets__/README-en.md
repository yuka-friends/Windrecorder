![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Memory Cue Search Engine</h1>
<p align="center"> An Open Source <a href="https://www.rewind.ai/">Rewind</a>’s alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">简体中文</a> | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---

This is a tool that can continuously record screen images and retrieve relevant memories at any time through keyword searches and other methods.

**All its capabilities (recording, recognition processing, storage traceback, etc.) run completely locally, without the need for an Internet connection, without uploading any data, and only do what should be done. **

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)

**Windrecorder currently does:**
- Record the screen stably and continuously with a smaller file size, only index changed pictures, and update the pictures and OCR content to the database; automatically maintain, clean and compress video files in your spare time;
- It has a complete webui interface, which can perform screen retrieval and OCR text query; provides data summary of word cloud, timeline, light box, and scatter plot; supports multiple languages;
- Features under construction: simplified installation process, multi-screen support, screen semantic search, database encryption, word embedding index and LLM query, more complete query experience interface...

---

> [!WARNING]
> This project is still in the early stages of development, and you may encounter some minor problems in experience and use. If you encounter it, you are welcome to submit issue feedback, follow updates, and initiate discussions in the [Discussions discussion area](https://github.com/yuka-friends/Windrecorder/discussions).
>
> 🤯 **If you are good at Python / client front-end direction and are interested in the project, you are welcome to participate in the construction by raising an issue / PR / PR review at [Dissuasions](https://github.com/yuka-friends /Windrecorder/discussions) Check out the Roadmap and discussions! **

> [!IMPORTANT]
> The project is adding functions and making architectural changes, which may cause problems such as users of earlier versions being unable to upgrade and update normally.
> Don't worry! Bring your own `videos`, `db`, `config\config_user.json` and other directories and files, and you can migrate to the latest version at any time.

## 🦝🎉 0.1.0 What's new (coming soon)

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-update-0.1.0.jpg)

- Now that we have integrated the tool into the system tray and will release a ready-to-run integration package, Wind Recorder will be more intuitive and easier to use than ever before. Say goodbye to complicated manual installation, `start_record.bat` & `start_webui.bat`! 👋
- Added time mark function: When you want to mark important meetings, emergencies, live broadcasts, gaming and movie-watching highlights, etc. to facilitate future review, you can mark the present moment through the tray, or you can Add records of important events when reviewing;
- Added more format and parameter support for compressed video;
- Refactored a large number of code structures, fixed some bugs and improved performance;
- For more upgrades and changes, please check the [Update Log](https://github.com/yuka-friends/Windrecorder/blob/main/CHANGELOG.md)


If you've been using a windlogger before, thank you! You can update to the latest version through the following methods:

- Method A: Download the integration package from [Releases](https://github.com/yuka-friends/Windrecorder/releases) and unzip it, then:
     - Create a new `userdata` folder in the tool directory, and move the original `videos`, `db`, `result_lightbox`, `result_timeline`, `result_wordcloud` folders to `userdata`;
     - Move the original `config\config_user.json` file to the `userdata` folder;
     - Open `windrecorder.exe` to use 🎉
- Method B: Execute `git pull` in the directory, and then open `install_update_setting.bat` to upgrade;


# 🦝 First time installation

## Automatic installation (almost ready)

Download the integration package from [Releases](https://github.com/yuka-friends/Windrecorder/releases), unzip it to the directory where you want to store the data, open `windrecorder.exe` and start using it.


## Manual installation

- Download [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) and extract ffmpeg.exe & ffprobe.exe in the bin directory to `C:\Windows\System32` ( or other directories located in PATH)

- Install [Git](https://git-scm.com/downloads), [Python](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe ) (check Add python.exe to PATH during installation), [Pip](https://pip.pypa.io/en/stable/installation/);
     - **Notice! Currently, python 3.12** is not supported. It is recommended to use python 3.10, which is the version pointed to by the link above.

- Navigate to the directory where you want to install this tool (it is recommended to place it in a partition with sufficient space), and download the tool through the terminal command `git clone https://github.com/yuka-friends/Windrecorder`;

     - You can open the folder you want to install, enter `cmd` in the path bar and press Enter, enter the current directory terminal, paste the above command and press Enter to execute;

- Open `install_update.bat` in the directory to install and configure the tool. If everything goes well, you can start using it!

     - If an error is reported due to network reasons, you can add proxy `set https_proxy=http://127.0.0.1:xxxx` or add mainland [mirror source] (https://mirrors.tuna.tsinghua.edu. cn/help/pypi/);


# 🦝 How to use

Currently, you need to open the batch script in the directory to use the tool:

- Start recording the screen by opening `start_app.bat` in the directory;

> Note: You need to keep the terminal window minimized and run in the background to record. Likewise, simply close the terminal window when you need to pause recording.

> Best practice: Set auto-start in webui to record everything without any fuss. Recording will be automatically paused when there is no change in the picture or the screen is in sleep mode. When the computer is idle and no one is using it, the tool will automatically maintain the database, compress, and clean up expired videos; Just set it and forget it!


# 🦝 How it works
![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/how-it-work-en.jpg)

When recording is started, the Wind Capture Recorder will record 15 minutes of video segment by segment, and OCR index the video segments after the recording is completed (therefore, there may be a 15-minute delay in querying the data). When the screen does not change or the computer enters the lock screen, recording will be automatically paused and idle maintenance will be performed, including compressing and cleaning videos, image embedding and recognition, etc., until the user comes back to continue operating the computer.

> In the future, the recording method may be improved to reduce ffmpeg usage and eliminate the need to wait for traceback.


# 🦝 Q&A | Frequently Asked Questions
Q: There is no data in the recent period when opening webui.

- A: When the tool is indexing data, webui will not create the latest temporary database file.
Solution: Try to wait for a while, wait for the tool index to be completed, refresh the webui interface, or delete the database file with the suffix _TEMP_READ.db in the db directory and refresh it (if there is a database file damage prompt, don’t worry, it may be The tool is still in the index, please try refreshing/removing it after some time). This strategy will be fixed and refactored in the future. [#26](https://github.com/yuka-friends/Windrecorder/issues/26)

Q: When opening webui, it prompts: `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'`

- A: Usually occurs when accessing the webui for the first time, while the tool is still indexing data.
Solution: After the tool background indexing is completed, delete the corresponding database file with the suffix _TEMP_READ.db in the db folder and refresh it.

Q: The mouse flashes during recording

- A: For issues left over from Windows history, you can try [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg ) method to solve🤔. (Actually, it’s okay if you get used to it and don’t care about it (escape)

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