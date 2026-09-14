from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from .models import InAppNotice, TeacherProfile


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = [
        "display_name", "phone", "school_name", "subject", "grade",
        "plans_count", "reviews_count", "notes_count", "reports_count", "questions_count", "last_login",
    ]
    list_filter = ["school_name", "subject", "grade"]
    search_fields = ["user__username", "user__first_name", "user__email", "school_name", "department"]
    list_per_page = 30
    readonly_fields = ["activity_summary"]
    fields = [
        "user", "school_name", "department", "subject", "grade",
        "avatar", "avatar_text", "notify_lesson", "notify_community", "activity_summary",
    ]
    autocomplete_fields = []

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["user", "activity_summary"]
        return ["activity_summary"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .filter(user__is_superuser=False)
            .annotate(
                notes_n=Count("user__research_notes", distinct=True),
                plans_n=Count("user__lesson_plans", distinct=True),
                reviews_n=Count("user__lesson_reviews", distinct=True),
                reports_n=Count("user__research_reports", distinct=True),
                questions_n=Count("user__questions", distinct=True),
            )
        )

    @admin.display(description="姓名", ordering="user__first_name")
    def display_name(self, obj):
        return obj.user.first_name or obj.user.username

    @admin.display(description="手机号", ordering="user__email")
    def phone(self, obj):
        return obj.user.email or "—"

    @admin.display(description="教案", ordering="plans_n")
    def plans_count(self, obj):
        return getattr(obj, "plans_n", obj.user.lesson_plans.count())

    @admin.display(description="听评课", ordering="reviews_n")
    def reviews_count(self, obj):
        return getattr(obj, "reviews_n", obj.user.lesson_reviews.count())

    @admin.display(description="笔记", ordering="notes_n")
    def notes_count(self, obj):
        return getattr(obj, "notes_n", obj.user.research_notes.count())

    @admin.display(description="报告", ordering="reports_n")
    def reports_count(self, obj):
        return getattr(obj, "reports_n", obj.user.research_reports.count())

    @admin.display(description="提问", ordering="questions_n")
    def questions_count(self, obj):
        return getattr(obj, "questions_n", obj.user.questions.count())

    @admin.display(description="最近登录", ordering="user__last_login")
    def last_login(self, obj):
        value = obj.user.last_login
        return value.strftime("%Y-%m-%d %H:%M") if value else "从未登录"

    @admin.display(description="教学活动汇总")
    def activity_summary(self, obj):
        if not obj or not obj.pk:
            return "保存后可查看该教师的课程记录"
        user = obj.user
        bits = [
            f"教学设计 {user.lesson_plans.count()} 份",
            f"听评课 {user.lesson_reviews.count()} 份",
            f"教研笔记 {user.research_notes.count()} 篇",
            f"教研报告 {user.research_reports.count()} 份",
            f"社区提问 {user.questions.count()} 条",
            f"智能对话 {user.assistant_chats.count()} 个",
        ]
        return " · ".join(bits)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        extra_context["teacher_records"] = self._records(obj) if obj else []
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def _records(self, profile):
        user = profile.user
        groups = [
            ("教学设计", "learning", "lessonplan", user.lesson_plans.all(), lambda i: f"{i.subject} · {i.grade} · {i.topic}"),
            ("听评课记录", "learning", "lessonreview", user.lesson_reviews.all(), lambda i: f"{i.subject} · {i.grade} · {i.course_teacher or '未填授课教师'}"),
            ("教研笔记", "learning", "researchnote", user.research_notes.all(), lambda i: i.get_category_display()),
            ("教研报告", "learning", "researchreport", user.research_reports.all(), lambda i: i.get_report_type_display()),
            ("社区提问", "community", "question", user.questions.all(), lambda i: i.get_status_display()),
            ("智能体对话", "learning", "assistantchat", user.assistant_chats.all(), lambda i: f"{i.messages.count()} 条消息"),
        ]
        result = []
        for title, app, model, qs, extra_fn in groups:
            rows = []
            for item in qs[:40]:
                try:
                    url = reverse(f"admin:{app}_{model}_change", args=[item.pk])
                except Exception:
                    url = ""
                created = getattr(item, "created_at", None) or getattr(item, "updated_at", None)
                rows.append({
                    "title": item.title,
                    "extra": extra_fn(item),
                    "when": created.strftime("%Y-%m-%d %H:%M") if created else "",
                    "url": url,
                })
            result.append({"title": title, "count": qs.count(), "rows": rows})
        return result


@admin.register(InAppNotice)
class InAppNoticeAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "category", "is_read", "created_at"]
    list_filter = ["category", "is_read"]
    search_fields = ["title", "body", "user__username", "user__first_name"]
    date_hierarchy = "created_at"
