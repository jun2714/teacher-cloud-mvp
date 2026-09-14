from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "*").split(",") if x.strip()]

if not DEBUG:
    if SECRET_KEY in ("dev-secret-key-change-me", "replace-me", ""):
        raise ValueError("生产环境必须在 .env 中设置 SECRET_KEY")
    if ALLOWED_HOSTS == ["*"]:
        raise ValueError("生产环境必须在 .env 中设置 ALLOWED_HOSTS")

INSTALLED_APPS = [
    "simpleui",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "core.apps.CoreConfig",
    "learning.apps.LearningConfig",
    "community.apps.CommunityConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

sqlite_path = os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3"))
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sqlite_path}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = 80 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / "cache",
    }
}

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
}

SMS_ENABLED = os.getenv("SMS_ENABLED", "0") == "1"
SMS_ENDPOINT = os.getenv("SMS_ENDPOINT", "dysmsapi.aliyuncs.com").strip()
SMS_REGION_ID = os.getenv("SMS_REGION_ID", "cn-hangzhou").strip()
SMS_ACCESS_KEY_ID = os.getenv("SMS_ACCESS_KEY_ID", "").strip().strip('"').strip("'")
SMS_ACCESS_KEY_SECRET = os.getenv("SMS_ACCESS_KEY_SECRET", "").strip().strip('"').strip("'")
SMS_SIGN_NAME = os.getenv("SMS_SIGN_NAME", "").strip().strip('"').strip("'")
SMS_TEMPLATE_ID = os.getenv("SMS_TEMPLATE_ID", "").strip().strip('"').strip("'")

# 教研云管理后台（SimpleUI）
SIMPLEUI_HOME_INFO = False
SIMPLEUI_ANALYSIS = False
SIMPLEUI_DEFAULT_THEME = "admin.lte.css"
SIMPLEUI_LOGO = ""
SIMPLEUI_CONFIG = {
    "system_keep": True,
    "dynamic": True,
    "menus": [
        {
            "name": "教师与课程",
            "icon": "fas fa-chalkboard-teacher",
            "models": [
                {"name": "数据总览", "url": "/admin/overview/", "icon": "fas fa-chart-pie"},
                {"name": "教师一览", "url": "core/teacherprofile/", "icon": "fas fa-user-tie"},
            ],
        }
    ],
}
SIMPLEUI_ICON = {
    "核心数据": "fas fa-school",
    "教师档案": "fas fa-user-tie",
    "站内通知": "fas fa-bell",
    "教研学习": "fas fa-book-open",
    "教研笔记": "fas fa-sticky-note",
    "教研报告": "fas fa-file-alt",
    "教学设计": "fas fa-chalkboard-teacher",
    "听评课记录": "fas fa-headphones",
    "智能体对话": "fas fa-robot",
    "智能体消息": "fas fa-comment",
    "社区答疑": "fas fa-comments",
    "问题": "fas fa-question-circle",
    "回答": "fas fa-comment-dots",
    "认证和授权": "fas fa-shield-alt",
    "用户": "fas fa-user",
    "组": "fas fa-users",
}
