![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Memory Cue Retriever</h1>
<p align="center"> An Open Source alternative tool on Windows to retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/Antonoko/Windrecorder/blob/main/README.md">简体中文</a> | <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---
> What is Rewind App?: https://www.rewind.ai/

It is a tool that continuously records screen footage and helps you retrieve relevant memory cues through keyword search and other methods.

**All its functionalities (recording, recognition processing, storage, and retrieval) run completely locally, without the need for internet connection. It does not upload any data and only focuses on its intended purpose.**

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)


# 🦝 Installation

- Download [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) and extract the ffmpeg.exe file from the bin directory to `C:\Windows\System32` (or any other directory in the PATH).

- Install [Git](https://git-scm.com/downloads), [Python](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe) (select "Add python.exe to PATH" during installation), and [Pip](https://pip.pypa.io/en/stable/installation/).

- Navigate to the directory where you want to install this tool (preferably in a partition with sufficient space) and download the tool using the terminal command `git clone https://github.com/Antonoko/Windrecorder`.

    - You can open the desired installation folder, enter `cmd` in the address bar, and press Enter to open the command prompt in the current directory. Then paste the above command and press Enter to execute it.

- Open the directory and run `install_update_setting.bat` to install and configure the tool. If everything goes well, you can start using it!



# 🦝 How to Use

- Run `start_record.bat` in the directory to start recording the screen.

> Note: Keep the terminal window minimized and running in the background to continue recording. Similarly, you can pause the recording by simply closing the terminal window.

- Run `start_webui.bat` in the directory to access the web interface for browsing, searching memories, and making settings.

> Best practice: Set `start_record.bat` to launch at startup using the web UI. It will silently record everything. When the computer is idle and not in use, `start_record.bat` will automatically pause the recording, compress, and clean up expired videos. Just set it and forget it!

---
### Roadmap:
- [x] Stable continuous screen recording with smaller file size
- [x] Only recognize and store indexed frames that have changed in the database
- [x] Well-designed graphical user interface (web UI)
- [x] Data summarization with word clouds, timelines, lightboxes, and scatter plots
- [x] Automatic identification, maintenance, cleaning, and compression of recorded segments
- [x] Multilingual support: Completed i18n support for the interface and OCR recognition.
- [ ] Process optimization for improved performance
- [ ] Add database encryption feature
- [ ] Record foreground process names and associate them with recognized OCR words to present as cues during search
- [ ] Add support for recording multiple screens (depending on future features of pyautogui)
- [ ] Implement modal recognition for describing visual content in search
- [ ] Add word embedding indexing and local LLM queries
- [ ] 🤔


# 🦝 Q&A

Q: Got `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'` when launching webui

- A: This usually happens when launching webui for the first time or start_record.bat is still indexing.  
Fix by deleting db files with suffix _TEMP_READ.db after start_record.bat done indexing in background, and refresh page.

Q: Mouse flickers during recording  

- A: A Windows legacy issue, try fixes in [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg). Or just ignore it while you getting used to it :p

Q: Windows.Media.Ocr.Cli OCR not working / low recognition rate

- A: Check if target language language packs/input methods are installed: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr

# 🧡
Powered by these amazing projects:

- [https://github.com/DayBreak-u/chineseocr_lite](https://github.com/DayBreak-u/chineseocr_lite)

- [https://github.com/zh-h/Windows.Media.Ocr.Cli](https://github.com/zh-h/Windows.Media.Ocr.Cli)


---

🧡 Like this tool? Feel free to enjoy the soothing music of [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) on YouTube and streaming music platforms. Thank you!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
