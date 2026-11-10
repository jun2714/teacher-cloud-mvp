"""Read-only statistics built from saved records, never example data."""
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta

from django import forms
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from community.models import Answer, Question
from learning.models import AssistantMessage, LessonPlan, LessonReview, ResearchNote, ResearchReport
from .models import TeacherProfile, TrainingBatch

CONTENT = (
    ("plans", "教学设计", LessonPlan, "#8448ff", "document"),
    ("reviews", "听评课", LessonReview, "#1684ff", "headphones"),
    ("notes", "教研笔记", ResearchNote, "#20c4ca", "notes"),
    ("reports", "教研报告", ResearchReport, "#ffb31a", "report"),
)
PERMISSIONS = (
    "core.view_teacherprofile", "learning.view_lessonplan", "learning.view_lessonreview",
    "learning.view_researchnote", "learning.view_researchreport", "learning.view_assistantmessage",
    "community.view_question", "community.view_answer",
)
ACTIVITY_HELP = "活跃指发布教学设计、听评课、教研笔记、教研报告、社区提问/教师回答或发送智能体消息；不包含仅登录和浏览。"


class DashboardFilters(forms.Form):
    start = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    end = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    school = forms.CharField(required=False, max_length=100)
    trend = forms.ChoiceField(required=False, choices=[("7", "7"), ("30", "30"), ("90", "90")])
    kind = forms.ChoiceField(required=False, choices=[("all", "全部")] + [(c[0], c[1]) for c in CONTENT])
    ranking = forms.ChoiceField(required=False, choices=[("content", "按内容数量"), ("teachers", "按教师人数")])

    def clean(self):
        data = super().clean()
        today = timezone.localdate()
        end = data.get("end") or today
        start = data.get("start") or end - timedelta(days=29)
        if start > end:
            raise forms.ValidationError("开始日期不能晚于结束日期。")
        if end > today:
            raise forms.ValidationError("结束日期不能晚于今天。")
        if (end - start).days >= 366:
            raise forms.ValidationError("一次最多查看 366 天，请缩小日期范围。")
        data.update(start=start, end=end, trend=int(data.get("trend") or 30),
                    kind=data.get("kind") or "all", ranking=data.get("ranking") or "content")
        return data


class CockpitFilters(DashboardFilters):
    batch = forms.ModelChoiceField(queryset=TrainingBatch.objects.exclude(official_roster=[]).filter(confirmed_at__isnull=False), required=False)
    participants = forms.ChoiceField(required=False, choices=[('used', '本期有使用记录'), ('all', '全部已匹配老师')])
    capture = forms.ChoiceField(required=False, choices=[('1', '截图展示')])

    def __init__(self, data=None, *args, **kwargs):
        # A batch owns its exact date interval. Old date inputs must not leak into it.
        if data is not None:
            data = data.copy()
            batch_id = str(data.get('batch') or '')
            batch = self.base_fields['batch'].queryset.filter(pk=batch_id).first() if batch_id.isdigit() else None
            if batch:
                data['start'], data['end'] = batch.start_date.isoformat(), batch.end_date.isoformat()
        super().__init__(data, *args, **kwargs)

    def clean(self):
        data = super().clean()
        data['participants'] = data.get('participants') or 'used'
        if data.get('capture') and not data.get('batch'):
            raise forms.ValidationError('请先选择研修批次，再打开截图展示。')
        return data


def midnight(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def build_dashboard(filters, teacher_id=None):
    start, end = filters["start"], filters["end"]
    duration = (end - start).days + 1
    previous_start = start - timedelta(days=duration)
    recent_start = max(start, end - timedelta(days=6))
    recent_length = (end - recent_start).days + 1
    previous_recent = recent_start - timedelta(days=recent_length)
    history_start = min(previous_start, previous_recent)
    end_time = midnight(end + timedelta(days=1))
    batch = filters.get('batch')
    identities = {r['profile_id']: r for r in batch.official_roster
                  if r.get('profile_id') and r.get('status') == '已匹配'} if batch else {}
    profiles = TeacherProfile.objects.filter(user__is_staff=False).select_related("user")
    if batch:
        profiles = profiles.filter(pk__in=identities)
        schools = sorted({r['school'] for r in identities.values()})
        if filters.get('school'):
            profiles = profiles.filter(pk__in=[pk for pk, r in identities.items() if r['school'] == filters['school']])
    else:
        profiles = profiles.filter(user__date_joined__lt=end_time)
        schools = list(profiles.exclude(school_name="").order_by("school_name").values_list("school_name", flat=True).distinct())
    if filters.get("school") and not batch:
        profiles = profiles.filter(school_name=filters["school"])
    if teacher_id is not None:
        profiles = profiles.filter(user_id=teacher_id)
    teachers = {p.user_id: p for p in profiles}
    for p in teachers.values():
        if p.pk in identities:
            identity = identities[p.pk]
            p.user.first_name, p.school_name, p.subject = identity['name'], identity['school'], identity['subject']
    activity = defaultdict(set)
    published = Counter()
    teacher_counts, teacher_days = Counter(), defaultdict(set)
    subject_counts, subject_teachers = Counter(), defaultdict(set)
    totals, previous, recent = Counter(), Counter(), Counter()
    latest = []
    # Group in the database: no large document bodies and no multi-join count explosion.
    for key, label, model, color, icon in CONTENT:
        queryset = model.objects.filter(author_id__in=teachers, created_at__gte=midnight(history_start), created_at__lt=end_time)
        fields = ["author_id", "day"] + (["subject"] if key != "reports" else [])
        grouped = queryset.annotate(day=TruncDate("created_at")).values(*fields).annotate(n=Count("pk")).order_by()
        for row in grouped:
            day, user_id, n = row["day"], row["author_id"], row["n"]
            activity[day].add(user_id)
            if previous_start <= day < start:
                previous[key] += n
            if start <= day <= end:
                totals[key] += n
                published[day] += n
                teacher_counts[user_id] += n
                subject = (teachers[user_id].subject if batch else row.get("subject") or teachers[user_id].subject or "未填写").strip() or "未填写"
                subject_counts[subject] += n
                subject_teachers[subject].add(user_id)
                if day >= recent_start:
                    recent[key] += n
        if filters["kind"] in ("all", key):
            for record in queryset.filter(created_at__gte=midnight(start)).select_related("author").only("id", "title", "created_at", "author__first_name", "author__username").order_by("-created_at", "-pk")[:10]:
                latest.append({"title": record.title, "kind": key, "label": label,
                               "author": teachers[record.author_id].user.first_name or teachers[record.author_id].user.username,
                               "created_at": record.created_at, "url": reverse(f"admin:learning_{model._meta.model_name}_change", args=[record.pk])})
    # New messages count continued use of an existing conversation as well.
    for model, author, extra in ((Question, "author_id", {}), (Answer, "author_id", {"answer_type": "teacher"}),
                                  (AssistantMessage, "chat__author_id", {"role": "user"})):
        rows = model.objects.filter(**{author + "__in": teachers}, **extra,
                                    created_at__gte=midnight(history_start), created_at__lt=end_time)
        for row in rows.annotate(day=TruncDate("created_at")).values(author, "day").distinct().order_by():
            activity[row["day"]].add(row[author])
    current_active, prior_active = set(), set()
    for day, users in activity.items():
        if recent_start <= day <= end:
            current_active.update(users)
        if previous_recent <= day < recent_start:
            prior_active.update(users)
        if start <= day <= end:
            for user_id in users:
                teacher_days[user_id].add(day)
    total = sum(totals.values())
    participation = round(len(current_active) / len(teachers) * 100, 1) if teachers else 0
    stats = [
        {"key": "teachers", "label": "教师总人数", "value": len(teachers), "icon": "users", "color": "blue",
         "delta": sum(start <= timezone.localtime(p.user.date_joined).date() <= end for p in teachers.values()),
         "caption": "本批已匹配教师" if batch else "所选学校教师", "comparison": "选期新增"},
        {"key": "active", "label": f"近{recent_length}天活跃教师", "value": len(current_active), "icon": "bars", "color": "teal",
         "delta": len(current_active) - len(prior_active), "caption": f"{participation}% 活跃率", "comparison": "较前期"},
    ]
    for key, label, model, color, icon in CONTENT:
        stats.append({"key": key, "label": label, "value": totals[key], "icon": icon,
                      "color": {"plans": "blue", "reviews": "purple", "notes": "orange", "reports": "teal"}[key],
                      "delta": totals[key] - previous[key], "caption": f"近{recent_length}天新增 {recent[key]}", "comparison": "较上期"})
    max_count = max(teacher_counts.values(), default=0)
    teacher_rows = sorted(({
        "user_id": uid, "profile_id": p.pk,
        "name": p.user.first_name or p.user.username, "school": p.school_name, "department": p.department,
        "count": teacher_counts[uid], "days": len(teacher_days[uid]), "last_login": p.user.last_login,
        "bar": round(teacher_counts[uid] / max_count * 100, 1) if max_count else 0,
        "url": reverse("admin:core_teacherprofile_change", args=[p.pk]),
    } for uid, p in teachers.items()), key=lambda row: (-row["count"], -row["days"], row["name"]))
    subjects = [{"name": name, "count": n, "teachers": len(subject_teachers[name])} for name, n in subject_counts.items() if name != "未填写"]
    subjects.sort(key=lambda row: (-row["count" if filters["ranking"] == "content" else "teachers"], row["name"]))
    max_subject = max((s["count" if filters["ranking"] == "content" else "teachers"] for s in subjects), default=1)
    for subject in subjects:
        subject["value"] = subject["count" if filters["ranking"] == "content" else "teachers"]
        subject["bar"] = round(subject["value"] / max_subject * 100, 1)
    series = [{"date": (start + timedelta(days=i)).isoformat(), "active": len(activity[start + timedelta(days=i)]),
               "content": published[start + timedelta(days=i)]} for i in range(duration)]
    segments, offset = [], 0
    for key in ("notes", "reviews", "plans", "reports"):
        spec = next(c for c in CONTENT if c[0] == key)
        percent = totals[key] / total * 100 if total else 0
        segments.append({"name": spec[1], "count": totals[key], "percent": round(percent, 1), "length": percent, "offset": -offset, "color": spec[3]})
        offset += percent
    batch_usage = None
    if batch:
        from .batch_roster import roster_evidence
        rows = roster_evidence(start, end, filters.get('school', ''), batch)
        if teacher_id is not None:
            rows = [r for r in rows if r['profile'].user_id == teacher_id]
        for row in rows:
            row['interactions'] = row['activities'] - row['materials']
            row['usage_label'] = '有教研记录' if row['activities'] else '仅有登录记录' if row['login_in_period'] else '暂无使用记录'
        used = [r for r in rows if r['used']]
        batch_usage = {'rows': rows if filters.get('participants') == 'all' else used,
                       'matched': len(rows), 'used': len(used), 'active': sum(bool(r['activities']) for r in rows),
                       'login_only': sum(r['login_in_period'] and not r['activities'] for r in rows),
                       'materials': sum(r['materials'] for r in rows), 'inactive': len(rows) - len(used)}
    return {"stats": stats, "teachers": teacher_rows, "teacher_preview": teacher_rows[:10], "subjects": subjects,
            "latest": sorted(latest, key=lambda r: r["created_at"], reverse=True)[:10], "series": series,
            "segments": segments, "total": total, "schools": schools, "filters": filters,
            "participation": participation, "active_count": len(current_active), "recent_length": recent_length,
            "subject_count": len(subjects), "activity_help": ACTIVITY_HELP,
            "batch": batch, "batch_usage": batch_usage,
            "content_types": [{"key": c[0], "name": c[1]} for c in CONTENT]}
