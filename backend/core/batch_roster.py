"""Registration and dated usage evidence suggest candidates, not membership."""
from datetime import timedelta

from django.db.models import Count, Min, Max
from django.db.models.functions import TruncDate
from django.utils import timezone

from community.models import Question, Answer
from learning.models import AssistantMessage
from .dashboard import CONTENT, midnight
from .guidance import display_name
from .models import TeacherProfile, TrainingBatch


def roster_evidence(start, end, school='', batch=None):
    profiles = TeacherProfile.objects.filter(user__is_staff=False).select_related('user').order_by('user__first_name', 'pk')
    if school:
        profiles = profiles.filter(school_name=school)
    batches = list(TrainingBatch.objects.prefetch_related('teachers'))
    members = {b.pk: {p.pk for p in b.teachers.all()} for b in batches}
    rows = {}
    for p in profiles:
        joined = timezone.localdate(p.user.date_joined)
        login = p.user.last_login
        login_in_period = bool(login and start <= timezone.localdate(login) <= end)
        rows[p.user_id] = dict(profile=p, name=display_name(p.user), registered_at=p.user.date_joined,
                              registered=start <= joined <= end, login_in_period=login_in_period,
                              last_login=login, first_use=login if login_in_period else None,
                              last_use=login if login_in_period else None,
                              activities=0, materials=0, counts={k: 0 for k, *_ in CONTENT},
                              days=set(), used_batches=set(), registered_batches=[b.name for b in batches if b.start_date <= joined <= b.end_date],
                              confirmed=bool(batch and p.pk in members.get(batch.pk, set())),
                              other_memberships=[b.name for b in batches if (not batch or b.pk != batch.pk) and p.pk in members[b.pk]])
        if login_in_period:
            rows[p.user_id]['days'].add(timezone.localdate(login))
        if login:
            rows[p.user_id]['used_batches'].update(b.name for b in batches if b.start_date <= timezone.localdate(login) <= b.end_date)
    # One grouped query per activity kind; never load document bodies to find a roster.
    lower = min([start] + [b.start_date for b in batches])
    upper = max([end] + [b.end_date for b in batches])
    models = [(model, 'author_id', {}, key) for key, _, model, *_ in CONTENT]
    models += [(Question, 'author_id', {}, ''), (Answer, 'author_id', {'answer_type': 'teacher'}, ''),
               (AssistantMessage, 'chat__author_id', {'role': 'user'}, '')]
    for model, author, extra, kind in models:
        grouped = model.objects.filter(**{author + '__in': list(rows)}, **extra,
                                      created_at__gte=midnight(lower), created_at__lt=midnight(upper + timedelta(days=1)))
        grouped = grouped.annotate(day=TruncDate('created_at')).values(author, 'day').annotate(n=Count('pk'), first=Min('created_at'), last=Max('created_at')).order_by()
        for item in grouped:
            row, day = rows[item[author]], item['day']
            row['used_batches'].update(b.name for b in batches if b.start_date <= day <= b.end_date)
            if not start <= day <= end:
                continue
            row['activities'] += item['n']
            row['days'].add(day)
            if kind:
                row['materials'] += item['n']
                row['counts'][kind] += item['n']
            row['first_use'] = min(row['first_use'], item['first']) if row['first_use'] else item['first']
            row['last_use'] = max(row['last_use'], item['last']) if row['last_use'] else item['last']
    for row in rows.values():
        row['used'] = bool(row['activities'] or row['login_in_period'])
        row['candidate'] = row['registered'] or row['used']
        row['other_usage'] = sorted(name for name in row['used_batches'] if not batch or name != batch.name)
        row['day_count'] = len(row['days'])
        row['basis'] = '本期注册且有使用记录' if row['registered'] and row['used'] else '本期注册，暂无本期使用记录' if row['registered'] else '非本期注册，本期有使用记录' if row['used'] else '暂无本期注册或使用记录'
    return list(rows.values())


def roster_statistics(rows):
    return {'registered': sum(r['registered'] for r in rows), 'used': sum(r['used'] for r in rows),
            'both': sum(r['registered'] and r['used'] for r in rows),
            'candidates': sum(r['candidate'] for r in rows), 'confirmed': sum(r['confirmed'] for r in rows)}


def roster_csv_rows(rows):
    def date(value):
        return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S') if value else '暂无记录'
    result = [['教师编号', '姓名', '学校', '注册时间', '本期筛选依据', '本期保存成果数', '本期活动记录数',
               '本期首次使用证据时间', '本期末次使用证据时间', '是否已确认本批名单', '其他已确认批次', '其他批次使用线索']]
    for r in rows:
        result.append([r['profile'].user_id, r['name'], r['profile'].school_name, date(r['registered_at']), r['basis'], r['materials'], r['activities'],
                       date(r['first_use']), date(r['last_use']), '是' if r['confirmed'] else '否', '、'.join(r['other_memberships']), '、'.join(r['other_usage'])])
    return result
