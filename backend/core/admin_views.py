import csv
from io import StringIO

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin

from django.contrib.auth.models import Group, User

from community.models import Answer, Question
from learning.models import AssistantChat, AssistantMessage, LessonPlan, LessonReview, ResearchNote, ResearchReport
from .dashboard import DashboardFilters, PERMISSIONS, build_dashboard
from .models import InAppNotice, TeacherProfile


PAGE_DESCRIPTIONS = {
    "archives": "整理研修过程与成果 · 生成批次及个人报告 · 支持预览和批量导出",
    "guidance": "从教研记录发现支持需求 · 阅读教学成果 · 给予具体指导并跟进落实",
    "overview": "数据驱动教研发展 · 精准洞察教师成长 · 提升学校教学质量",
    "reviews": "汇总全校听评课观察与 AI 诊断报告 · 支撑课堂教学持续改进",
    "plans": "沉淀个人教学设计成果 · 共享各学科优秀备课方案",
    "reports": "归档周报、月报与跟岗研修总结 · 追踪教师阶段性成长",
    "notes": "记录日常听评课、教学反思与集体备课心得 · 积累鲜活教研素材",
    "chats": "查看智能体教研问答与辅助对话记录 · 了解教师高频教研诉求",
    "questions": "管理教师社区提问与同伴互助解答 · 营造校本协作教研氛围",
    "teachers": "管理全校教师档案、任教学科年级与个人教研产出明细",
    "core": "维护教师档案、站内通知与平台基础业务数据",
    "manage": "配置全平台数据模型、后台管理员权限与系统运行参数",
}


def resolve_admin_nav(path: str) -> str:
    if path.startswith("/admin/archives/"):
        return "archives"
    if path.startswith("/admin/teaching/"):
        return "guidance"
    if path.startswith("/admin/overview"):
        return "overview"
    if "/learning/lessonreview" in path:
        return "reviews"
    if "/learning/lessonplan" in path:
        return "plans"
    if "/learning/researchreport" in path:
        return "reports"
    if "/learning/researchnote" in path:
        return "notes"
    if "/learning/assistantchat" in path or "/learning/assistantmessage" in path:
        return "chats"
    if "/community/" in path:
        return "questions"
    if "/core/teacherprofile" in path:
        return "teachers"
    if path.rstrip("/") == "/admin/core" or "/core/inappnotice" in path:
        return "core"
    return "manage"


def admin_shell_context(request):
    path = getattr(request, "path", "") or ""
    if not path.startswith("/admin"):
        return {}
    user = getattr(request, "user", None)
    nav = resolve_admin_nav(path)
    unread_count = 0
    notices = []
    shell_counts = {}
    if user and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False):
        qs = InAppNotice.objects.filter(user=user)
        unread_count = qs.filter(is_read=False).count()
        notices = list(qs[:5])
        if path.rstrip("/") in ("/admin", "/admin/core", "/admin/learning", "/admin/community"):
            shell_counts = {
                "teachers": TeacherProfile.objects.filter(user__is_staff=False).count(),
                "reviews": LessonReview.objects.count(),
                "plans": LessonPlan.objects.count(),
                "reports": ResearchReport.objects.count(),
                "notes": ResearchNote.objects.count(),
                "chats": AssistantChat.objects.count(),
                "messages": AssistantMessage.objects.count(),
                "questions": Question.objects.count(),
                "answers": Answer.objects.count(),
                "notices": InAppNotice.objects.count(),
                "users": User.objects.count(),
                "groups": Group.objects.count(),
            }
    return {
        "admin_active_nav": nav,
        "admin_page_subtitle": PAGE_DESCRIPTIONS.get(nav, PAGE_DESCRIPTIONS["manage"]),
        "unread_count": unread_count,
        "notices": notices,
        "shell_counts": shell_counts,
    }


def admin_landing(request):
    if request.GET.get("manage") == "1" or not request.user.has_perms(PERMISSIONS):
        return admin.site.index(request)
    return redirect("teacher_overview")


def dashboard_context(request):
    if not request.user.has_perms(PERMISSIONS):
        raise PermissionDenied("查看驾驶舱需要教师档案及相关教研记录的查看权限。")
    form = DashboardFilters(request.GET)
    if not form.is_valid():
        return None, "；".join(str(message) for messages in form.errors.values() for message in messages)
    return build_dashboard(form.cleaned_data), ""


@never_cache
@xframe_options_sameorigin
@staff_member_required
def teacher_overview(request):
    context, error = dashboard_context(request)
    if error:
        default = DashboardFilters({})
        default.is_valid()
        context = build_dashboard(default.cleaned_data)
    notices = InAppNotice.objects.filter(user=request.user)
    context.update({"title": "教学教研数据驾驶舱", "error": error,
                    "unread_count": notices.filter(is_read=False).count(), "notices": notices[:5],
                    "export_url": reverse("teacher_overview_export") + "?" + request.GET.urlencode()})
    from .guidance import guidance_evidence
    context["guidance"] = guidance_evidence(request.user, context)
    return render(request, "admin/teacher_overview.html", context, status=400 if error else 200)


@never_cache
@staff_member_required
def teacher_overview_export(request):
    context, error = dashboard_context(request)
    if error:
        return HttpResponse(error, status=400, content_type="text/plain; charset=utf-8")
    output = StringIO()
    writer = csv.writer(output)

    def row(values):
        # Keep user-controlled titles/names from becoming spreadsheet formulas.
        writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for value in values])

    f = context["filters"]
    row(["教学教研数据驾驶舱", f["start"].isoformat(), f["end"].isoformat(), f.get("school") or "全校"])
    row(["统计口径", "教师人数为截止日人数；内容统计按所选日期；较上期为此前等长时段差值。"])
    row(["活跃口径", context["activity_help"]])
    row(["指标", "数量", "增减", "比较方式"])
    for stat in context["stats"]:
        row([stat["label"], stat["value"], stat["delta"], stat["comparison"]])
    row([])
    row(["教师姓名", "学校", "教研组", "内容数量", "活跃天数", "最近登录"])
    for teacher in context["teachers"]:
        when = timezone.localtime(teacher["last_login"]).strftime("%Y-%m-%d %H:%M") if teacher["last_login"] else "从未登录"
        row([teacher["name"], teacher["school"], teacher["department"], teacher["count"], teacher["days"], when])
    row([])
    row(["日期", "活跃教师数", "发布内容数"])
    for point in context["series"]:
        row([point["date"], point["active"], point["content"]])
    row([])
    row(["学科", "内容数量", "教师人数"])
    for subject in context["subjects"]:
        row([subject["name"], subject["count"], subject["teachers"]])
    response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="teaching-dashboard-{f["start"]}-{f["end"]}.csv"'
    return response
