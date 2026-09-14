from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta

from community.models import Answer, Question
from learning.models import AssistantChat, LessonPlan, LessonReview, ResearchNote, ResearchReport
from .models import TeacherProfile


@staff_member_required
def teacher_overview(request):
    teachers = (
        TeacherProfile.objects.filter(user__is_superuser=False)
        .select_related("user")
        .annotate(
            notes_count=Count("user__research_notes", distinct=True),
            plans_count=Count("user__lesson_plans", distinct=True),
            reviews_count=Count("user__lesson_reviews", distinct=True),
            reports_count=Count("user__research_reports", distinct=True),
            questions_count=Count("user__questions", distinct=True),
            chats_count=Count("user__assistant_chats", distinct=True),
        )
        .order_by("-user__last_login", "-id")
    )
    week_ago = timezone.now() - timedelta(days=7)
    stats = {
        "teachers": teachers.count(),
        "new_week": User.objects.filter(is_superuser=False, date_joined__gte=week_ago).count(),
        "plans": LessonPlan.objects.count(),
        "reviews": LessonReview.objects.count(),
        "notes": ResearchNote.objects.count(),
        "reports": ResearchReport.objects.count(),
        "questions": Question.objects.count(),
        "answers": Answer.objects.filter(answer_type="teacher").count(),
        "chats": AssistantChat.objects.count(),
    }
    return render(request, "admin/teacher_overview.html", {
        "title": "教师与课程总览",
        "stats": stats,
        "teachers": teachers,
    })
