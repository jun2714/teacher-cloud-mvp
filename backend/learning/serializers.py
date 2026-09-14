from rest_framework import serializers
from .models import ResearchNote, ResearchReport, LessonPlan, LessonReview, AssistantChat, AssistantMessage

class ResearchNoteSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    input_method_label = serializers.CharField(source="get_input_method_display", read_only=True)
    source_file_url = serializers.SerializerMethodField()
    audio_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ResearchNote
        fields = [
            "id", "title", "content", "raw_text", "category", "category_label",
            "input_method", "input_method_label", "subject", "grade", "tags",
            "source_file", "source_file_url", "audio_file", "audio_file_url",
            "created_at", "updated_at",
        ]
        extra_kwargs = {"source_file": {"write_only": True}, "audio_file": {"write_only": True}}

    def _url(self, obj, field):
        f = getattr(obj, field)
        if not f:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(f.url) if request else f.url

    def get_source_file_url(self, obj):
        return self._url(obj, "source_file")

    def get_audio_file_url(self, obj):
        return self._url(obj, "audio_file")

class ResearchReportSerializer(serializers.ModelSerializer):
    source_note_ids = serializers.PrimaryKeyRelatedField(source="source_notes", many=True, read_only=True)
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)

    class Meta:
        model = ResearchReport
        fields = ["id", "title", "report_type", "report_type_label", "content", "source_note_ids", "created_at"]


class ResearchReportListSerializer(ResearchReportSerializer):
    class Meta(ResearchReportSerializer.Meta):
        fields = ["id", "title", "report_type", "report_type_label", "source_note_ids", "created_at"]


class LessonPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPlan
        fields = "__all__"
        read_only_fields = ["author", "generated_content", "created_at"]


class LessonPlanListSerializer(LessonPlanSerializer):
    class Meta(LessonPlanSerializer.Meta):
        fields = ["id", "title", "subject", "grade", "topic", "class_hours", "created_at"]

class LessonReviewSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = LessonReview
        fields = ["id", "title", "subject", "grade", "course_teacher", "media_file", "media_url", "transcript", "report_content", "created_at"]
        read_only_fields = ["report_content", "created_at"]
        extra_kwargs = {"media_file": {"write_only": True, "required": False}}

    def get_media_url(self, obj):
        if not obj.media_file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.media_file.url) if request else obj.media_file.url


class LessonReviewListSerializer(LessonReviewSerializer):
    class Meta(LessonReviewSerializer.Meta):
        fields = ["id", "title", "subject", "grade", "course_teacher", "created_at"]


class AssistantMessageSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = AssistantMessage
        fields = ["id", "role", "content", "attachment_name", "attachment_url", "created_at"]

    def get_attachment_url(self, obj):
        if not obj.attachment:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.attachment.url) if request else obj.attachment.url


class AssistantChatSerializer(serializers.ModelSerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantChat
        fields = ["id", "title", "messages", "created_at", "updated_at"]


class AssistantChatListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantChat
        fields = ["id", "title", "created_at", "updated_at"]
