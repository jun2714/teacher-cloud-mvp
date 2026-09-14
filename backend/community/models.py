from django.contrib.auth.models import User
from django.db import models

class Question(models.Model):
    STATUS_CHOICES = [("pending", "待解答"), ("discussing", "讨论中"), ("solved", "已解答")]
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions", verbose_name="提问者")
    title = models.CharField("标题", max_length=220)
    content = models.TextField("内容")
    subject = models.CharField("学科", max_length=40, blank=True, default="")
    grade = models.CharField("年级", max_length=40, blank=True, default="")
    tags = models.JSONField("标签", default=list, blank=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default="pending")
    ask_ai = models.BooleanField("请求AI回答", default=True)
    liked_by = models.ManyToManyField(User, related_name="liked_questions", blank=True, verbose_name="点赞用户")
    accepted_answer = models.ForeignKey("Answer", on_delete=models.SET_NULL, null=True, blank=True, related_name="accepted_for", verbose_name="采纳回答")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "问题"
        verbose_name_plural = "问题"

    def __str__(self):
        return self.title

class Answer(models.Model):
    TYPE_CHOICES = [("teacher", "教师回答"), ("ai", "AI回答")]
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers", verbose_name="问题")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="answers", verbose_name="作者")
    answer_type = models.CharField("回答类型", max_length=20, choices=TYPE_CHOICES, default="teacher")
    content = models.TextField("内容")
    liked_by = models.ManyToManyField(User, related_name="liked_answers", blank=True, verbose_name="点赞用户")
    is_accepted = models.BooleanField("已采纳", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        ordering = ["-is_accepted", "created_at"]
        verbose_name = "回答"
        verbose_name_plural = "回答"
