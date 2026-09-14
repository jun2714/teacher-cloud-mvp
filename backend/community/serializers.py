from rest_framework import serializers
from core.serializers import UserSerializer
from .models import Question, Answer

class AnswerSerializer(serializers.ModelSerializer):
    author_info = UserSerializer(source="author", read_only=True)
    like_count = serializers.IntegerField(source="liked_by.count", read_only=True)
    is_liked = serializers.SerializerMethodField()
    answer_type_label = serializers.CharField(source="get_answer_type_display", read_only=True)

    class Meta:
        model = Answer
        fields = ["id", "author_info", "answer_type", "answer_type_label", "content", "like_count", "is_liked", "is_accepted", "created_at"]
        read_only_fields = ["answer_type", "is_accepted"]

    def get_is_liked(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.liked_by.filter(id=request.user.id).exists())

class QuestionSerializer(serializers.ModelSerializer):
    author_info = UserSerializer(source="author", read_only=True)
    answers = AnswerSerializer(many=True, read_only=True)
    answer_count = serializers.IntegerField(source="answers.count", read_only=True)
    like_count = serializers.IntegerField(source="liked_by.count", read_only=True)
    is_liked = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_owner = serializers.SerializerMethodField()
    ai_failed = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id", "author_info", "title", "content", "subject", "grade", "tags", "status",
            "status_label", "ask_ai", "answers", "answer_count", "like_count", "is_liked",
            "accepted_answer", "is_owner", "ai_failed", "created_at", "updated_at",
        ]
        read_only_fields = ["status", "accepted_answer"]

    def get_is_liked(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.liked_by.filter(id=request.user.id).exists())

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.author_id == request.user.id)

    def get_ai_failed(self, obj):
        answers = obj.answers.all()
        return any(
            item.answer_type == "ai" and "暂时无法生成" in (item.content or "")
            for item in answers
        )
