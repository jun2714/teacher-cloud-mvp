from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import QuestionViewSet, AnswerViewSet

router = DefaultRouter()
router.register("questions", QuestionViewSet, basename="question")
router.register("answers", AnswerViewSet, basename="answer")
urlpatterns = [path("", include(router.urls))]
