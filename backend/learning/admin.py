from django.contrib import admin
from .models import ResearchNote, ResearchReport, LessonPlan, LessonReview, AssistantChat, AssistantMessage


@admin.register(ResearchNote)
class ResearchNoteAdmin(admin.ModelAdmin):
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
class ResearchReportAdmin(admin.ModelAdmin):
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
class LessonPlanAdmin(admin.ModelAdmin):
    list_display = ["title", "author_name", "subject", "grade", "topic", "class_hours", "created_at"]
    list_filter = ["subject", "grade"]
    search_fields = ["title", "topic", "author__username", "author__first_name", "author__email"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(LessonReview)
class LessonReviewAdmin(admin.ModelAdmin):
    list_display = ["title", "author_name", "subject", "grade", "course_teacher", "created_at"]
    list_filter = ["subject", "grade"]
    search_fields = ["title", "course_teacher", "author__username", "author__first_name", "author__email"]
    date_hierarchy = "created_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(AssistantChat)
class AssistantChatAdmin(admin.ModelAdmin):
    list_display = ["title", "author_name", "updated_at"]
    search_fields = ["title", "author__username", "author__first_name"]
    date_hierarchy = "updated_at"
    list_select_related = ["author"]

    @admin.display(description="教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username


@admin.register(AssistantMessage)
class AssistantMessageAdmin(admin.ModelAdmin):
    list_display = ["chat", "role", "attachment_name", "created_at"]
    list_filter = ["role"]
    search_fields = ["content", "chat__title"]
    date_hierarchy = "created_at"
