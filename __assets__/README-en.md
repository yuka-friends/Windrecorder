![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-header-en.jpg)
<h1 align="center"> 🦝 Windrecorder | Personal Memory Search Engine</h1>
<p align="center"> An Open Source Mac App <a href="https://www.rewind.ai/">Rewind</a>'s alternative tool on Windows to help you retrieve memory cues.</p>

<p align="center"> <a href="https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | <a href="https://github.com/yuka-friends/Windrecorder/blob/main/README.md">简体中文</a></p>

---

Windrecorder is a memory search app by records everything on your screen in small size, to let you rewind what you have seen, query through OCR text or image description, and get activity statistics. All its capabilities run completely locally, without the need for an Internet connection or uploading any data, you should own all your data.**

![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/product-preview-en.jpg)

**Windrecorder currently does:**
- Record multiple or single displays stably and continuously with a small file size;
- Only index the changed scenes and update the OCR text, page title and other information to the database; automatically maintain the database, clean and compress the video when no one is using the computer;
- Complete webui interface, which can review the screen, conduct OCR/image semantics and other queries;
- Provide data summaries such as activity statistics, word clouds, timelines, light boxes, scatter plots, etc.;
- Supports multiple languages. Currently built-in: Simplified Chinese, English, and Japanese. Welcome to contribute multilingual translations and help us improve copywriting quality.
- _coming soon... pay attention to our PR :)_

**Windrecorder current limitations:**
- Only supports recording for the main display, multi-display support is still under development;
- FFmpeg may occupy a large amount of memory in some cases;

---

> [!WARNING]
> This project is still in the early stages of development, and you may encounter some minor problems in experience and use, feel free to submit issue feedback, follow updates, and initiate discussions or roadmap in [Discussions](https://github.com/yuka-friends/Windrecorder/discussions).You are also welcome to help us optimize and build the project, submit PR/review.

# 🦝 Installation

- Download [ffmpeg](https://github.com/BtbN/FFmpeg-Builds/releases) (the download file name is: `ffmpeg-master-latest-win64-gpl-shared.zip`), extract all files in `bin` directory(excluding the bin directory itself) to `C:\Windows\System32` (or other directories located in PATH)
     - ffmpeg may have a bug that "the mouse pointer flicker during screen recording". You can fix it according to the Q&A below and then copy to the system directory;

- Install [Git](https://git-scm.com/download/win), just keep clicking next step.

- Install [Python](https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe), make sure to check `Add python.exe to PATH` when installing.
     - **Currently, Python 3.12 is not supported**. It is recommended to use python 3.11, which is the version pointed to by the link above.

- In file explorer, navigate to the directory where you want to install Windrecorder (it is recommended to place it in a partition with sufficient space), and download the app through the terminal command `git clone https://github.com/yuka-friends/Windrecorder`;

     - You can open the folder you want to install, enter `cmd` in the path bar and press Enter, and you will be located into current directory in terminal, then paste the above command and press Enter to execute;

     - Currently, if there are spaces in the installation path, an error may occur on app startup. [#110](https://github.com/yuka-friends/Windrecorder/issues/110)

- Open `install_update.bat` in the directory to install dependencies and configure the app. If everything goes well, you can start using it!


# 🦝 How to use

- Open `start_app.bat` in the directory, the tool will run in the system tray and be used through the right-click menu;
- All data (video, database, statistical information) will be stored in `userdata` directory in Windrecorder. If you want to copy or move the app location (for example, if you change the computer), you can delete `.venv` in the directory and moved, then re-run `install_update.bat` to install the virtual environment to use it;

> [!TIP]
> Best practice: Set up auto-start in webui to record everything without any fuss.
>
> **Recording will be automatically paused when there is no change in the picture or the screen is sleeping. When the computer is idle and no one is using it, the tool will automatically maintain the database, compress, and clean up expired videos.**
>
> _Just set it and forget it!_


# 🦝 How it works
![Windrecorder](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/how-it-work-en.jpg)

When recording is started, the Windrecorder will record each 15 minutes of video segment by segment, and the video segments will be indexed after the recorded (therefore, there may be a 15-minute delay while querying the data). When the screen content not change, or the foreground windows title in skip list, or the computer enters the lock screen/sleep state, recording will be automatically paused and idle maintenance will be performed (compressing and cleaning videos, image embedding recognition, etc.) until the user comes back and continues to use the computer.

- _Image Embedding is provided as an extension and can be installed under the directory `extension/install_img_embedding_module`._


| Video recording size                                                                                                                | SQlite database size         |
|-------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| Per Hour: 2-100 Mb (depends on screen change\number of monitors)                                                                    |                              |
| Per Month: 10-20 Gb (depends on screen time)  Different video compression presets can compress these data to 0.1-0.7 times the size | Per Month: About 160 Mb      |

> In the future, the recording method may be improved to reduce ffmpeg usage and eliminate the need to wait for traceback.


# 🦝 Q&A | Frequently Asked Questions

Q: The mouse pointer flicker during recording

- A: It's a Windows historical issues, you can try [this post](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg ) method to solve.
     - Use any hex editor (such as [HxD](https://mh-nexus.de/en/downloads.php?product=HxD20)) to open `avdevice-XX.dll` in the previously downloaded `FFmpeg/bin`;
     - Search for hex code `20 00 cc 40` and change the last two digits of `40` to `00`;
     - Save the file;

Q: There is no data in the recent period when opening webui.

- A: When the tool is indexing data, webui will not create the latest temporary database file.
Solution: Try to wait for a while, wait for the tool indexing to complete, refresh the webui interface, or delete the database file with the suffix _TEMP_READ.db in the db directory and refresh it (if there is a database file damage prompt, don’t worry, it may be The tool is still in the index, please try refreshing/removing it after some time). This strategy will be fixed and refactored in the future. [#26](https://github.com/yuka-friends/Windrecorder/issues/26)

Q: When opening webui, it prompts: `FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'`

- A: Usually occurs when accessing the webui for the first time, while the tool is still indexing data.
Solution: After the tool background indexing is completed, delete the corresponding database file with the suffix _TEMP_READ.db in the db folder and refresh it.

Q: Windows.Media.Ocr.Cli OCR is not available/the recognition rate is too low

- A1: Check whether the language pack/input method of the target language has been added to the system: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr

- A2: Windows.Media.Ocr.Cli may have poor recognition rate for text. We will add more OCR extension support in the future.

# 🧡
Thanks to the following projects

- https://github.com/DayBreak-u/chineseocr_lite
- https://github.com/zh-h/Windows.Media.Ocr.Cli
- https://github.com/unum-cloud/uform
- https://github.com/streamlit/streamlit


---

🧡 Like this tool? Also check out [YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA)'s gentle music on Youtube and streaming music platforms, thank ya!

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
---
Vote **Windrecorder** on Product Hunt:

<a href="https://www.producthunt.com/posts/windrecorder?utm_source=badge-featured&utm_medium=badge&utm_souce=badge-windrecorder" target="_blank"><img src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=441411&theme=neutral" alt="Windrecorder - search&#0032;&#0038;&#0032;rewind&#0032;everything&#0032;happened&#0032;on&#0032;your&#0032;screen | Product Hunt" style="width: 250px; height: 54px;" width="250" height="54" /></a>
