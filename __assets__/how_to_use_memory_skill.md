# 用 AI Agent 检索 Windrecorder 记录

最简单的方式：让支持 skill 安装的本地 AI Agent 帮你安装，直接发送：

> 请安装 E:\Windrecorder\extension\windrecorder-memory 这个 skill。

将 `E:\Windrecorder` 换成你的实际安装目录，并确认 Windrecorder 已更新、包含该 skill 文件夹。

需要一个能读取本机文件、执行 Python 的 AI Agent。无需在 Windrecorder 中配置 LLM API。

## 手动安装（以 Codex 为例）

1. 更新 Windrecorder，确认安装目录中已有 `extension\windrecorder-memory` 文件夹。
2. 将这个**完整文件夹**复制到 `%USERPROFILE%\.agents\skills\`（没有该目录就创建），最终应有：
   `%USERPROFILE%\.agents\skills\windrecorder-memory\SKILL.md`。不要只复制 `SKILL.md`。
3. 在 Codex 中选择 `windrecorder-memory` 技能；若未出现，重启 Codex。[技能目录说明](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

## 开始使用

直接告诉 Agent（将路径替换为你实际存放记录的 Windrecorder 目录）：

> 使用 $windrecorder-memory，记录目录是 E:\Windrecorder。帮我找上周关于项目甲的讨论，并注明记录时间和来源。

Agent 会先确认记录库，再按关键词、日期、前后文或旗标备注检索。查询不会修改原有记录。

其他 Agent：将完整文件夹放入其支持的 skill 目录；也可以直接让具备本地文件和命令权限的 Agent 读取
`E:\Windrecorder\extension\windrecorder-memory\SKILL.md` 后按说明检索。

更新 Windrecorder 后，重新复制 skill 文件夹即可更新技能。请保留 Windrecorder 安装目录，技能需要调用其中的查询程序。
