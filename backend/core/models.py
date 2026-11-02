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


class TeachingFeedback(models.Model):
    KIND_CHOICES = [("teacher", "阶段指导"), ("plans", "教学设计"), ("reviews", "听评课"), ("notes", "教研笔记"), ("reports", "教研报告")]
    STATUS_CHOICES = [("draft", "草稿"), ("sent", "待落实"), ("done", "已落实")]
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teaching_feedback", verbose_name="教师")
    reviewer = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="given_teaching_feedback", verbose_name="指导人")
    kind = models.CharField("指导类型", max_length=16, choices=KIND_CHOICES, default="teacher")
    object_id = models.PositiveBigIntegerField("关联成果编号", null=True, blank=True)
    target_title = models.CharField("指导对象", max_length=200)
    strengths = models.TextField("值得肯定", blank=True, default="")
    suggestions = models.TextField("改进建议")
    action_plan = models.TextField("下一步行动", blank=True, default="")
    follow_up_date = models.DateField("跟进日期", blank=True, null=True)
    status = models.CharField("状态", max_length=12, choices=STATUS_CHOICES, default="draft")
    teacher_reply = models.TextField("教师落实说明", blank=True, default="")
    sent_at = models.DateTimeField("发送时间", blank=True, null=True)
    completed_at = models.DateTimeField("落实时间", blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "教研指导反馈"
        verbose_name_plural = "教研指导反馈"
        indexes = [models.Index(fields=["teacher", "status"], name="feedback_teacher_status"), models.Index(fields=["kind", "object_id"], name="feedback_target")]
        constraints = [models.CheckConstraint(condition=(models.Q(kind="teacher", object_id__isnull=True) | models.Q(kind__in=["plans", "reviews", "notes", "reports"], object_id__isnull=False)), name="feedback_target_consistent")]

    def __str__(self):
        return self.target_title
