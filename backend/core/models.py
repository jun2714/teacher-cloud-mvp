from django.contrib.auth.models import User
from django.db import models

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile", verbose_name="用户")
    school_name = models.CharField("学校", max_length=100, default="吴忠市吴忠中学")
    subject = models.CharField("学科", max_length=40, default="语文")
    grade = models.CharField("年级", max_length=40, default="高一")
    department = models.CharField("教研组", max_length=100, default="语文教研组")
    avatar_text = models.CharField("头像文字", max_length=4, blank=True, default="")
    avatar = models.ImageField("头像", upload_to="avatars/", blank=True, null=True)
    notify_lesson = models.BooleanField("教学生成提醒", default=True)
    notify_community = models.BooleanField("社区互动提醒", default=True)

    class Meta:
        verbose_name = "教师档案"
        verbose_name_plural = "教师档案"

    def __str__(self):
        return f"{self.user.username} - {self.school_name}"


class InAppNotice(models.Model):
    CATEGORY_CHOICES = [
        ("lesson", "教学设计"),
        ("report", "教研报告"),
        ("review", "听评课"),
        ("community", "社区互动"),
        ("system", "系统"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notices", verbose_name="用户")
    category = models.CharField("类型", max_length=20, choices=CATEGORY_CHOICES, default="system")
    title = models.CharField("标题", max_length=80)
    body = models.CharField("摘要", max_length=300, blank=True, default="")
    link = models.CharField("跳转", max_length=200, blank=True, default="")
    is_read = models.BooleanField("已读", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "站内通知"
        verbose_name_plural = "站内通知"

    def __str__(self):
        return self.title
