from django.contrib.auth.models import User
from django.db import models

class ResearchNote(models.Model):
    CATEGORY_CHOICES = [
        ("reflection", "教学反思"),
        ("learning", "学习心得"),
        ("lesson_review", "听评课"),
        ("collective", "集体备课"),
        ("idea", "教学灵感"),
    ]
    INPUT_CHOICES = [("text", "手动输入"), ("voice", "语音录入"), ("file", "文件上传")]

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="research_notes", verbose_name="作者")
    title = models.CharField("标题", max_length=200)
    content = models.TextField("内容")
    raw_text = models.TextField("原始文本", blank=True, default="")
    category = models.CharField("分类", max_length=30, choices=CATEGORY_CHOICES, default="reflection")
    input_method = models.CharField("录入方式", max_length=20, choices=INPUT_CHOICES, default="text")
    subject = models.CharField("学科", max_length=40, blank=True, default="")
    grade = models.CharField("年级", max_length=40, blank=True, default="")
    tags = models.JSONField("标签", default=list, blank=True)
    source_file = models.FileField("附件", upload_to="notes/files/%Y/%m/", blank=True, null=True)
    audio_file = models.FileField("音频", upload_to="notes/audio/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "教研笔记"
        verbose_name_plural = "教研笔记"

    def __str__(self):
        return self.title

class ResearchReport(models.Model):
    REPORT_CHOICES = [
        ("weekly", "教学周报"),
        ("monthly", "教学月报"),
        ("semester", "学期教研总结"),
        ("growth", "个人成长报告"),
        ("topic", "专题教学分析"),
    ]
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="research_reports", verbose_name="作者")
    title = models.CharField("标题", max_length=200)
    report_type = models.CharField("报告类型", max_length=30, choices=REPORT_CHOICES, default="weekly")
    content = models.TextField("内容")
    source_notes = models.ManyToManyField(ResearchNote, related_name="generated_reports", verbose_name="来源笔记")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "教研报告"
        verbose_name_plural = "教研报告"

    def __str__(self):
        return self.title

class LessonPlan(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_plans", verbose_name="作者")
    title = models.CharField("标题", max_length=200)
    subject = models.CharField("学科", max_length=40)
    grade = models.CharField("年级", max_length=40)
    topic = models.CharField("课题", max_length=200)
    class_hours = models.PositiveSmallIntegerField("课时", default=1)
    student_context = models.TextField("学情", blank=True, default="")
    requirements = models.TextField("要求", blank=True, default="")
    generated_content = models.TextField("生成内容")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "教学设计"
        verbose_name_plural = "教学设计"

    def __str__(self):
        return self.title

class LessonReview(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_reviews", verbose_name="作者")
    title = models.CharField("标题", max_length=200)
    subject = models.CharField("学科", max_length=40, blank=True, default="")
    grade = models.CharField("年级", max_length=40, blank=True, default="")
    course_teacher = models.CharField("授课教师", max_length=80, blank=True, default="")
    media_file = models.FileField("音视频", upload_to="lesson_reviews/%Y/%m/", blank=True, null=True)
    transcript = models.TextField("转写文本", blank=True, default="")
    report_content = models.TextField("评课报告")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "听评课记录"
        verbose_name_plural = "听评课记录"

    def __str__(self):
        return self.title


class AssistantChat(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assistant_chats", verbose_name="作者")
    title = models.CharField("标题", max_length=80, default="新对话")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "智能体对话"
        verbose_name_plural = "智能体对话"

    def __str__(self):
        return self.title


class AssistantMessage(models.Model):
    ROLE_CHOICES = [("user", "教师"), ("assistant", "助手")]
    chat = models.ForeignKey(AssistantChat, on_delete=models.CASCADE, related_name="messages", verbose_name="对话")
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES)
    content = models.TextField("内容")
    attachment = models.FileField("附件", upload_to="assistant/files/%Y/%m/", blank=True, null=True)
    attachment_name = models.CharField("附件名", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "智能体消息"
        verbose_name_plural = "智能体消息"

    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:20]}"
