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

- `GET /api/notes/`
- `POST /api/notes/`
- `GET /api/notes/{id}/`
- `PUT/PATCH /api/notes/{id}/`
- `DELETE /api/notes/{id}/`
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

## 听评课助手

- `GET /api/lesson-reviews/`
- `POST /api/lesson-reviews/generate/`：支持 multipart 上传 `media_file`

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
