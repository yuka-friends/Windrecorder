![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-cn.jpg)
<h1 align="center"> 🦝 Windrecorder | 捕风记录仪</h1>
<p align="center"> An Open Source Rewind’s alternative for Windows. | 一款运行在 Windows 平台上的 Rewind 替代工具</p>

<p align="center"> English  | 简体中文 </p>

---
> What's Rewind ｜ Rewind 是什么？: https://www.rewind.ai/

This tool can continuously record and OCR your desktop screen, and search to retrieve the picture at that moment at any time.
It runs **entirely locally, stored your private data locally, without any need of Internet connection.**

这是一款可以持续录制并识别你的屏幕内容、通过搜索等手段随时找回相关记忆的工具。**它的所有服务（录制、识别处理等）完全运行在本地，在本地存储数据，无需联网，不会外泄你任何数据。**


![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/preview.png)


**NOTE: This project is still under early development and the availability of many features are not guaranteed.** 

**注意：这个项目仍然在开发早期阶段，部分能力和特性不保证可以正常运行。**

----

💡 Project Status: Have basically completely functions. Under intensity development

💡 项目状态：具有基本完整可用的功能。仍在持续开发中。

---

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

There are two ways to setup windrecorder:

## A. Download the integration package in Release Page (not yet created - soon!) (recommended)

- Download the integrated package with complete dependencies in Release Page.

- Run `install_update_setting.bat` to complete basic settings. That's it!

- Starting recording screen content: run `start_record.bat` (Close the console window to stop recording)

- Query, Rewind or update database manually through webui: run  `start_webui.bat`

## B. Manual deployment

- Ensure [ffmpeg](https://ffmpeg.org/) is installed and can be accessed from PATH.

- Make sure Python, Pip and Git are installed. Git clone this repository to your computer, then install virtualenv by `pip install virtualenv` and create a virtual environment under Windrecorder directory: `python -m venv env`. 

- Run `install_update_setting.bat` to install dependencies and complete basic settings. That's it!

- Starting recording screen content: run `start_record.bat` (Close the console window to stop recording)

- Query, Rewind or update database manually through webui: run  `start_webui.bat`

    - We recommend using Windows.Media.Ocr.Cli method to OCR Video data, which is faster and using less system resources. Make sure your Windows computer has installed the corresponding OCR language module (it should have been installed with IME by default, and used to identify the corresponding language content). For more information: https://learn.microsoft.com/en-us/windows/powertoys/text-extractor


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
