![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-header-cn.jpg)
<h1 align="center"> 🦝 Windrecorder | 捕风记录仪</h1>
<p align="center"> An Open Source Rewind’s alternative tool on Windows to help you retrieve memory cues.</p>
<p align="center">一款运行在 Windows 平台上的 Rewind 替代工具，帮助你找回记忆线索</p>

<p align="center"> <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-en.md">English</a>  | 简体中文 | <a href="https://github.com/Antonoko/Windrecorder/blob/main/__assets__/README-ja.md">日本語</a> </p>

---
> Rewind App 是什么？: https://www.rewind.ai/

这是一款可以持续记录你的屏幕、通过关键词搜索等方式随时找回相关记忆的工具。

**它的所有能力（录制、识别处理、存储回溯等）完全运行在本地，无需联网，不上传任何数据。它只做它应该做的事。**

![Windrecorder](https://github.com/Antonoko/Windrecorder/blob/main/__assets__/product-preview-cn.jpg)


# 🦝 安装

- 下载 [ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip) ，并将其中bin目录下的ffmpeg.exe解压至 `C:\Windows\System32` 下（或其他 PATH 访问得到的目录下）

- 确保已安装 [Git](https://git-scm.com/downloads)、[Python](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe)（安装时勾选 Add python.exe to PATH）、[Pip](https://pip.pypa.io/en/stable/installation/)；

- 导航到想要安装的目录下，通过终端命令 `git clone https://github.com/Antonoko/Windrecorder` 下载该工具；

    - 可以打开想要安装的文件夹，在路径栏输入`cmd`并回车，进入当前目录终端，将以上命令贴入、回车执行；

- 打开目录下的`install_update_setting.bat`进行工具安装与配置，顺利的话就可以开始使用了！

    - 如因网络原因报错，可在脚本安装依赖前添加代理`set https_proxy=http://127.0.0.1:xxxx`、或添加大陆[镜像源](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)；

- 通过打开目录下的`start_record.bat`进行屏幕记录，通过`start_webui.bat`来回溯、查询与进行设置；

---
### Roadmap:
- [x] 以较小的文件体积稳定持续地录制屏幕
- [x] 只识别发生变化的画面，在数据库中存储索引
- [x] 完善的图形界面（webui）
- [x] 词云、时间轴、光箱、散点图的数据总结
- [x] 录制完片段后自动识别、自动维护清理与压缩视频
- [ ] 多语言支持：已完成界面的 i18n 支持。todo：编译支持 English/日本語 环境的 Windows.Media.Ocr.Cli
- [ ] 优化流程，提升性能
- [ ] 添加多屏幕的记录支持（取决于 pyautogui 未来特性加入）
- [ ] 添加画面模态的识别，以实现对画面内容描述的搜索
- [ ] 添加词嵌入索引、本地 LLM 查询
- [ ] 🤔



# 🦝 Q&A | 常见问题
Q: 在打开webui时提示：FileNotFoundError: [WinError 2] The system cannot find the file specified: './db\\user_2023-10_wind.db-journal'

- A: 通常在初次访问 webui 时、start_record.bat 仍正在索引数据时出现。
解决方法：在 start_record.bat 后台索引完毕后，删除 db 文件夹下对应后缀为 _TEMP_READ.db 的数据库文件后刷新即可。

Q: 录制过程中鼠标闪烁

- A：Windows历史遗留问题，可尝试[该帖](https://stackoverflow.com/questions/34023630/how-to-avoid-mouse-pointer-flicker-when-capture-a-window-by-ffmpeg)方法解决🤔。

Q：结果在同一个视频中时，拖动滑杆不自动跳转时间

- A：streamlit 的 bug [#7126](https://github.com/streamlit/streamlit/issues/7126)，将在未来修复。

Q: Windows.Media.Ocr.Cli OCR的识别率过低

- A: 检查系统中是否添加了目标语言的语言包/输入法：https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr


# 🧡
引入了这些项目的帮助：

- https://github.com/DayBreak-u/chineseocr_lite

- https://github.com/zh-h/Windows.Media.Ocr.Cli


---

喜欢这个工具？欢迎到 Youtube 与流媒体音乐平台上听听 [長瀬有花 / YUKA NAGASE](https://www.youtube.com/channel/UCf-PcSHzYAtfcoiBr5C9DZA) 温柔的音乐，谢谢！

> "Your tools suck, check out my girl Yuka Nagase, she's amazing, I code 10 times faster when listening to her." -- @jpswing
