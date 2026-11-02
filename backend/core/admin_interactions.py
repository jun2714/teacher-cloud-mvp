"""Permission-aware reading views for saved conversations and community exchanges."""
from django.contrib import admin
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from community.models import Answer, Question
from learning.models import AssistantChat, AssistantMessage
from .dashboard import PERMISSIONS
from .guidance import display_name, render_document
from .guidance_views import page_context
from .models import TeacherProfile


def admin_url(obj, action="change"):
    return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_{action}", args=[obj.pk] if action == "change" else [])


def allowed(request, obj):
    return admin.site._registry[type(obj)].has_view_or_change_permission(request, obj)


def entry(request, obj):
    is_message = isinstance(obj, AssistantMessage)
    is_ai = obj.role == "assistant" if is_message else obj.answer_type == "ai"
    author = obj.chat.author if is_message and not is_ai else getattr(obj, "author", None)
    name = "智能助手" if is_ai else (display_name(author) if author else "原作者")
    return {
        "pk": obj.pk, "author": name, "ai": is_ai,
        "label": ("智能助手回复" if is_ai else "教师提问") if is_message else ("AI 参考回答" if is_ai else "教师回答"),
        "html": render_document(obj.content, anchor_prefix=f"entry-{obj._meta.model_name}-{obj.pk}")[0],
        "when": obj.created_at,
        "accepted": not is_message and (obj.is_accepted or obj.question.accepted_answer_id == obj.pk),
        "attachment": getattr(obj, "attachment", None),
        "attachment_name": getattr(obj, "attachment_name", "") or "查看附件",
        "url": admin_url(obj),
    }


def interaction_reading(request, obj, model_admin):
    is_chat, is_message = isinstance(obj, AssistantChat), isinstance(obj, AssistantMessage)
    is_question = isinstance(obj, Question)
    label = "智能体对话" if is_chat else "智能体消息" if is_message else "社区提问" if is_question else "社区回答"
    author = obj.author if is_chat or is_question else obj.chat.author if is_message else obj.author
    profile = TeacherProfile.objects.filter(user=author).first() if author else None
    context = page_context(request, title=f"{label}详情", opts=obj._meta, original=obj, obj=obj,
                           content_label=label, is_chat=is_chat, is_question=is_question,
                           author_name=display_name(author) if author else "智能助手" if obj.answer_type == "ai" else "原作者",
                           profile=profile, can_edit=model_admin.has_change_permission(request, obj),
                           list_url=admin_url(obj, "changelist"), metadata=[], statistics=[], tags=[],
                           can_view_teacher=bool(profile and not author.is_staff and request.user.has_perms(PERMISSIONS)))
    if is_chat:
        child_admin = admin.site._registry[AssistantMessage]
        can_read = child_admin.has_view_or_change_permission(request)
        qs = child_admin.get_queryset(request).filter(chat=obj).select_related("chat__author").order_by("created_at", "pk")
        context.update(record_title=obj.title, thread_title="完整对话记录", thread_hint="按时间顺序展示教师提问与助手回复，附件随消息保留。", can_read_entries=can_read)
        if can_read:
            counts = dict(qs.order_by().values("role").annotate(n=Count("pk")).values_list("role", "n"))
            context["statistics"] = [("消息总数", sum(counts.values())), ("教师提问", counts.get("user", 0)), ("助手回复", counts.get("assistant", 0))]
        context["metadata"] = [("最近更新", timezone.localtime(obj.updated_at).strftime("%Y-%m-%d %H:%M"))]
        context["observation"] = "留意教师反复追问的知识点、活动设计与评价问题，结合实际教学记录提供支持。助手回复仅供参考，请结合教材和学情核验。"
    elif is_question:
        child_admin = admin.site._registry[Answer]
        can_read = child_admin.has_view_or_change_permission(request)
        qs = child_admin.get_queryset(request).filter(question=obj).select_related("author", "question").order_by("-is_accepted", "created_at", "pk")
        context.update(record_title=obj.title, thread_title="回答与交流", thread_hint="区分教师经验与 AI 参考回答，保留采纳标记。", can_read_entries=can_read,
                       intro_html=render_document(obj.content, anchor_prefix="question-body")[0], status=obj.get_status_display(),
                       tags=[str(tag)[:60] for tag in obj.tags[:20]] if isinstance(obj.tags, list) else [])
        context["metadata"] = [("学科", obj.subject), ("年级", obj.grade), ("请求 AI 回答", "是" if obj.ask_ai else "否")]
        if can_read:
            context["statistics"] = [("回答数量", qs.count()), ("教师回答", qs.filter(answer_type="teacher").count()), ("AI 回答", qs.filter(answer_type="ai").count())]
        context["observation"] = "把共同的教学困惑转为集体备课议题。优先关注已采纳的实践经验，结合本校学情判断适用性。"
    else:
        parent = obj.chat if is_message else obj.question
        context.update(record_title=(obj.get_role_display() + "消息") if is_message else obj.get_answer_type_display(),
                       thread_title="消息内容" if is_message else "回答内容", thread_hint="", can_read_entries=True,
                       entries=[entry(request, obj)], observation="阅读时结合原始问题与课堂情境理解，避免将 AI 参考内容直接视为教学结论。")
        if allowed(request, parent):
            context.update(parent_url=admin_url(parent), parent_title=parent.title,
                           parent_label="查看完整对话" if is_message else "查看原问题与全部回答")
    if is_chat or is_question:
        if can_read:
            page = Paginator(qs, 30 if is_chat else 10).get_page(request.GET.get("page"))
            context.update(thread_page=page, entries=[entry(request, record) for record in page if child_admin.has_view_or_change_permission(request, record)])
        else:
            context["entries"] = []
    return render(request, "admin/interaction_reading.html", context)
