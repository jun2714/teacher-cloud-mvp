"""Teaching evidence and feedback; record counts do not rate teaching quality."""
from collections import Counter
from datetime import timedelta
import re
from urllib.parse import urlencode

from django import forms
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.db.models.functions import TruncDate
from django.core.validators import MaxLengthValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

from community.models import Answer, Question
from learning.models import AssistantMessage
from services.text_clean import clean_generated_text
from .dashboard import CONTENT, midnight
from .models import TeachingFeedback

SPECS = {item[0]: item for item in CONTENT}
BODY_FIELDS = {"plans": "generated_content", "reviews": "report_content", "notes": "content", "reports": "content"}


def display_name(user):
    return user.first_name or user.username


def render_document(text, *, anchor_prefix="reading-section"):
    parser = MarkdownIt("js-default", {"breaks": True})
    # User attachments are accessed explicitly; rendering never fetches remote images.
    parser.add_render_rule("image", lambda renderer, tokens, idx, options, env: str(escape(tokens[idx].content)))
    # Keep board diagrams/code verbatim, including standalone dashes and stars.
    chunks, prose, fence = [], [], None
    for line in (text or "").splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            chunks.append(line)
            if re.match(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$", line):
                fence = None
        elif match:
            chunks.append(clean_generated_text("".join(prose)))
            prose = []
            fence = match.group(1)
            chunks.append(line)
        else:
            prose.append(line)
    chunks.append(clean_generated_text("".join(prose)))
    tokens = parser.parse("".join(chunks))
    toc = []
    for i, token in enumerate(tokens):
        if token.type == "heading_open":
            anchor = f"{anchor_prefix}-{len(toc) + 1}"
            token.attrSet("id", anchor)
            label = tokens[i + 1].content.replace("**", "").replace("`", "")
            toc.append({"anchor": anchor, "label": label, "level": int(token.tag[1:])})
        if token.type == "inline":
            for child in token.children or []:
                if child.type == "link_open":
                    child.attrSet("rel", "noreferrer noopener")
    return mark_safe(parser.renderer.render(tokens, parser.options, {})), toc


def visible_feedback(user):
    if not user.has_perm("core.view_teachingfeedback"):
        return TeachingFeedback.objects.none()
    return TeachingFeedback.objects.select_related("reviewer", "teacher").filter(~Q(status="draft") | Q(reviewer=user)).order_by("-updated_at", "-pk")


def decorate_feedback(item, user):
    item.reviewer_name = display_name(item.reviewer) if item.reviewer else "原指导人"
    item.overdue = item.status == "sent" and bool(item.follow_up_date and item.follow_up_date < timezone.localdate())
    item.can_edit = item.status == "draft" and item.reviewer_id == user.pk and user.has_perm("core.change_teachingfeedback")
    return item


def guidance_evidence(user, dashboard):
    rows = dashboard["teachers"]
    teacher_ids = [row["user_id"] for row in rows]
    start, end = dashboard["filters"]["start"], dashboard["filters"]["end"]
    pending = Counter()
    can_view = user.has_perm("core.view_teachingfeedback")
    open_counts, done_counts = Counter(), Counter()
    if can_view:
        for key, _, model, *_ in CONTENT:
            reviewed = TeachingFeedback.objects.filter(kind=key, object_id=OuterRef("pk"), teacher_id=OuterRef("author_id"), status__in=["sent", "done"])
            qs = model.objects.filter(author_id__in=teacher_ids, created_at__gte=midnight(start), created_at__lt=midnight(end + timedelta(days=1)))
            for record in qs.annotate(has_feedback=Exists(reviewed)).filter(has_feedback=False).values("author_id").annotate(n=Count("pk")):
                pending[record["author_id"]] += record["n"]
        for record in TeachingFeedback.objects.filter(teacher_id__in=teacher_ids).exclude(status="draft").values("teacher_id", "status").annotate(n=Count("pk")):
            (open_counts if record["status"] == "sent" else done_counts)[record["teacher_id"]] += record["n"]
    for row in rows:
        row.update(pending=pending[row["user_id"]], followups=open_counts[row["user_id"]], done=done_counts[row["user_id"]])
    return {"can_view": can_view, "pending": sum(pending.values()), "followups": sum(open_counts.values()),
            "inactive": sum(row["days"] == 0 for row in rows), "done": sum(done_counts.values()),
            "query": urlencode({"start": start, "end": end, "school": dashboard["filters"].get("school") or ""})}


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = TeachingFeedback
        fields = ["strengths", "suggestions", "action_plan", "follow_up_date"]
        widgets = {
            "strengths": forms.Textarea(attrs={"rows": 3, "placeholder": "结合实际成果，写下值得肯定的做法"}),
            "suggestions": forms.Textarea(attrs={"rows": 4, "placeholder": "围绕教学目标、课堂活动或评价方式，给出具体建议"}),
            "action_plan": forms.Textarea(attrs={"rows": 3, "placeholder": "建议老师下一次备课或授课时尝试什么"}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("strengths", "suggestions", "action_plan"):
            self.fields[name].max_length = 5000
            self.fields[name].validators.append(MaxLengthValidator(5000))
            self.fields[name].widget.attrs["maxlength"] = 5000


def teacher_activity(profile, filters):
    """Recent saved artifacts and interaction evidence, without reading chat bodies."""
    rows, totals = [], []
    window = {"created_at__gte": midnight(filters["start"]), "created_at__lt": midnight(filters["end"] + timedelta(days=1))}
    for key, label, model, _, icon in CONTENT:
        qs = model.objects.filter(author=profile.user, **window)
        totals.append({"label": label, "count": qs.count(), "icon": icon, "key": key})
        for item in qs.only("pk", "title", "created_at").order_by("-created_at", "-pk")[:30]:
            rows.append({"title": item.title, "kind": key, "label": label, "when": item.created_at,
                         "url": reverse(f"admin:learning_{model._meta.model_name}_change", args=[item.pk]), "detail": "保存教研成果"})
    for model, owner, extra, label in [(Question, "author", {}, "社区提问"), (Answer, "author", {"answer_type": "teacher"}, "同伴互助")]:
        qs = model.objects.filter(**{owner: profile.user}, **extra, **window).select_related("question") if model is Answer else model.objects.filter(author=profile.user, **window)
        for item in qs.order_by("-created_at", "-pk")[:30]:
            question = item.question if model is Answer else item
            rows.append({"title": question.title, "kind": "community", "label": label, "when": item.created_at,
                         "url": reverse(f"admin:community_{model._meta.model_name}_change", args=[item.pk]), "detail": "参与社区教研交流"})
    messages = AssistantMessage.objects.filter(chat__author=profile.user, role="user", **window)
    for day in messages.annotate(day=TruncDate("created_at")).values("day").annotate(n=Count("pk"), last=Max("created_at")).order_by("-last")[:30]:
        rows.append({"title": f"向教研助手发起 {day['n']} 次提问", "kind": "chats", "label": "智能体使用", "when": day["last"], "url": "", "detail": "按教师发送的消息统计"})
    return sorted(rows, key=lambda row: row["when"], reverse=True)[:30], totals
