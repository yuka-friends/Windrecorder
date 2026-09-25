# 查询 API

统一调用：`python <skill>/scripts/query.py --root <Windrecorder安装目录> <命令> ...`。
`--root` 是数据源，脚本可位于开发仓库或复制后的 skill 目录。仓库内脚本使用同仓库的
`windrecorder.query_service.RecordQuery`；复制后的 skill 使用目标安装目录提供的查询模块。
脚本依赖这两个项目模块：`query_service.py`、`query_sql.py`，不要只把脚本单独拷走。

| 命令 | 必要参数 | 可选参数 | 用途 |
| --- | --- | --- | --- |
| `status` | 无 | 无 | 数据源、可用时间范围、记录数 |
| `search` | `--start --end` | `--query --exclude --limit --offset --text-limit` | 关键词与时间查询 |
| `context` | `--at` | `--seconds --limit --offset --text-limit` | 时间点前后文，默认各 300 秒 |
| `record` | `--id` | `--text-limit --text-offset` | 按引用 ID 读取原文，避免 rowid 被复用后读错记录 |
| `counts` | `--start --end` | `--by hour/day/month` | 按时间聚合索引条数，默认按天 |
| `notes` | `--start --end` | `--query --limit --offset --text-limit` | 读取旗标备注，不输出备注截图 |

日期/时间采用 ISO 本地时间，例如 `2026-09-15` 或 `2026-09-15 14:30:00`，
不接受时区后缀、UTC 偏移和小数秒。`end` 不包含在结果中。
仅日期参数从自然日零点开始，不自动叠加 WebUI 的自定义“一天起点”；需要其他边界时传完整时间。
`context` 的半径范围 1–86400 秒，包含两端对应秒。
`limit` 范围 1–200，`offset` 范围 0–100000，`text-limit` 范围 1–20000。
非常大的结果集应按日期拆分；小时统计最多一次查 366 天。

## 语义与分页

`search` 与 WebUI 共用 `query_sql.keyword_conditions`：词之间 AND，每词在 OCR/窗口标题间 OR；
`--exclude` 的词排除 OCR 中包含该词的记录。沿用 SQLite LIKE 规则，`%`、`_` 为通配符，
词内部的连字符按 WebUI 规则转为空格。此命令不自动展开相似汉字；由 agent 有目的地尝试别称。
空关键词对应浏览所有非 NULL OCR 记录。`notes` 使用不区分大小写的字面子串 AND，不解释通配符。

OCR 查询按月份、时间、rowid 顺序分页，备注按 CSV 中的原始行序分页。输出外层为：

```json
{"ok": true, "command": "search", "root": "<实际目录>", "result": {
  "records": [], "total_matches": 0, "has_more": false, "next_offset": null
}}
```

OCR 记录包含 `recorded_at`、`ocr_text`、`text_length`、`text_offset`、`text_truncated`、
`win_title`、`deep_linking`、`videofile_name`、`picturefile_name`、`video_offset_seconds`、
`database`、`rowid`、`record_id`。引用 ID 形如 `username_2026-09_wind.db:42:1789430400`，
直接沿用返回值，不手工拼接。`record` 返回 `record: null` 表示已删除、源库不可用或时间不再匹配。
`text_truncated: true` 时可将 `text_offset + 当前文本长度` 作为下次 `--text-offset`。
负的视频偏移表示旧记录本身的时间不一致，不能作为有效播放位置。

`notes` 返回 `source_type: flag_note`、`recorded_at`、`note`、`source_file`、`row_number`。
行号是 CSV 表头后的逻辑记录行号，修改备注文件后可能变化。备注超长时缩小日期范围并增大
`--text-limit`；最大长度仍不足时可根据明确的来源文件只读检查该条备注，避免输出整份截图列。

`counts` 返回有记录的 bucket 及 `total_records`；未返回的 bucket 为零。
`status` 的记录条数包含 NULL OCR 行，因此可能比空关键词搜索的总数大。
`db_directory_exists: false` 或 `shard_count: 0` 时先核对安装目录、用户名和实际数据路径。

## 与应用接口的关系

| agent API | 应用中的相应用途 |
| --- | --- |
| `RecordQuery.search` | `db_search_data` + `db_search_data_page_turner`；复用关键词 SQL，显式使用半开时间范围 |
| `RecordQuery.context/record` | 时间邻近查询、原始行读取；提供完整前后文与来源 ID |
| `RecordQuery.counts` | `db_get_record_counts`；复用同一统计 SQL |
| `RecordQuery.status` | `db_first_earliest_record_time` / `db_latest_record_time` / `db_num_records` |
| `RecordQuery.notes` | `flag_mark_note` 的 `datetime/note` CSV 数据 |

不直接导入应用的 `db_manager`、`config`、`flag_mark_note`，因为它们的初始化会创建或迁移文件。
查询服务使用 SQLite `mode=ro` 和 `query_only`，兼容已提交 WAL 数据及缺少
`win_title`/`deep_linking` 的旧表，不修改其 schema 或 rowid，也不加载 base64 缩略图。
单库内计数与分页共享读事务；多个库之间或两次翻页之间，录制进程仍可能新增记录。

图像语义检索属于应用的可选 `img_embed_manager`（uform/FAISS）能力；本入口未提供向量检索。
不要将关键词检索描述为语义检索，也不要为普通回忆查询自动安装模型或重建索引。
关键词不足以定位视觉内容时，明确说明限制，可使用 WebUI 中已安装的图像语义检索功能。
