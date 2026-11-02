from django.contrib import admin
from django.db.models import Count
from core.admin_reading import InteractionReadingAdminMixin
from .models import Question, Answer


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ["answer_type", "author", "content", "is_accepted", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Question)
class QuestionAdmin(InteractionReadingAdminMixin, admin.ModelAdmin):
    list_display = ["title", "author_name", "subject", "status", "answer_count", "created_at"]
    list_filter = ["status", "subject", "grade", "ask_ai"]
    search_fields = ["title", "content", "author__username", "author__first_name", "author__email"]
    inlines = [AnswerInline]
    date_hierarchy = "created_at"
    list_per_page = 20
    list_select_related = ["author"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(answers_n=Count("answers"))

    @admin.display(description="提问教师", ordering="author__first_name")
    def author_name(self, obj):
        return obj.author.first_name or obj.author.username

    @admin.display(description="回答数量", ordering="answers_n")
    def answer_count(self, obj):
        return obj.answers_n


@admin.register(Answer)
class AnswerAdmin(InteractionReadingAdminMixin, admin.ModelAdmin):
    list_display = ["question", "answer_type", "author", "is_accepted", "created_at"]
    list_filter = ["answer_type", "is_accepted"]
    search_fields = ["content", "question__title", "author__username"]
    date_hierarchy = "created_at"
    list_per_page = 20
    list_select_related = ["question", "author"]
