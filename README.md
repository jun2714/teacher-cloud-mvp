# 教研云 H5 MVP

这是一个按照最新 UI 与业务说明搭建的可运行全栈起步项目，包含：

- 教学设计辅助
- 听评课助手
- 教研笔记：手动输入、浏览器语音录入、文件上传
- 选择多篇笔记生成教研报告
- 校内答疑交流：发布、点赞、回复、AI 参考回答、提问者标记已解答
- 我的页面与个人统计
- Django Admin 管理后台

## 技术栈

- 前端：Vue 3、Vite、Pinia、Vue Router、Axios
- 后端：Python、Django 5.2 LTS、Django REST Framework
- 数据库：默认 SQLite，正式部署可切换 PostgreSQL
- AI：默认 Mock 模式；支持配置 OpenAI 兼容接口

## 快速启动

### 1. 后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python manage.py makemigrations core learning community
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8001
```

后端地址：`http://127.0.0.1:8001`（必须是 8001，前端开发代理指向这里）

管理后台：`http://127.0.0.1:8001/admin/`

演示账号：

- 教师账号：`teacher`
- 密码：`teacher123`
- 管理员账号：`admin`
- 密码：`admin123456`

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:6060`

正式上线（Nginx + Gunicorn 或 Docker）见 [docs/部署说明.md](docs/部署说明.md)。

## AI 接口配置

复制后端环境变量示例：

```bash
cd backend
cp .env.example .env
```

默认：

```env
AI_PROVIDER=mock
```

接入 OpenAI 兼容接口时：

```env
AI_PROVIDER=openai_compatible
AI_BASE_URL=https://你的接口地址/v1
AI_API_KEY=你的密钥
AI_MODEL=模型名称
```

当前项目会通过后端统一调用 AI，前端不会暴露密钥。

## 当前 MVP 的边界

- 教学设计、报告、AI答疑和听评课分析默认使用本地 Mock 内容，配置兼容接口后可真实生成。
- 听评课页面支持上传音视频和录入转写文本；真正的音视频转文字需要再接入讯飞、腾讯云、阿里云等 ASR 服务。
- 浏览器语音录入使用 Web Speech API，Chrome/Edge 支持较好；不支持时可以手动输入或上传文件。
- 当前是单校 MVP，社区内容默认所有登录教师可见。

## 推荐下一步

1. 接入真实 AI 和语音识别接口。
2. 将 SQLite 切换 PostgreSQL。
3. 增加学校、教研组与角色权限。
4. 增加对象存储、操作日志、敏感信息提示和数据备份。
