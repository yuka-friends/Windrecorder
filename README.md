<h1 align="center"> 🦝 Windrecorder | 捕风记录仪</h1>
<p align="center"> A Rewind’s alternative for Windows. | 一款运行在 Windows 平台上的 Rewind 替代工具</p>

---
> What's Rewind ｜ Rewind 是什么？: https://www.rewind.ai/

This tool can continuously record and OCR your desktop screen, and search to retrieve the picture at that moment at any time.
It runs entirely locally, stored your private data locally, without any need of Internet connection. 

这是一款可以持续录制并 OCR 你的桌面屏幕、通过搜索等手段随时找回任意时刻画面的工具。它完全运行在本地、在本地存储数据、无需联网、不会外泄你任何数据的工具。


![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/preview.png)


**NOTE: This project is still under development and the availability of many features are not guaranteed.**

**注意：这个项目仍然在开发中的阶段，部分能力和特性不保证可以正常运行。**

-

Project Status: have very basic functions

项目状态：初级阶段，具有基本的功能。

-

### Todo:
- [x] Continuously record screen with smaller file size.
- [x] Extract unchanging frames in the file and ocr record them to the database.
- [x] Provide basic webui for querying and updating database.
- [ ] Better webui dashboard & control center
- [ ] Automated operation
- [ ] Fully i18n support
- [ ] Polishing details
- [ ] 🤔


# 🦝 QuickStart ｜ 快速开始

- Installed ffmpeg and make sure it can be accessed from PATH.

- Install dependencies: `pip install -r requirements.txt`

- Starting recording screen: `Python recordScreen.py` or run `start_record.bat`

  - **NOTE:** This function is crude and can only be run and terminated manually at present. ~~Before recording, you need to adjust your screen resolution and block recording time in `config.json`, currently the default set is 3840x2160, 60 seconds.~~

- Query and update database through webui: `python -m streamlit run webui.py` or run  `start_webui.bat`

- We recommend using Windows.Media.Ocr.Cli method to OCR Video data, so make sure your Windows computer has installed the corresponding OCR language module (it should have been installed with IME by default). For more information: https://learn.microsoft.com/en-us/windows/powertoys/text-extractor


# 🧡
If you like this project, feel free to check [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) 's healing music on YouTube and Stream music platform <3 thx

如果你喜欢这个工具，请考虑在 Youtube 与流媒体音乐平台上支持**长濑有花**温柔的音乐，谢谢！

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
