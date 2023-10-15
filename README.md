![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-cn.jpg)
<h1 align="center"> 🦝 Windrecorder | 捕风记录仪</h1>
<p align="center"> An Open Source Rewind’s alternative tool on Windows to help you retrieve memory cues.</p>
<p align="center">一款运行在 Windows 平台上的 Rewind 替代工具，帮助你找回记忆线索</p>

<p align="center"> English  | 简体中文 | 日本語 </p>

---
> What's Rewind ｜ Rewind 是什么？: https://www.rewind.ai/

这是一款可以持续记录你的屏幕内容、通过关键词搜索等方式随时找回相关记忆的工具。**它的所有服务（录制、识别处理等）完全运行在本地，在本地存储数据，无需联网，不会外泄你任何数据。**

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/preview.png)

----

### Roadmap:
- [x] Continuously record screen with smaller file size
- [x] Extract unchanging frames in video file and save OCR result in database
- [x] Word Cloud and Timeline/Lightbox summarize
- [x] Full functional webui dashboard & control center for querying database and set configuration
- [x] Automated operation: auto compress and remove outdated videos to save space
- [x] Fully i18n support with English, Simple Chinese, Japanese
- [x] Setup an easier to use Onboarding/installer
- [ ] Polishing details, improving stability and code quality
- [ ] Multi-monitors supports (depends on pyautogui's future update)
- [ ] Add vision understanding based search
- [ ] Add LLM summarize and vector searching
- [ ] 🤔


# 🦝 QuickStart ｜ 快速开始

- 下载 [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) ，并将其中bin目录下的ffmpeg.exe解压至 `C:\Windows\System32` 下（或其他 PATH 访问得到的目录下）

- 确保已安装 [Git](https://git-scm.com/downloads)、[Python](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe)（安装时勾选 Add python.exe to PATH）、[Pip](https://pip.pypa.io/en/stable/installation/)；

- 导航到想要安装的目录下，通过终端命令 `git clone https://github.com/Antonoko/Windrecorder` 下载该工具；

    - 可以打开想要安装的文件夹，在路径栏输入`cmd`并回车，进入当前目录终端，将以上命令贴入、回车执行；

- 打开目录下的`install_update_setting.bat`进行工具安装与配置，顺利的话就可以开始使用了！

    - 如因网络原因报错，可在脚本安装依赖前添加代理`set https_proxy=http://127.0.0.1:xxxx`、或添加大陆镜像源；

- 通过打开目录下的`start_record.bat`进行屏幕记录，通过`start_webui.bat`来回溯、查询与进行设置；





- Ensure [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) is installed and can be accessed from PATH.

- Make sure Python, Pip and Git are installed. Git clone this repository to your computer, then install virtualenv by `pip install virtualenv` and create a virtual environment under Windrecorder directory: `python -m venv env`. 

- Run `install_update_setting.bat` to install dependencies and complete basic settings. That's it!

- Starting recording screen content: run `start_record.bat` (Close the console window to stop recording)

- Query, Rewind or update database manually through webui: run  `start_webui.bat`

    - We recommend using Windows.Media.Ocr.Cli method to OCR Video data, which is faster and using less system resources. Make sure your Windows computer has installed the corresponding OCR language module (it should have been installed with IME by default, and used to identify the corresponding language content). For more information: https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr


# 🦝 Q&A | 常见问题
Q: 在打开webui时提示：FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'

A: 这种情况通常在初次访问时、start_record.bat 仍正在索引数据时出现。解决方法：在 start_record.bat 后台索引完毕后，删除 db 文件夹下对应后缀为 _TEMP_READ.db 的数据库文件后刷新即可。

Q: 录制过程中鼠标闪烁

A：

Q：结果在同一个视频中时，拖动滑杆不自动跳转时间

A：


# 🧡
引入了这些项目的帮助：

- https://github.com/DayBreak-u/chineseocr_lite

- https://github.com/zh-h/Windows.Media.Ocr.Cli

---

Like this project? Also check out [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) 's healing music on YouTube and Stream music platform <3

如果你喜欢这个工具，欢迎在 Youtube 与流媒体音乐平台上支持 **长濑有花** 温柔的音乐，谢谢！

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
