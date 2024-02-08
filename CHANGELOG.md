# Changelog

## 0.0.6
> 2024-01-25

- **修复了 webui 下重复轮询数据库的 bug，大幅提升使用性能；**
- 修复全新安装时可能遇到的 db 目录不存在而阻塞的错误；
- 移除更新 st.experimental.rerun 为 st.rerun；
- 优先在 Windrecorder 目录下添加虚拟环境；

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/103 bug: update check broken, user can never get update remind
- https://github.com/yuka-friends/Windrecorder/issues/100 bug: “记忆摘要”统计中，翻阅年视图不生效
- https://github.com/yuka-friends/Windrecorder/issues/87 bug: 当存在跨年的数据，“记忆摘要”tab 下的月份选择器范围约束会失效
- https://github.com/yuka-friends/Windrecorder/issues/77 bug: 在托盘关闭 webui 服务后，菜单残留局域网提示项
- https://github.com/yuka-friends/Windrecorder/issues/56 feat: 已有托盘在运行时，阻止托盘重复启动、且提供指引提示


## 0.0.5
> 2023-12-22

- 添加了托盘形态：现在可以通过托盘来控制记录与进入查询页面了，不再需要通过脚本手动控制；
- 为闲时维护添加了视频压缩参数设置；
- 使用 poetry 创建与维护虚拟环境；

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/75 bug: 点击webui中 录制与视频存储-自动化维护-测试支持的编码方式 之后，报错，详细信息如图
- https://github.com/yuka-friends/Windrecorder/issues/62 Bug: webui 在 Firefox 上无法播放，本地可以
- https://github.com/yuka-friends/Windrecorder/issues/37 bug: Windows Terminal 下背景颜色显示异常


## 0.0.4 
> 2023-11-25

- 修复若干 bug，治理重构了大量代码。

### Fixed
- https://github.com/yuka-friends/Windrecorder/issues/42 执行install_update_setting.bat报错Type error
- https://github.com/yuka-friends/Windrecorder/issues/33 random walk功能失效
- https://github.com/yuka-friends/Windrecorder/issues/31 记忆摘要部分中的词云和光箱无法正确更新
- https://github.com/yuka-friends/Windrecorder/issues/27 安装时候报错
- https://github.com/yuka-friends/Windrecorder/issues/22 文件夹在重新命名后未考虑到原本的文件夹问题
- https://github.com/yuka-friends/Windrecorder/issues/12 在全局搜索页面时，有时输入框需要输入两次才能执行搜索
