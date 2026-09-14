from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    ResearchNoteViewSet,
    ResearchReportViewSet,
    LessonPlanViewSet,
    LessonReviewViewSet,
    AssistantChatViewSet,
)

router = DefaultRouter()
router.register("notes", ResearchNoteViewSet, basename="note")
router.register("reports", ResearchReportViewSet, basename="report")
router.register("lesson-plans", LessonPlanViewSet, basename="lesson-plan")
router.register("lesson-reviews", LessonReviewViewSet, basename="lesson-review")
router.register("assistant-chats", AssistantChatViewSet, basename="assistant-chat")

urlpatterns = [path("", include(router.urls))]
