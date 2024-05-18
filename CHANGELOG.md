# Changelog 更新日志

## 0.0.13
> 2024-05-18
- 为索引出错的视频文件添加自动重试机制；
- Add automatic retry for index errored video files;

## 0.0.12
> 2024-04-21
- 添加了月度统计中对窗口标题的过滤，现在可以查看具体关于某件事的屏幕时间了；
- Added filtering for window titles in monthly statistics, now you can view screen time specifically about something;

### Fixed
- bug: 当 OCR 支持语言找不到对应测试集时，将会阻塞 onboarding 向导；When the OCR supported language cannot find the corresponding test set, the onboarding wizard will be blocked;
- 添加更多尝试隐藏 CLI 窗口次数重试，以应对未解锁屏幕时隐藏失败；Added more retries to try to hide the CLI window in case hiding fails when the screen is not unlocked;

## 0.0.11
> 2024-04-19

- 支持多显示器与单个显示器录制；
- 添加了录制时的编码选项（cpu_h264, cpu_h265, NVIDIA_h265, AMD_h265, SVT-AV1）；
- 优化了索引时比较图像的性能；
- 索引视频切片时，如果有相同内容显示在不同时间点，可以只记录第一次出现、而不重复记录；
- 优化 webui 底部统计信息缓存机制，在数据多的情况下获得更快加载体验；

- Supports multi-monitor and single-monitor recording;
- Added encoding options when recording (cpu_h264, cpu_h265, NVIDIA_h265, AMD_h265, SVT-AV1);
- Optimized the performance of comparing images during indexing;
- When indexing video slices, if the same content is displayed at different points in time, only the first occurrence can be recorded without repeated recording;
- Optimize the statistical information caching mechanism at webui footer to obtain a faster loading experience when there is a lot of data;

### Fixed
- bug: 当锁屏时程序有几率不会进入空闲暂停状态；There is a chance that the program will not enter the idle pause state when the screen is locked;
- bug: INDEX 标签被添加在 iframe cache 目录名中，导致不会被 img embedding 索引和清理；The INDEX tag should not been added to the iframe cache directory name, which resulting in it not being indexed and cleaned by img embedding;

## 0.0.10
> 2024-03-03

### Fixed
- https://github.com/yuka-friends/Windrecorder/pull/138 feat: 为 webui footer 数据统计添加了缓存机制，不需要每次进入 webui 都进行统计了，大幅提高加载速度。 A caching mechanism has been added for webui footer data statistics, so there is no need to perform statistics every time you enter webui, which significantly improve loading speed.
- bug: 当一天以非零点分隔时，每月最后一天无法被选择。 The last day of the month cannot be selected when the days are separated by a non-zero point.
- bug: 升级时没有保留原用户 config. The original user config is not retained during the upgrade.
- bug: bug: during CLI loading, if force on other window it be hidden instead of CLI https://github.com/yuka-friends/Windrecorder/issues/133

## 0.0.9
> 2024-03-02

### Fixed
- https://github.com/yuka-friends/Windrecorder/pull/137 bug: 在索引视频时因为 column name typo 导致索引失败。 Indexing failed due to column name typo when indexing videos.

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
