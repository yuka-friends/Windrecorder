![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder</h1>
<p align="center"> An Open Source Rewind’s alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> English  | <a href="https://github.com/Antonoko/Windrecorder/blob/main/README.md">简体中文</a> | <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---
> What is Rewind App?: https://www.rewind.ai/

**⚠️ The Windows.Media.Ocr.Cli currently included in the tool is only compiled for the Chinese language, which will cause OCR recognition to be unavailable under pure English systems. This blocking problem is still waiting for an update to be fixed.**

This is a tool that continuously records your screen and allows you to retrieve relevant memories anytime using keyword search and other methods.

**All its capabilities (recording, recognition processing, storage, and retrieval) run entirely locally without the need for an internet connection. It does not upload any data. It simply does what it is supposed to do.**

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)


# 🦝 Installation

- Download [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) and extract the ffmpeg.exe file from the bin directory to `C:\Windows\System32` (or any other directory in the PATH environment variable).

- Make sure you have installed [Git](https://git-scm.com/downloads), [Python](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe) (select "Add python.exe to PATH" during installation), and [Pip](https://pip.pypa.io/en/stable/installation/).

- Navigate to the directory where you want to install the tool and download it using the command `git clone https://github.com/Antonoko/Windrecorder`.

    - You can open the desired installation folder, enter `cmd` in the path bar, and press Enter to open a terminal in the current directory. Paste the above command and press Enter to execute it.

- Open the directory and run `install_update_setting.bat` to install and configure the tool. If everything goes smoothly, you can start using it!

- Use `start_record.bat` to start screen recording and `start_webui.bat` to query, search, and configure.

---
### Roadmap:
- [x] Continuously record the screen with smaller file size
- [x] Only recognize and store index for changed frames in the database
- [x] Improved graphical user interface (webui)
- [x] Summarize data in word clouds, timelines, lightboxes, and scatter plots
- [x] Automatically recognize and maintain/clean/compress videos after recording segments
- [ ] Multi-language support: Completed i18n support for the interface. Todo: Compile support for English/Japanese environment of Windows.Media.Ocr.Cli
- [ ] Optimize workflow and improve performance
- [ ] Add support for recording multiple screens (depends on future features of pyautogui)
- [ ] Add visual recognition for searching descriptions of screen content
- [ ] Add word embedding index and local LLM query
- [ ] 🤔


# 🦝 Q&A | Frequently Asked Questions
Q: When opening webui, I get the following error: FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'

- A: This usually occurs when accessing webui for the first time while start_record.bat is still indexing data. Solution: After start_record.bat finishes indexing in the background, delete the database file with the suffix _TEMP_READ.db in the db folder and refresh the page.

Q: Mouse flickering during recording

- A: This is a legacy issue with Windows. You can try the method mentioned in [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg) to resolve it. 🤔

Q: When results are in the same video, dragging the slider does not automatically jump to the corresponding time.

- A: This is a bug in streamlit [#7126](https://github.com/streamlit/streamlit/issues/7126) and will be fixed in the future.

Q: Low recognition rate for Windows.Media.Ocr.Cli OCR

- A: Check if you have added language packs/input methods for the target language in your system: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr/ocrresult#remarks


# 🧡
Help from these projects has been enlisted:

- [https://github.com/DayBreak-u/chineseocr_lite](https://github.com/DayBreak-u/chineseocr_lite)

- [https://github.com/zh-h/Windows.Media.Ocr.Cli](https://github.com/zh-h/Windows.Media.Ocr.Cli)


---

Like this tool? Feel free to enjoy the soothing music of [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) on YouTube and streaming music platforms. Thank you!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
