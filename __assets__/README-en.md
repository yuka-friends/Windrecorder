![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Memory Cue Search Engine</h1>
<p align="center"> An Open Source <a href="https://www.rewind.ai/">Rewind</a>’s alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">简体中文</a> | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---

This is a tool that can continuously record screen images and retrieve relevant memories at any time through keyword searches and other methods.

**All its capabilities (recording, recognition processing, storage traceback, etc.) run completely locally, without the need for an Internet connection, without uploading any data, and only do what should be done. **

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)

> [!WARNING]
>
> 🤯 This project is still in the early stages of development, and you may encounter some minor problems in experience and use. If you encounter it, you are welcome to submit issue feedback and pay attention to updates.

# 🦝 Installation

## Automatic installation (not ready)

Download the integration package from [Releases](https://github.com/yuka-friends/Windrecorder/releases), unzip it to the directory where you want to store the data and use it.


## Manual installation

- Download [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) and extract ffmpeg.exe in the bin directory to `C:\Windows\System32` ( or other directories located in PATH)

- Install [Git](https://git-scm.com/downloads), [Python](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe ) (check Add python.exe to PATH during installation), [Pip](https://pip.pypa.io/en/stable/installation/);
     - **Notice! Currently, python 3.12** is not supported. It is recommended to use python 3.10, which is the version pointed to by the link above.

- Navigate to the directory where you want to install this tool (it is recommended to place it in a partition with sufficient space), and download the tool through the terminal command `git clone https://github.com/yuka-friends/Windrecorder`;

     - You can open the folder you want to install, enter `cmd` in the path bar and press Enter, enter the current directory terminal, paste the above command and press Enter to execute;

- Open `install_update_setting.bat` in the directory to install and configure the tool. If everything goes well, you can start using it!

     - If an error is reported due to network reasons, you can add proxy `set https_proxy=http://127.0.0.1:xxxx` or add mainland [mirror source] (https://mirrors.tuna.tsinghua.edu. cn/help/pypi/);


# 🦝 How to use

Currently, you need to open the batch script in the directory to use the tool:

- Start recording the screen by opening `start_record.bat` in the directory;

> Note: You need to keep the terminal window minimized and run in the background to record. Likewise, simply close the terminal window when you need to pause recording.

- Open `start_webui.bat` in the directory to trace back, query memory, and make settings;

> Best practice: Set `start_record.bat` to start automatically at boot in the webui, so that everything can be recorded without any fuss. When the computer is idle and no one is using it, `start_record.bat` will automatically pause recording, compress and clean up expired videos; Just set it and forget it!

---
### Roadmap:
- [x] Stable and continuous screen recording with smaller file size
- [x] Only identify changed pictures and store the index in the database
- [x] Complete graphical interface (webui)
- [x] Data summary of word cloud, timeline, light box, scatter plot
- [x] Automatically identify clips after recording, and automatically maintain, clean and compress videos in your spare time
- [x] Multi-language support: i18n support for interface and OCR recognition completed
- [ ] Refactor the code to make it more standardized, easier to develop, and have better performance
- [ ] Packaging tools, providing a more convenient usage mode, making it user-friendly
- [ ] Add recognition of screen modalities to enable search for screen content descriptions
- [ ] Add database encryption function
- [ ] Record the foreground process name and record the corresponding position of the OCR word to present it as a clue during search
- [ ] Add word embedding index, local/API LLM query
- [ ] Add multi-screen recording support (depends on future features of pyautogui)
- [ ] 🤔


# 🦝 Q&A | Frequently Asked Questions
Q: There is no data in the recent period when opening webui.

- A: When start_record.bat is indexing data, webui will not create the latest temporary database file. You can delete the database file with the suffix _TEMP_READ.db in the db directory and refresh it after start_record.bat is indexed. This strategy will be fixed and refactored in the future. [#26](https://github.com/yuka-friends/Windrecorder/issues/26)

Q: When opening webui, it prompts: `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'`

- A: Usually occurs when the webui is accessed for the first time, while start_record.bat is still indexing data.
Solution: After the start_record.bat background indexing is completed, delete the corresponding database file with the suffix _TEMP_READ.db in the db folder and refresh it.

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