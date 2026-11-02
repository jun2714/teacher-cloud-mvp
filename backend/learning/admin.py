from django.contrib import admin
from core.admin_reading import InteractionReadingAdminMixin, ReadingAdminMixin
from django.db.models import Count
from .models import ResearchNote, ResearchReport, LessonPlan, LessonReview, AssistantChat, AssistantMessage


@admin.register(ResearchNote)
class ResearchNoteAdmin(ReadingAdminMixin, admin.ModelAdmin):
    reading_kind = "notes"
    list_display = ["title", "author_name", "category", "input_method", "subject", "created_at"]
    list_filter = ["category", "input_method", "subject", "grade"]
    search_fields = ["title", "content", "author__username", "author__first_name", "author__email"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]
    list_per_page = 20

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(ResearchReport)
class ResearchReportAdmin(ReadingAdminMixin, admin.ModelAdmin):
    reading_kind = "reports"
    list_display = ["title", "author_name", "report_type", "created_at"]
    list_filter = ["report_type"]
    search_fields = ["title", "author__username", "author__first_name", "author__email"]
    filter_horizontal = ["source_notes"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(LessonPlan)
class LessonPlanAdmin(ReadingAdminMixin, admin.ModelAdmin):
    reading_kind = "plans"
    list_display = ["title", "author_name", "subject", "grade", "topic", "class_hours", "created_at"]
    list_filter = ["subject", "grade"]
    search_fields = ["title", "topic", "author__username", "author__first_name", "author__email"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(LessonReview)
class LessonReviewAdmin(ReadingAdminMixin, admin.ModelAdmin):
    reading_kind = "reviews"
    list_display = ["title", "author_name", "subject", "grade", "course_teacher", "created_at"]
    list_filter = ["subject", "grade"]
    search_fields = ["title", "course_teacher", "author__username", "author__first_name", "author__email"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(AssistantChat)
class AssistantChatAdmin(InteractionReadingAdminMixin, admin.ModelAdmin):
    list_display = ["title", "author_name", "message_count", "created_at", "updated_at"]
    search_fields = ["title", "author__username", "author__first_name"]
    date_hierarchy = "updated_at"
    list_select_related = ["author"]
    list_per_page = 20

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(messages_n=Count("messages"))

    @admin.display(description="消息数量", ordering="messages_n")
    def message_count(self, obj):
        return obj.messages_n

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(AssistantMessage)
class AssistantMessageAdmin(InteractionReadingAdminMixin, admin.ModelAdmin):
    list_display = ["chat", "role", "attachment_name", "created_at"]
    list_filter = ["role"]
    search_fields = ["content", "chat__title"]
    date_hierarchy = "created_at"
    list_select_related = ["chat", "chat__author"]
    list_per_page = 20
