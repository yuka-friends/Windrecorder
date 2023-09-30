![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-cn.jpg)
<h1 align="center"> 🦝 Windrecorder | 捕风记录仪</h1>
<p align="center"> An Open Source Rewind’s alternative for Windows. | 一款运行在 Windows 平台上的 Rewind 替代工具</p>

---
> What's Rewind ｜ Rewind 是什么？: https://www.rewind.ai/

This tool can continuously record and OCR your desktop screen, and search to retrieve the picture at that moment at any time.
It runs **entirely locally, stored your private data locally, without any need of Internet connection.**

这是一款可以持续录制并识别你的屏幕内容、通过搜索等手段随时找回相关记忆的工具。**它的所有服务（录制、识别处理等）完全运行在本地，在本地存储数据，无需联网，不会外泄你任何数据。**


![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/preview.png)


**NOTE: This project is still under early development and the availability of many features are not guaranteed.** English and i18n GUI support will be added after the alpha version is released.

**注意：这个项目仍然在开发早期阶段，部分能力和特性不保证可以正常运行。**

----

💡 Project Status: have very basic functions, under intensity development

💡 项目状态：初级阶段，具有基本的功能。仍在持续开发中。

---

### Todo:
- [x] Continuously record screen with smaller file size.
- [x] Extract unchanging frames in video file and save OCR result in database.
- [x] Provide basic webui for querying and updating database.
- [x] Word Cloud and Timeline/Lightbox summarize
- [ ] Full functional webui dashboard & control center
- [ ] Automated operation
- [ ] Fully i18n support
- [ ] Setup an easier to use Onboarding/installer
- [ ] Polishing details, improving stability
- [ ] 🤔


# 🦝 QuickStart ｜ 快速开始


- Ensure [ffmpeg](https://ffmpeg.org/) is installed and can be accessed from PATH.

- Install dependencies: `pip install -r requirements.txt`

- Starting recording screen: run `start_record.bat` (send "ctrl C" or close console window to stop recording)

- Query, Rewind or update database manually through webui: run  `start_webui.bat`

    - We recommend using Windows.Media.Ocr.Cli method to OCR Video data, which is faster and using less system resources. Make sure your Windows computer has installed the corresponding OCR language module (it should have been installed with IME by default, and used to identify the corresponding language content). For more information: https://learn.microsoft.com/en-us/windows/powertoys/text-extractor


# 🧡
Like this project? Also check out [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) 's healing music on YouTube and Stream music platform <3

如果你喜欢这个工具，欢迎在 Youtube 与流媒体音乐平台上支持 **长濑有花** 温柔的音乐，谢谢！

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
