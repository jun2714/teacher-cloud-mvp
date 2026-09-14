from django.contrib import admin
from .models import Question, Answer


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ["answer_type", "author", "content", "is_accepted", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "subject", "status", "ask_ai", "created_at"]
    list_filter = ["status", "subject", "grade", "ask_ai"]
    search_fields = ["title", "content", "author__username", "author__first_name", "author__email"]
    inlines = [AnswerInline]
    date_hierarchy = "created_at"
    list_per_page = 20


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ["question", "answer_type", "author", "is_accepted", "created_at"]
    list_filter = ["answer_type", "is_accepted"]
    search_fields = ["content", "question__title", "author__username"]
    date_hierarchy = "created_at"
    list_per_page = 20
