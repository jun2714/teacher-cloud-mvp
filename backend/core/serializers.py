from django.contrib.auth.models import User
from rest_framework import serializers
from .models import InAppNotice, TeacherProfile


class TeacherProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = ["school_name", "subject", "grade", "department", "avatar_text", "avatar_url", "notify_lesson", "notify_community"]

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return ""
        return obj.avatar.url


class UserSerializer(serializers.ModelSerializer):
    profile = TeacherProfileSerializer(source="teacher_profile", read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "display_name", "profile"]

    def get_display_name(self, obj):
        return obj.first_name or obj.username


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotice
        fields = ["id", "category", "title", "body", "link", "is_read", "created_at"]
