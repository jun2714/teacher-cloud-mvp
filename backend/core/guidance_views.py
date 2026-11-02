from urllib.parse import urlencode

from django.contrib import admin, messages
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .dashboard import DashboardFilters, PERMISSIONS, build_dashboard
from .guidance import (BODY_FIELDS, SPECS, FeedbackForm, decorate_feedback, display_name,
                       guidance_evidence, render_document, teacher_activity, visible_feedback)
from .models import InAppNotice, TeacherProfile, TeachingFeedback


def require_evidence_permission(request):
    if not request.user.has_perms(PERMISSIONS):
        raise PermissionDenied("需要教师档案及教研内容查看权限。")


def period(request):
    form = DashboardFilters(request.GET)
    if form.is_valid():
        return form.cleaned_data, ""
    default = DashboardFilters({})
    default.is_valid()
    return default.cleaned_data, "；".join(str(error) for errors in form.errors.values() for error in errors)


def page_context(request, **extra):
    return {**admin.site.each_context(request), "opts": None, "modern_reading": True, **extra}


def feedback_cards(request, **filters):
    qs = visible_feedback(request.user).filter(**filters)
    return [decorate_feedback(item, request.user) for item in qs[:30]]


@never_cache
@staff_member_required
def guidance_workbench(request):
    require_evidence_permission(request)
    filters, error = period(request)
    dashboard = build_dashboard(filters)
    guidance = guidance_evidence(request.user, dashboard)
    q, state = request.GET.get("q", "").strip()[:120], request.GET.get("state", "all")
    rows = dashboard["teachers"]
    if q:
        rows = [row for row in rows if q.casefold() in (row["name"] + row["school"] + row["department"]).casefold()]
    if state not in ("all", "pending", "followups", "inactive"):
        error = error or "请选择有效的跟进类型。"
    if state in ("pending", "followups") and not guidance["can_view"]:
        raise PermissionDenied("需要指导反馈查看权限。")
    if state in ("pending", "followups", "inactive"):
        rows = [row for row in rows if (row["days"] == 0 if state == "inactive" else row["pending" if state == "pending" else "followups"] > 0)]
    teacher_page = Paginator(rows, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "admin/guidance_workbench.html", page_context(request, title="教研指导工作台", guidance=guidance,
                  teacher_page=teacher_page, filters=filters, schools=dashboard["schools"], q=q, state=state,
                  pagination_query=params.urlencode(), error=error), status=400 if error else 200)


@never_cache
@staff_member_required
def teacher_workspace(request, profile_id):
    require_evidence_permission(request)
    profile = get_object_or_404(TeacherProfile.objects.select_related("user"), pk=profile_id, user__is_staff=False)
    filters, error = period(request)
    # A personal archive follows the chosen dates; a school filter must not hide its owner.
    filters["school"] = ""
    dashboard = build_dashboard(filters, teacher_id=profile.user_id)
    evidence = guidance_evidence(request.user, dashboard)
    activity, totals = teacher_activity(profile, filters)
    return render(request, "admin/teacher_workspace.html", page_context(request, title="教师成长档案", profile=profile,
                  teacher_name=display_name(profile.user), filters=filters, activity=activity, totals=totals,
                  usage=dashboard["teachers"][0] if dashboard["teachers"] else {}, guidance=evidence,
                  feedbacks=feedback_cards(request, teacher=profile.user), can_feedback=request.user.has_perms(["core.add_teachingfeedback", "core.view_teachingfeedback"]),
                  feedback_url=reverse("teaching_feedback_new") + "?" + urlencode({"teacher": profile.pk}),
                  can_edit_profile=request.user.has_perm("core.change_teacherprofile"), error=error), status=400 if error else 200)


def document_reading(request, obj, kind, model_admin):
    label = SPECS[kind][1]
    body = getattr(obj, BODY_FIELDS[kind])
    html, toc = render_document(body)
    profile = TeacherProfile.objects.filter(user=obj.author).first()
    metadata = [("学科" if getattr(obj, "subject", "") else "教师当前学科", getattr(obj, "subject", "") or (profile.subject if profile else "")),
                ("年级" if getattr(obj, "grade", "") else "教师当前年级", getattr(obj, "grade", "") or (profile.grade if profile else ""))]
    if kind == "plans":
        metadata += [("课题", obj.topic), ("课时", obj.class_hours)]
    elif kind == "reports":
        metadata += [("报告类型", obj.get_report_type_display())]
    elif kind == "notes":
        metadata += [("笔记分类", obj.get_category_display()), ("录入方式", obj.get_input_method_display())]
    elif kind == "reviews":
        metadata += [("授课教师", obj.course_teacher), ("材料类型", obj.get_material_kind_display())]
    sources = []
    if kind == "reports" and request.user.has_perm("learning.view_researchnote"):
        sources = [{"title": note.title, "url": reverse("admin:learning_researchnote_change", args=[note.pk])} for note in obj.source_notes.all()[:50]]
    details = []
    for field, name in (("student_context", "学情说明"), ("requirements", "设计要求"), ("transcript", "分析所用材料"), ("raw_text", "原始材料")):
        value = getattr(obj, field, "")
        if value:
            details.append({"title": name, "content": value})
    files = []
    for field in ("source_file", "audio_file", "media_file"):
        value = getattr(obj, field, None)
        if value:
            files.append({"name": value.name.rsplit("/", 1)[-1], "url": value.url})
    return render(request, "admin/document_reading.html", page_context(request, title=f"{label}详情", obj=obj, opts=obj._meta, original=obj,
                  kind=kind, content_label=label, author_name=display_name(obj.author), profile=profile, metadata=metadata,
                  document_html=html, toc=toc, sources=sources, source_details=details, files=files,
                  word_count=len(body or ""), can_edit=model_admin.has_change_permission(request, obj),
                  can_view_teacher=request.user.has_perms(PERMISSIONS),
                  can_feedback=not obj.author.is_staff and request.user.has_perms(["core.add_teachingfeedback", "core.view_teachingfeedback"]),
                  feedbacks=feedback_cards(request, teacher=obj.author, kind=kind, object_id=obj.pk),
                  feedback_url=reverse("teaching_feedback_new") + "?" + urlencode({"kind": kind, "object": obj.pk}),
                  list_url=reverse(f"admin:learning_{obj._meta.model_name}_changelist")))


def feedback_target(request, params=None):
    """Recipients and targets come from authorized records, never editable POST fields."""
    params = request.GET if params is None else params
    kind = params.get("kind", "teacher")
    if kind == "teacher":
        require_evidence_permission(request)
        profile = get_object_or_404(TeacherProfile.objects.select_related("user"), pk=params.get("teacher") if str(params.get("teacher", "")).isdigit() else None, user__is_staff=False)
        return profile.user, kind, None, f"{display_name(profile.user)}的阶段教研指导", reverse("teacher_workspace", args=[profile.pk])
    if kind not in SPECS:
        raise Http404
    model = SPECS[kind][2]
    obj = get_object_or_404(model.objects.select_related("author"), pk=params.get("object") if str(params.get("object", "")).isdigit() else None, author__is_staff=False)
    model_admin = admin.site._registry[model]
    if not model_admin.has_view_or_change_permission(request, obj):
        raise PermissionDenied
    return obj.author, kind, obj.pk, obj.title, reverse(f"admin:learning_{model._meta.model_name}_change", args=[obj.pk])


@never_cache
@staff_member_required
def feedback_editor(request, feedback_id=None):
    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])
    if not request.user.has_perm("core.view_teachingfeedback"):
        raise PermissionDenied
    with transaction.atomic():
        existing = None
        if feedback_id is not None:
            if not request.user.has_perm("core.change_teachingfeedback"):
                raise PermissionDenied
            existing = get_object_or_404(TeachingFeedback.objects.select_for_update().select_related("teacher"), pk=feedback_id, reviewer=request.user)
            if existing.status != "draft":
                raise PermissionDenied("已发送的指导不可改写，请补充一条新指导。")
            if existing.kind == "teacher":
                profile = get_object_or_404(TeacherProfile, user=existing.teacher)
                params = {"teacher": profile.pk}
            else:
                params = {"kind": existing.kind, "object": existing.object_id}
            # Revalidate access and ownership if the underlying document changed.
            teacher, kind, object_id, target_title, back_url = feedback_target(request, params)
            if teacher.pk != existing.teacher_id:
                raise PermissionDenied("关联成果已变更，请重新创建指导。")
        else:
            if not request.user.has_perm("core.add_teachingfeedback"):
                raise PermissionDenied
            teacher, kind, object_id, target_title, back_url = feedback_target(request)
        form = FeedbackForm(request.POST if request.method == "POST" else None, instance=existing)
        if request.method == "POST" and form.is_valid():
            action = request.POST.get("action")
            if action == "draft" and not request.user.has_perm("core.change_teachingfeedback"):
                raise PermissionDenied("保存并继续编辑指导草稿需要修改指导反馈权限。")
            if action not in ("draft", "send"):
                form.add_error(None, "请选择保存草稿或发送指导。")
            else:
                item = form.save(commit=False)
                item.teacher, item.reviewer, item.kind, item.object_id, item.target_title = teacher, request.user, kind, object_id, target_title
                if action == "send":
                    item.status, item.sent_at = "sent", timezone.now()
                item.save()
                if action == "send":
                    InAppNotice.objects.create(user=teacher, category="system", title="收到一条教研指导反馈", body=f"{display_name(request.user)}对《{target_title}》提出了建议，请查看并记录落实情况。"[:300], link=f"/guidance/{item.pk}")
                LogEntry.objects.log_actions(user_id=request.user.pk, queryset=TeachingFeedback.objects.filter(pk=item.pk), action_flag=CHANGE if existing else ADDITION,
                                            change_message="发送教研指导" if action == "send" else "保存指导草稿")
                messages.success(request, "指导已发送，老师可在“我的指导反馈”中查看。" if action == "send" else "草稿已保存，仅指导人可见。")
                return redirect(back_url + "#feedback-history")
    return render(request, "admin/feedback_editor.html", page_context(request, title="编辑指导草稿" if existing else "撰写教研指导", form=form,
                  teacher_name=display_name(teacher), teacher=teacher, target_title=target_title, back_url=back_url,
                  can_draft=request.user.has_perm("core.change_teachingfeedback")), status=400 if request.method == "POST" else 200)


@never_cache
@staff_member_required
def document_download(request, kind, object_id):
    if kind not in SPECS:
        raise Http404
    obj = get_object_or_404(SPECS[kind][2], pk=object_id)
    if not admin.site._registry[type(obj)].has_view_or_change_permission(request, obj):
        raise PermissionDenied
    from learning.views import _docx_response
    return _docx_response(getattr(obj, BODY_FIELDS[kind]), obj.title)
