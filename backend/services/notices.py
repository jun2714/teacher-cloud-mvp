from django.core.exceptions import ObjectDoesNotExist
from core.models import InAppNotice


def push_notice(user, category: str, title: str, body: str = "", link: str = "") -> None:
    if not user or not getattr(user, "is_authenticated", True):
        return
    try:
        profile = user.teacher_profile
    except ObjectDoesNotExist:
        profile = None
    if category in {"lesson", "report", "review"} and profile and not profile.notify_lesson:
        return
    if category == "community" and profile and not profile.notify_community:
        return
    InAppNotice.objects.create(
        user=user,
        category=category,
        title=(title or "新消息")[:80],
        body=(body or "")[:300],
        link=(link or "")[:200],
    )
