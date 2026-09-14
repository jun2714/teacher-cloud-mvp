from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from .models import InAppNotice
from .serializers import NoticeSerializer, UserSerializer
from learning.models import ResearchNote, ResearchReport, LessonPlan, LessonReview
from community.models import Question, Answer
from services.asr import AsrError, transcribe_upload
from .tokens import blacklist_user_tokens

PROFILE_FIELDS = ("school_name", "subject", "grade", "department")
BOOL_FIELDS = ("notify_lesson", "notify_community")
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@api_view(["GET", "PATCH"])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def me(request):
    user = request.user
    if request.method == "GET":
        return Response(UserSerializer(user, context={"request": request}).data)

    data = request.data or {}
    display_name = data.get("display_name") or data.get("first_name")
    if display_name is not None:
        user.first_name = str(display_name).strip()[:30]
        user.save(update_fields=["first_name"])
        profile = user.teacher_profile
        if not profile.avatar_text:
            profile.avatar_text = user.first_name[:1] or user.username[:1]
            profile.save(update_fields=["avatar_text"])

    profile = user.teacher_profile
    profile_data = data.get("profile") if isinstance(data.get("profile"), dict) else data
    changed = False
    for field in PROFILE_FIELDS:
        if field in profile_data and profile_data[field] is not None:
            setattr(profile, field, str(profile_data[field]).strip())
            changed = True
    for field in BOOL_FIELDS:
        if field in profile_data and profile_data[field] is not None:
            setattr(profile, field, _as_bool(profile_data[field]))
            changed = True

    avatar = request.FILES.get("avatar")
    if avatar is not None:
        if avatar.size > MAX_AVATAR_SIZE:
            return Response({"detail": "头像不能超过 5MB"}, status=400)
        content_type = (avatar.content_type or "").lower()
        if content_type and content_type not in ALLOWED_AVATAR_TYPES:
            return Response({"detail": "仅支持 JPG / PNG / WEBP / GIF 图片"}, status=400)
        if profile.avatar:
            profile.avatar.delete(save=False)
        profile.avatar = avatar
        changed = True

    if changed:
        profile.save()

    return Response(UserSerializer(user, context={"request": request}).data)


@api_view(["POST"])
def change_password(request):
    user = request.user
    old_password = str(request.data.get("old_password") or "")
    new_password = str(request.data.get("new_password") or "")
    confirm_password = str(request.data.get("confirm_password") or new_password)
    if not old_password or not new_password:
        return Response({"detail": "请填写原密码和新密码"}, status=400)
    if not user.check_password(old_password):
        return Response({"detail": "原密码不正确"}, status=400)
    if len(new_password) < 6:
        return Response({"detail": "新密码至少 6 位"}, status=400)
    if new_password != confirm_password:
        return Response({"detail": "两次输入的新密码不一致"}, status=400)
    if new_password == old_password:
        return Response({"detail": "新密码不能与原密码相同"}, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_user_tokens(user)
    return Response({"detail": "密码已修改，请使用新密码重新登录"})


@api_view(["GET"])
def my_stats(request):
    user = request.user
    return Response({
        "notes": ResearchNote.objects.filter(author=user).count(),
        "reports": ResearchReport.objects.filter(author=user).count(),
        "questions": Question.objects.filter(author=user).count(),
        "solved_questions": Question.objects.filter(author=user, status="solved").count(),
        "answers": Answer.objects.filter(author=user, answer_type="teacher").count(),
        "lesson_plans": LessonPlan.objects.filter(author=user).count(),
        "lesson_reviews": LessonReview.objects.filter(author=user).count(),
        "learning_days": ResearchNote.objects.filter(author=user).dates("created_at", "day").count(),
    })


@api_view(["GET"])
def notice_list(request):
    qs = InAppNotice.objects.filter(user=request.user)
    unread_only = str(request.query_params.get("unread") or "") in ("1", "true")
    if unread_only:
        qs = qs.filter(is_read=False)
    return Response(NoticeSerializer(qs[:50], many=True).data)


@api_view(["GET"])
def notice_unread(request):
    qs = InAppNotice.objects.filter(user=request.user, is_read=False)
    latest = qs.first()
    return Response({
        "count": qs.count(),
        "latest": NoticeSerializer(latest).data if latest else None,
    })


@api_view(["POST"])
def notice_mark_read(request):
    ids = request.data.get("ids") or []
    qs = InAppNotice.objects.filter(user=request.user, is_read=False)
    if ids:
        qs = qs.filter(id__in=ids)
    updated = qs.update(is_read=True)
    return Response({"updated": updated})


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def asr_transcribe(request):
    uploaded = request.FILES.get("file") or request.FILES.get("audio") or request.FILES.get("media_file")
    if not uploaded:
        return Response({"detail": "请选择要转写的音视频"}, status=400)
    try:
        text = transcribe_upload(uploaded)
    except AsrError as exc:
        return Response({"detail": str(exc)}, status=502)
    return Response({"text": text, "filename": getattr(uploaded, "name", "")})
