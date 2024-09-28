# Changelog 更新日志

> [!TIP]
> 如果无法升级，请尝试在目录下执行命令 `git fetch origin | git reset --hard origin/main` 后运行 `install_update.bat`
>
> If app cannot upgrade correctly, try executing the command `git fetch origin | git reset --hard origin/main` in the directory and then running `install_update.bat`

## 0.0.28
> 2024-09-24
- 添加了自定义 webui 背景图功能，可以在 `extension/set_custom_webui_background` 设置；Added custom webui background image, can be set in `extension/set_custom_webui_background`;
- 🍃 细化 灵活截图模式 的节能策略选项，可以选择立即合成、仅在插电时合成（限笔记本电脑）、仅在电脑空闲时合成视频；修复了 PC 由于一直插电、导致无法设定为仅闲时合成视频的问题；Refine the energy-saving strategy options of Flexible Screenshot Mode, you can choose to synthesize immediately, synthesize only when plugged in (limited to laptops), and synthesize video only when the computer is idle; fix the problem that the PC cannot be set to synthesize video only when idle because it is always plugged in; https://github.com/yuka-friends/Windrecorder/issues/237
- 提高了 webui 在记录数据较多时的初始化速度，通过优化了 check_is_onboarding 的判断逻辑；Improved the initialization speed of webui when recording a lot of data by optimizing the judgment logic of check_is_onboarding;

![set_custom_webui_background](https://github.com/yuka-friends/Windrecorder/blob/main/extension/set_custom_webui_background/_preview.jpg)


### Fixed
---rollout to new user---
- 正确捕获 LLM 生成出错时的异常；Handle exceptions when LLM generation fails; (@X-T-E-R)

---

## 0.0.27
> 2024-09-17
- 添加了是否启用记录浏览器链接的选项，如果感到浏览器卡顿，可以尝试关闭；Added the option to enable recording browser links. If you feel the browser is lagging, you can try to turn it off;

### Fixed
- 修复了在启动一段时间后，当前台窗口标题包含 windrecorder 时可能会被错误隐藏的 bug；Fixed a bug where the foreground window might be hidden incorrectly when its title contains windrecorder after a while of startup;

---

## 0.0.26
> 2024-09-10
- 更新了隐藏命令行窗口的方式，现在可以一打开 start_app.bat 立即自动隐藏；Updated the way to hide the command line window. Now it can be automatically hidden immediately after opening start_app.bat;
    - 如果命令行窗口一闪而过、过了一段时间 捕风记录仪 仍没有出现在托盘中，这可能是由于新的隐藏方式与系统不兼容，请在目录下创建一个名为`hide_CLI_by_python.txt`的文件以回到原先兼容性更加的隐藏方式；
    - If the command line window flashes by and the Windrecorder still does not appear in the tray after a while, it may be because the new hiding method is incompatible with the system. Please create a file named `hide_CLI_by_python.txt` in the directory to return to the original hiding method with more compatibility; https://github.com/yuka-friends/Windrecorder/issues/232

---

## 0.0.25
> 2024-09-01
- 生成光箱图片时，可以选择在底部添加时间戳水印；When generating a lightbox image, you can choose to add a timestamp watermark at the bottom;
- 添加了自定义光箱缩略图生成器，可以从任意日期范围创建光箱图片，支持自定义缩略图数量、分布模式、图像大小等。你可以在 `extension\create_custom_lightbox_thumbnail_image` 进行使用；Added custom lightbox thumbnail generator, which can create lightbox images from any date range, supports custom thumbnail count, distribution pattern, image size, etc. You can use it in `extension\create_custom_lightbox_thumbnail_image`; https://github.com/yuka-friends/Windrecorder/issues/226

![create_custom_lightbox_thumbnail_image](https://github.com/yuka-friends/Windrecorder/blob/main/extension/create_custom_lightbox_thumbnail_image/_preview.jpg)

### Fixed
- 修复了 json 可能因为未指定 utf-8 编码而导致读取出错的潜在问题；Fixed a potential issue where json might be read incorrectly because utf-8 encoding was not specified;

---

## 0.0.24
> 2024-08-24
- 在全局搜索页，提供更方便操作的月份滑杆选择器、精确日期选择器两种筛选模式；On the global search page, two filtering modes are provided: month slider selector and precise date selector, which are more convenient to operate;
- 在将每日活动提交给语言模型前，可以排除特定的词语列表，从而降低因为敏感内容导致生成失败概率；Before submitting daily activities to the language model, a specific list of words can be excluded to reduce the probability of generation failure due to sensitive content;
- 在每月活动中，支持通过语言模型生成标签、查看当月的所有诗词；In monthly activities, you can generate tags through language models and view all poems of the month;

---

## 0.0.23
> 2024-08-19
- 支持使用大语言模型为每日活动写一句诗歌；Add the ability to write a poem for each activity;
- 优化灵活截图模式，当一段时间（默认2mins）在跳过规则时终止记录当前视频片段；Optimize the flexible screenshot mode, and stop recording the current video clip when the rule is skipped for a period of time (default 2 minutes); (config.screenshot_interrupt_recording_count)

---

## 0.0.22
> 2024-08-17
- 支持使用大语言模型对每日活动进行标签提取总结；Add the ability to extract and summarize tags for daily activities;

![header_llm](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/header_llm.png)

- 升级 streamlit 版本，优化了部分界面布局；Upgrade the version of streamlit to optimize some interface layouts;
- 优化截图文件夹清理机制：清理之前可能遗漏的数据不足文件夹；Optimize the screenshot folder cleaning mechanism: clean up the folders with insufficient data that may have been missed before;
- 添加空闲时清理缓存文件夹机制；Add the mechanism of cleaning the cache folder in idle time;
- 将统计中的年月散点图缓存移动至用户文件夹；Move the scatter plot cache of year and month in statistics to the user folder.
- 支持使用"-"连接单词进行连续整句话的搜索匹配。比如通过搜索 'i-love-you' 而不是 'i love you'来匹配连续整句；Support using "-" to connect words for continuous whole sentence search matching. For example, by searching for 'i-love-you' instead of 'i love you' to match continuous whole sentences;

![instruction-search-split-dash](https://github.com/yuka-friends/Windrecorder/blob/main/__assets__/instruction-search-split-dash.jpg)

### Fixed
- bug: 当程序目录存在空格时，第三方 OCR 扩展无法进入虚拟环境完成安装；When the program directory has a space, the third-party OCR extension cannot enter the virtual environment to complete the installation;
- bug: 当时间戳位于12月，换算后结果可能大于12月从而异常；When the timestamp is in December, the result after conversion may be greater than December, which is abnormal; (utils.py(278))
- bug: 由于 wechat ocr 重复初始化导致 webui 假死；Due to repeated initialization of WeChat OCR, WebUI freezes;

---

## 0.0.21
> 2024-08-06
- 添加以下第三方 OCR 扩展，可以在 Extension 目录下进行安装；Add the following third-party OCR extensions, which can be installed in the Extension directory;
    - RapidOCR (Paddle OCR based on ONNXRuntime) (Collaborators: ASC8384)
    - WeChat OCR (Collaborators: B1lli), with extremely high Chinese and English recognition accuracy;
    - Tesseract OCR, supports more than 100 languages ​​and can recognize multiple languages ​​at the same time;
- 为压缩视频添加自动硬件加速参数；Added automatic hardware acceleration parameters for compressed video;

### Fixed
- bug：当截图文件不完整或损坏时，webui未能捕捉阻塞报错；When the screenshot file is incomplete or damaged, the webui not capture the blocking error;

---

## 0.0.20
> 2024-07-13
- 添加对 Chrome、Microsoft Edge、Firefox 当前浏览的 url 记录；Add the recording of the currently browsed URL in Chrome, Microsoft Edge, and Firefox;

---

## 0.0.19
> 2024-07-12
- 增加对前台窗口进程名的记录，从而可以更精确地统计与排除应用；Added the record of the foreground window process name, so that applications can be counted and excluded more accurately;

---

## 0.0.18
> 2024-07-06

### Fixed
- bug：修复了在新的一个月「自动灵活截图」无法自动将截图缓存转换为视频；Fixed the issue where the "Automatic Flexible Screenshot" couldn't automatically convert the screenshot cache into a video in the new month.
- bug：优化时间轴截图生成算法，当使用「自动灵活截图-仅捕捉前台窗口」时降低预览图变形几率；Optimized the timeline screenshot generation algorithm, which reduces the chances of preview image deformation under the "Automatic Flexible Screenshot - foreground window only" recording mode;
- 自动移除空截图缓存文件夹；Automatically remove the empty screenshot cache folder;
- bug: 修复了当录制视频时长超出 config.record_seconds 时，无法在一天之时中被定位展示；Fixed the issue that when the duration of the recorded video exceeds config.record_seconds, it cannot be located and displayed in Oneday;
- bug：一天之时在寻找最早最晚截图时间戳时，数据为空时会可能导致报错；When searching for the earliest and latest screenshot timestamps at Oneday, it may cause an error when the data is empty;
- bug：修复错误记录的维护时间戳缓存可能会阻塞正常的录制线程；Fixing the error maintenance timestamp cache may block the recording thread;

---

## 0.0.17
> 2024-06-29

### Fixed
- bug：修复了「自动灵活截图」下可能无法记录当前时间戳旗标；Fixed the issue that the current timestamp flag might not be recorded under "Automatic Flexible Screenshot";
- bug：修复了「自动灵活截图-仅捕捉单显示器时」无法使用；Fixed the issue that the "Automatic Flexible Screenshot" recording mode would not work;
- bug：修复了当截图未完整存储时无法合成视频的情况；Fixed the situation that the video could not be synthesized when the screenshot was not completely stored;

---

## 0.0.16
> 2024-06-26
- 添加了「自动灵活截图」录制模式，现在能以更低的系统资源进行录制、实时回溯已录制画面了，同时可以仅录制前台窗口、精确过滤不想被录制的内容。同时也保留了原先的「直接录制视频（ffmpeg）」模式，可根据需要自行选择；
- Added "Automatic Flexible Screenshot" recording mode, which can now record with lower system resources and replay recorded images in real time. It can also record only the foreground window and accurately filter out the content you don't want to record. At the same time, the original "Directly record video (ffmpeg)" mode is also retained, and you can choose it according to your needs.

---

## 0.0.15
> 2024-06-09

### Fixed
- bug: 修复了锁屏检测在 Windows 11 上不起作用；Fixed lock screen detection not working on Windows 11;
- 优化 i18n 逻辑，当 key 不存在时会 fallback 到 English 文案；Optimizing i18n logic, when the key does not exist, it will fallback to English copy text;

---

## 0.0.14
> 2024-06-01
- 升级了图像嵌入模型到 unum-cloud/uform v3，模型不再依赖庞大的 torch 环境，而使用更加节能轻便的 ONNX 进行推理，速度、能耗与召回质量均得到提升。如果你之前安装了旧版本，可通过 extension/install_img_embedding_module 中的脚本先卸载旧版、再安装新版、并可以对旧数据进行回滚以重新索引；
- 压缩视频：添加 AMF（AMD Advanced Media Framework）编码器选项；(@arrio464)
- 添加针对 Microsoft Edge / Firefox 的 h265 解码提示；

- Upgraded the image embedding model to unum-cloud/uform v3. The model no longer relies on the huge torch environment, but uses the more energy-efficient and lightweight ONNX for reasoning, which improves speed, energy consumption, and recall quality. If you have installed an old version before, you can use the script in extension/install_img_embedding_module to uninstall the old version first, then install the new version, and roll back the old data to re-index.
- Compressed video: added AMF (AMD Advanced Media Framework) encoder option;(@arrio464)
- Added h265 decoding tips for Microsoft Edge/Firefox;

### Fixed
- bug: 当试图列出每月第一天的所有数据时，会因为首条记录预览图为 None 而阻塞报错；When trying to list all data on the first day of each month, an error will be reported because the preview image of the first record is None;

---

## 0.0.13
> 2024-05-18
- 为索引出错的视频文件添加自动重试机制；
- Add automatic retry for index errored video files;

---

## 0.0.12
> 2024-04-21
- 添加了月度统计中对窗口标题的过滤，现在可以查看具体关于某件事的屏幕时间了；
- Added filtering for window titles in monthly statistics, now you can view screen time specifically about something;

### Fixed
- bug: 当 OCR 支持语言找不到对应测试集时，将会阻塞 onboarding 向导；When the OCR supported language cannot find the corresponding test set, the onboarding wizard will be blocked;
- 添加更多尝试隐藏 CLI 窗口次数重试，以应对未解锁屏幕时隐藏失败；Added more retries to try to hide the CLI window in case hiding fails when the screen is not unlocked;
- Fix: Startup path now supports spaces;(@zetaloop)

---

## 0.0.11
> 2024-04-19

- 支持多显示器与单个显示器录制；
- 添加了录制时的编码选项（cpu_h264, cpu_h265, NVIDIA_h265, AMD_h265, SVT-AV1）；(@myshzzx)
- 优化了索引时比较图像的性能；
- 索引视频切片时，如果有相同内容显示在不同时间点，可以只记录第一次出现、而不重复记录；
- 优化 webui 底部统计信息缓存机制，在数据多的情况下获得更快加载体验；

- Supports multi-monitor and single-monitor recording;
- Added encoding options when recording (cpu_h264, cpu_h265, NVIDIA_h265, AMD_h265, SVT-AV1);(@myshzzx)
- Optimized the performance of comparing images during indexing;
- When indexing video slices, if the same content is displayed at different points in time, only the first occurrence can be recorded without repeated recording;
- Optimize the statistical information caching mechanism at webui footer to obtain a faster loading experience when there is a lot of data;

### Fixed
- bug: 当锁屏时程序有几率不会进入空闲暂停状态；There is a chance that the program will not enter the idle pause state when the screen is locked;
- bug: INDEX 标签被添加在 iframe cache 目录名中，导致不会被 img embedding 索引和清理；The INDEX tag should not been added to the iframe cache directory name, which resulting in it not being indexed and cleaned by img embedding;

---

## 0.0.10
> 2024-03-03

### Fixed
- https://github.com/yuka-friends/Windrecorder/pull/138 feat: 为 webui footer 数据统计添加了缓存机制，不需要每次进入 webui 都进行统计了，大幅提高加载速度。 A caching mechanism has been added for webui footer data statistics, so there is no need to perform statistics every time you enter webui, which significantly improve loading speed.
- bug: 当一天以非零点分隔时，每月最后一天无法被选择。 The last day of the month cannot be selected when the days are separated by a non-zero point.
- bug: 升级时没有保留原用户 config. The original user config is not retained during the upgrade.
- bug: bug: during CLI loading, if force on other window it be hidden instead of CLI https://github.com/yuka-friends/Windrecorder/issues/133

---

## 0.0.9
> 2024-03-02

### Fixed
- https://github.com/yuka-friends/Windrecorder/pull/137 bug: 在索引视频时因为 column name typo 导致索引失败。 Indexing failed due to column name typo when indexing videos.

---

## 0.0.8
> 2024-02-24

- **添加图像语义嵌入、检索扩展，可以通过对画面的自然语言描述进行搜索、或以图搜图**；在 extension\install_img_embedding_module 进行安装；
- 可跳过录制自定义的前台活动了，比如自定义锁屏、游戏、隐私场景等；
- 移除了 一日之时 中的词云统计，UI 提供双栏与三栏布局；
- 在搜索时提供推荐词；
- 调整目录结构，将所有用户数据集中放置到 userdata 下；
- 添加日志；添加对搜索历史的记录（可在 config_user.json enable_search_history_record 中设置）
- 对闲时任务添加了分批数量限制；

- Add image embedding and retrieval extension, which can **search through the natural language description of the picture or search for pictures**; install in extension\install_img_embedding_module;
- You can now skip recording customized foreground activities, such as customized lock screens, games, privacy scenes, etc.
- Removed wordcloud in Daily; Provide two-column and three-column layout;
- Provided synonyms recommend in global search; 
- Adjust the directory structure and centrally place all user data under userdata dictionary;
- Add logger; Add a record of search history (can be set in config_user.json enable_search_history_record)
- Added a limit on the number of batches for idle tasks;

### Fixed
- bug: 当 CLI 未隐藏时切换了活动前台窗口、导致该前台窗口被隐藏；(?)

---

## 0.0.7
> 2024-02-09

- **添加对窗口标题的记录与统计；**
- 添加时间标记功能，可以为当下时间、回溯中的时间进行标记和备注，方便回忆查找；
- 添加 webui 保护密码；
- 添加托盘中的更新日志入口；
- 隐藏显示命令行窗口，加入阻止托盘重复运行；
- 升级支持了 python 3.11；虚拟环境默认创建在 windrecorder 目录下；

- Added time mark function, which can mark and make notes for the current time and the time in retrospect to facilitate recall and search;
- Added records and statistics of window titles;
- Add webui protection password;
- Added update log entry in the tray;
- Hide the command line window and prevent the tray from running repeatedly;
- Upgraded to support python 3.11; the virtual environment is created in the windrecorder directory by default;

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/109 bug: 托盘显示"WebUI started failed"且无webui错误日志
- https://github.com/yuka-friends/Windrecorder/issues/97 bug: 当开启“形近字”搜索，可能以空字符进行搜索
- https://github.com/yuka-friends/Windrecorder/pull/105 修复图像对比函数
- https://github.com/yuka-friends/Windrecorder/issues/100 bug: “记忆摘要”统计中，翻阅年视图不生效
- https://github.com/yuka-friends/Windrecorder/pull/88 fix state page date selector

---

## 0.0.6
> 2024-01-25

- **修复了 webui 下重复轮询数据库的 bug，大幅提升使用性能；**
- 修复全新安装时可能遇到的 db 目录不存在而阻塞的错误；
- 移除更新 st.experimental.rerun 为 st.rerun；
- 优先在 Windrecorder 目录下添加虚拟环境；

- **Fixed the bug of repeatedly polling the database under webui, greatly improving performance;**
- Fixed an error that may be encountered during a new installation due to the non-existence of the db directory;
- Removed and updated st.experimental.rerun to st.rerun;
- Prioritize adding a virtual environment under the Windrecorder directory;

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/103 bug: update check broken, user can never get update remind
- https://github.com/yuka-friends/Windrecorder/issues/100 bug: “记忆摘要”统计中，翻阅年视图不生效
- https://github.com/yuka-friends/Windrecorder/issues/87 bug: 当存在跨年的数据，“记忆摘要”tab 下的月份选择器范围约束会失效
- https://github.com/yuka-friends/Windrecorder/issues/77 bug: 在托盘关闭 webui 服务后，菜单残留局域网提示项
- https://github.com/yuka-friends/Windrecorder/issues/56 feat: 已有托盘在运行时，阻止托盘重复启动、且提供指引提示

---

## 0.0.5
> 2023-12-22

- 添加了托盘形态：现在可以通过托盘来控制记录与进入查询页面了，不再需要通过脚本手动控制；
- 为闲时维护添加了视频压缩参数设置；
- 使用 poetry 创建与维护虚拟环境；

- Added tray: now you can control recording and enter the query page through the tray, no longer need to manually control through script;
- Added video compression parameter settings for idle time maintenance;
- Use poetry to create and maintain virtual environments;

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/75 bug: 点击webui中 录制与视频存储-自动化维护-测试支持的编码方式 之后，报错，详细信息如图
- https://github.com/yuka-friends/Windrecorder/issues/62 Bug: webui 在 Firefox 上无法播放，本地可以
- https://github.com/yuka-friends/Windrecorder/issues/37 bug: Windows Terminal 下背景颜色显示异常

---

## 0.0.4 
> 2023-11-25

- 修复若干 bug，治理重构了大量代码。

- Fixed bugs and refactor a large amount of code.

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/42 执行install_update_setting.bat报错Type error
- https://github.com/yuka-friends/Windrecorder/issues/33 random walk功能失效
- https://github.com/yuka-friends/Windrecorder/issues/31 记忆摘要部分中的词云和光箱无法正确更新
- https://github.com/yuka-friends/Windrecorder/issues/27 安装时候报错
- https://github.com/yuka-friends/Windrecorder/issues/22 文件夹在重新命名后未考虑到原本的文件夹问题
- https://github.com/yuka-friends/Windrecorder/issues/12 在全局搜索页面时，有时输入框需要输入两次才能执行搜索
