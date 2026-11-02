from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .guidance import display_name
from .models import InAppNotice, TeacherProfile, TeachingFeedback


class FeedbackSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    source_link = serializers.SerializerMethodField()

    class Meta:
        model = TeachingFeedback
        fields = ["id", "kind", "kind_label", "target_title", "reviewer_name", "strengths", "suggestions", "action_plan", "follow_up_date",
                  "status", "status_label", "teacher_reply", "sent_at", "completed_at", "source_link"]
        read_only_fields = fields

    def get_reviewer_name(self, obj):
        return display_name(obj.reviewer) if obj.reviewer else "指导教师"

    def get_source_link(self, obj):
        # Only link to an existing artifact still owned by the feedback recipient.
        from .guidance import SPECS
        routes = {"plans": "lesson-plans", "reviews": "lesson-reviews", "notes": "notes", "reports": "reports"}
        if obj.kind in SPECS and SPECS[obj.kind][2].objects.filter(pk=obj.object_id, author_id=obj.teacher_id).exists():
            return f"/{routes[obj.kind]}/{obj.object_id}"
        return ""


class FeedbackPagination(PageNumberPagination):
    page_size = 10


class MyFeedbackList(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackSerializer
    pagination_class = FeedbackPagination

    def get_queryset(self):
        return TeachingFeedback.objects.filter(teacher=self.request.user, status__in=["sent", "done"]).select_related("reviewer").order_by("-sent_at", "-pk")


class ReplySerializer(serializers.Serializer):
    teacher_reply = serializers.CharField(max_length=5000, allow_blank=False, error_messages={"blank": "请填写落实说明后再提交。", "required": "请填写落实说明。", "max_length": "落实说明不能超过 5000 字。"})


@api_view(["GET", "POST"])
def my_feedback_detail(request, feedback_id):
    with transaction.atomic():
        qs = TeachingFeedback.objects.filter(teacher=request.user, status__in=["sent", "done"]).select_related("reviewer")
        item = get_object_or_404(qs.select_for_update(of=("self",)) if request.method == "POST" else qs, pk=feedback_id)
        if request.method == "POST":
            if item.status == "done":
                return Response({"detail": "此条指导已提交落实说明，请勿重复提交。"}, status=400)
            form = ReplySerializer(data=request.data)
            form.is_valid(raise_exception=True)
            item.teacher_reply = form.validated_data["teacher_reply"]
            item.status, item.completed_at = "done", timezone.now()
            item.save(update_fields=["teacher_reply", "status", "completed_at", "updated_at"])
            if item.reviewer and item.reviewer.is_active and item.reviewer.is_staff:
                profile = TeacherProfile.objects.filter(user=request.user).first()
                link = f"/admin/teaching/teachers/{profile.pk}/#feedback-history" if profile else "/admin/teaching/"
                InAppNotice.objects.create(user=item.reviewer, category="system", title="教师已提交指导落实说明",
                                           body=f"{display_name(request.user)}已提交《{item.target_title}》的落实说明。"[:300],
                                           link=link)
    return Response(FeedbackSerializer(item).data)
