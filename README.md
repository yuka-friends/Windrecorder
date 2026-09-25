![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Personal Memory Search Engine</h1>
<p align="center"> An Open Source Mac App <a href="https://www.rewind.ai/">Rewind</a> / Copilot Recall alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-sc.md">简体中文</a></p>

---

Windrecorder is a memory search app by records everything on your screen in small size, to let you rewind what you have seen, query through OCR text or image description, and get activity statistics. All its capabilities run completely locally, without the need for an Internet connection or uploading any data, you should own all your data.

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-en.jpg)

**Windrecorder currently does:**
- Record multiple or single screens, or just the active window, with smaller file sizes and lower system resources, ensuring stable, continuous capture and the ability to rewind live footage;
- Only index the changed scenes and update the OCR text, page title, browser url and other information to the database; Custom skip conditions (by window title, process name, included text, or screen still time); Automatically maintain the database, clean and compress the video when no one is using the computer;
- Complete webui interface, which can review the screen, conduct OCR/image semantics and other queries;
- Provide data summaries such as activity statistics, word clouds, timelines, light boxes, scatter plots, etc.; Supports tags summarization using AI (LLM).
- Supports multiple languages. Currently built-in: Simplified Chinese, English, and Japanese. Welcome to contribute multilingual translations and help us improve copywriting quality;
- In addition to Windows' built-in recognition capabilities, it also supports other third-party OCR engines ([performance test reference](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/third_party_ocr_engine_benchmark_reference.md)), currently including:
     - [Rapid OCR](https://github.com/RapidAI/RapidOCR), based onnxruntime version of Paddle OCR;
     - [WeChat OCR](https://github.com/kanadeblisst00/wechat_ocr), with extremely high Chinese and English recognition accuracy;
     - [Tesseract OCR](https://github.com/tesseract-ocr/tessdoc), supports more than 100 languages ​​and can recognize multiple languages ​​at the same time;
     - [Contribute custom OCR](https://github.com/yuka-friends/Windrecorder/blob/main/extension/how_to_contribute_third_party_ocr_support.md)
- _coming soon... pay attention to our PR :)_

---

> [!IMPORTANT]
> If automatic updates fail, close Windrecorder, open `cmd` in the Windrecorder root directory, run `git pull --ff-only`, then reopen `install_update.bat`. See [upgrade and recovery](docs/upgrading.md) if Git reports a conflict.

# 🦝 Installation

- Download [ffmpeg](https://github.com/BtbN/FFmpeg-Builds/releases) (the download file name is: `ffmpeg-master-latest-win64-gpl-shared.zip`), extract all files in `bin` directory(excluding the bin directory itself) to `C:\Windows\System32` (or other directories located in PATH)

- Install [Git](https://git-scm.com/download/win), just keep clicking next step.

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/). The installer automatically manages **Python 3.12**; a separate Python installation is not required. Existing Python/Poetry users can keep their installation and run the updater directly.

- In file explorer, navigate to the directory where you want to install Windrecorder (it is recommended to place it in a partition with sufficient space), and download the app through the terminal command `git clone https://github.com/yuka-friends/Windrecorder`

     - You can open the folder you want to install, enter `cmd` in the path bar and press Enter, and you will be located into current directory in terminal, then paste the above command and press Enter to execute;

- Open `install_update.bat` to install and configure the app.


# 🦝 How to use

- Use an AI agent to search your records: [Memory skill installation and usage (简体中文)](__assets__/how_to_use_memory_skill.md).
- Open `start_app.bat` in the directory, the tool will run on the system tray and be used through the right-click menu;
- All data (video, database, statistical information) will be stored in `userdata` directory under Windrecorder. If you want to copy or move the app location (for example, if you change the computer), you can delete `.venv` in the directory and moved, then re-run `install_update.bat` to install the virtual environment to use it;

> [!TIP]
> Best practice: Set `Run on system startup` in webui to record everything without any fuss.
>
> **Recording will be automatically paused when there is no change in the picture or the screen is sleeping. When the computer is idle and no one is using it, the tool will automatically maintain the database, compress, and clean up expired videos.**
>
> _Just set it and forget it!_

# 🦝 How it works
![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/how-it-work-en.jpg)

Windrecorder offers two recording modes for your convenience:

1. **Automatic Flexible Screenshots**:

    Upon starting the recording, Windrecorder takes screenshots every 3 seconds (by default), indexing them when content or text changes, allowing real-time rewind. Additionally, every 15 minutes, past screenshots are automatically converted into videos.

    This option consumes low system resources and is suitable for users who need to store, rewind, and search for memory cues.

2. **Direct Video Recording via FFmpeg**:

    When recording begins, Windrecorder records video in 15-minute segments, indexing the video clips after recording completion (hence, there may be a 15-minute delay in data querying).

    This option consumes moderate system resources and enables smooth and complete recording of computer activities.

When the screen remains static, window titles or screen content are on the exclusion list, or the computer enters lock screen, recording pauses automatically and performs idle maintenance (compressing and cleaning videos, conducting image recognition embedding, etc.) until the user returns to continue operating the computer.

- _Image Embedding is provided as an extension and can be installed under the directory `extension/install_img_embedding_module`._


| Video recording size                                                                                                                | SQlite database size         |
|-------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| Per Hour: 2-100 Mb (depends on screen change\number of monitors)                                                                    |                              |
| Per Month: 10-20 Gb (depends on screen time)  Different video compression presets can compress these data to 0.1-0.7 times the size | Per Month: About 160 Mb      |

# 🦝 Q&A | Frequently Asked Questions

Q: The mouse pointer flicker during recording (Direct Video Recording via FFmpeg)

- A: It's a Windows historical issues, you can try [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg ) method to solve. TL;DR:
     - Use any hex editor (such as [HxD](https://mh-nexus.de/en/downloads.php?product=HxD20)) to open `avdevice-XX.dll` in the previously downloaded `FFmpeg/bin`;
     - Search for hex code `20 00 cc 40` and change the last two digits of `40` to `00`;
     - Save the file;

Q: There is no data in the recent period when opening webui.

- A: Check that recording and OCR indexing have completed, then refresh the page. Search reads committed data directly through read-only SQLite connections; there is no need to delete temporary databases. If an error persists, retain the database and include the error log when reporting the issue.

Q: When opening webui, it prompts: `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'`

- A: This is an old database-copying issue. Update Windrecorder and restart the web UI. Do not delete SQLite journal or WAL files; if the error persists, retain the database and report the error log.

Q: Windows.Media.Ocr.Cli OCR is not available/the recognition rate is too low

- A1: Check whether the language pack/input method of the target language has been added to the system: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr

- A2: Install a third-party OCR engine in the `extension` directory. They usually have higher recognition accuracy and support simultaneous recognition of multiple languages, but may take up slightly more performance;

- A3: Windows.Media.Ocr.Cli may struggle with small text. For Chinese text, enable similar-character search in Settings to improve recall when OCR confuses characters with similar shapes.

# 🧡
Thanks to the following projects

- https://github.com/DayBreak-u/chineseocr_lite
- https://github.com/zh-h/Windows.Media.Ocr.Cli
- https://github.com/kanadeblisst00/wechat_ocr
- https://github.com/tesseract-ocr/tessdoc
- https://github.com/unum-cloud/uform
- https://github.com/streamlit/streamlit


---

🧡 Like this tool? Also check out [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA)'s gentle music on Youtube and streaming music platforms, thank ya!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
---
Vote **Windrecorder** on Product Hunt:

<a href="https://www.producthunt.com/posts/windrecorder?utm_source=badge-featured&utm_medium=badge&utm_souce=badge-windrecorder" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=441411&theme=neutral" alt="Windrecorder - search&#0032;&#0038;&#0032;rewind&#0032;everything&#0032;happened&#0032;on&#0032;your&#0032;screen | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>

---

For more research and discussion on HackerNews:
- https://news.ycombinator.com/item?id=38787892
- https://news.ycombinator.com/item?id=40105371
