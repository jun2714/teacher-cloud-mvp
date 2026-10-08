# API 概览

所有业务接口默认需要 JWT：

```http
Authorization: Bearer <access_token>
```

## 登录与个人信息

- `POST /api/auth/token/`：登录
- `POST /api/auth/token/refresh/`：刷新 Token
- `GET /api/me/`：当前教师
- `GET /api/me/stats/`：个人统计

## 教研笔记与报告

- `GET /api/notes/`：返回当前用户全部笔记数组，与无分页控件的笔记列表保持一致。
- `POST /api/notes/`
- `GET /api/notes/{id}/`
- `PUT/PATCH /api/notes/{id}/`
- `DELETE /api/notes/{id}/`
- `POST /api/notes/extract/`：multipart `file`（兼容 `source_file`），返回 `{filename, excerpt, warnings}`。支持 `.docx`、PDF（含扫描件）、JPG/PNG/WEBP，以及 TXT/MD/CSV/JSON；文档限 8MB / 60000 字，PDF 页数限制同听评课。空内容、损坏、超限返回 400；视觉服务不可用返回 502。
- 笔记附件先提取/转写，老师核对后再保存；保存接口以 `content` 为准，不再重新识别或追加原文。可用 `raw_text` 保留原识别文本，`source_file` / `audio_file` 保留附件，`tags` 使用字符串数组（multipart 时为 JSON 数组文本）。
- 笔记页面录音复用听评课录音组件，停止后调用 `/api/asr/transcribe/`，支持回听、下载、重试；正文可继续修改。清除待保存附件保留已导入的文字；重新导入会追加，每类附件保存最后一份。
- `GET /api/reports/`
- `POST /api/reports/generate/`

生成报告示例：

```json
{
  "title": "本周教学反思报告",
  "report_type": "weekly",
  "note_ids": [1, 2, 3]
}
```

## 教学设计辅助

- `GET /api/lesson-plans/`
- `POST /api/lesson-plans/generate/`

个人教学设计生成完成页、历史详情页默认展示 PPT，保留“完整正文”、正文编辑及 Word 下载。前端按 Markdown 章节和表格行分页，同一份布局用于浏览器预览与 `.pptx` 导出，文字为可编辑文本框。支持三套内置配色、章节跳转、方向键/触摸翻页和全屏展示；正文保存后重新分页。PPT 导出使用浏览器按需加载的 `pptxgenjs`，无需额外后端接口或 AI 调用。目前内置样式为应用定义版式；用户提供的 `.pptx` 模板需另行适配，不支持任意模板直接上传套用。

## 听评课助手

- `GET /api/lesson-reviews/`
- `POST /api/lesson-reviews/generate/`：支持 multipart 上传 `media_file`
- `POST /api/lesson-reviews/extract/`：JWT + multipart `file`，识别单个 `.docx` / `.pdf` / `.jpg` / `.jpeg` / `.png` / `.webp`，返回 `{filename, text, warnings}`。文档/图片限 8MB；PDF 最多 40 页、需视觉识别页面最多 10 页；不静默截断。无内容/损坏/超限为 400，视觉服务未配置或不可用为 502。
- 前端按选取顺序调用识别接口，将结果追加到可编辑正文；文档原文件仅用于识别，生成时保存核对后的正文。
- 生成接口增加 `material_kind`：`lesson_plan`（教案）、`classroom`（实录，默认，兼容旧客户端）、`mixed`（对照）。`transcript` 为核对后的材料正文，限 60000 字；没有正文时仍支持旧版 `media_file` 转写。
- `POST /api/asr/transcribe/`：multipart `file`，沿用百炼语音转写。页面内录音停止后上传完整录音（WebM/MP4/Ogg，按浏览器支持情况选择），不是逐字流式转写。
- 多段录音与音视频的文字合并分析；生成时保留列表中最后一段成功识别的音视频原文件。页面录音支持本地回听和下载，刷新前可自行保存。

## 疑惑交流

- `GET /api/questions/`
- `POST /api/questions/`
- `GET /api/questions/{id}/`
- `POST /api/questions/{id}/answer/`
- `POST /api/questions/{id}/toggle-like/`
- `POST /api/questions/{id}/mark-solved/`
- `POST /api/answers/{id}/toggle-like/`

问题状态：

- `pending`：待解答
- `discussing`：讨论中
- `solved`：已解答

只有提问者可以执行 `mark-solved`，并可传入 `answer_id` 采纳满意回答。
