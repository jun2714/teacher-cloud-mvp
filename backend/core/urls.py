from django.urls import path
from .views import asr_transcribe, change_password, me, my_stats, notice_list, notice_mark_read, notice_unread
from .auth_views import captcha, logout, register, send_sms_code, sms_login

urlpatterns = [
    path("auth/captcha/", captcha),
    path("auth/sms-code/", send_sms_code),
    path("auth/sms-login/", sms_login),
    path("auth/register/", register),
    path("auth/logout/", logout),
    path("me/", me),
    path("me/change-password/", change_password),
    path("me/stats/", my_stats),
    path("notices/", notice_list),
    path("notices/unread/", notice_unread),
    path("notices/mark-read/", notice_mark_read),
    path("asr/transcribe/", asr_transcribe),
]
