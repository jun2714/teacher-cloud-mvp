"""Official identities belong to an archive, never overwrite teachers' accounts."""
import copy
import re
from collections import Counter
from types import SimpleNamespace

from django.core.exceptions import ValidationError

from .guidance import display_name


def match_roster(teachers, profiles, *, confirmed_names=()):
    """Match a unique complete phone only. Names alone are review candidates."""
    if not teachers or len(teachers) > 100:
        raise ValidationError('正式名单须包含 1 至 100 位教师。')
    rows, seen_numbers, seen_phones = [], set(), set()
    profiles = list(profiles)
    for teacher in teachers:
        no = int(teacher['no'])
        name, school, subject = (str(teacher.get(k, '')).strip() for k in ('name', 'school', 'subject'))
        phone = re.sub(r'[\s-]', '', str(teacher.get('phone', '')))
        if no < 1 or no in seen_numbers or not name or not school or not subject or not re.fullmatch(r'1\d{10}', phone):
            raise ValidationError('名单序号、姓名、学校、学科或完整手机号不合法。')
        if phone in seen_phones:
            raise ValidationError('正式名单存在重复手机号，请先核对。')
        if any(len(v) > limit for v, limit in ((name, 80), (school, 100), (subject, 40))):
            raise ValidationError('名单字段过长。')
        seen_numbers.add(no)
        seen_phones.add(phone)
        found = [p for p in profiles if p.user.email.strip() == phone]
        candidates = [p for p in profiles if display_name(p.user) == name]
        row = dict(no=no, name=name, school=school, subject=subject, profile_id=None,
                   status='未匹配账号', basis='完整手机号未匹配；不据此判断是否参训')
        if len(found) == 1:
            row.update(profile_id=found[0].pk, status='已匹配', basis='正式名单与注册完整手机号一致')
        elif not found and len(candidates) == 1 and name in confirmed_names:
            row.update(profile_id=candidates[0].pk, status='已匹配', basis='管理员按正式姓名核对确认；注册手机号与名单不同')
        elif found or candidates:
            row.update(status='待核对账号', basis='手机号重复或同名账号手机号不同，尚未确认')
        # Contact details and national IDs are deliberately not persisted/exported.
        rows.append(row)
    matched = [r['profile_id'] for r in rows if r['profile_id']]
    if len(matched) != len(set(matched)):
        raise ValidationError('同一账号对应多个正式名单人员，请先核对。')
    return rows


def apply_official_roster(data, evidence):
    batch = data.get('batch')
    if not batch or not batch.official_roster or data.get('scope') != 'batch':
        return evidence
    entries = batch.official_roster
    if data.get('school'):
        entries = [r for r in entries if r['school'] == data['school']]
    available = {p.pk: p for p in data['profiles']}
    renamed, profiles, audit = {}, [], []
    for entry in entries:
        row = dict(entry)
        original = available.get(row.get('profile_id'))
        if original:
            p, user = copy.copy(original), copy.copy(original.user)
            row.update(account=original.user.username, account_name=display_name(original.user), user_id=original.user_id)
            user.first_name = row['name']
            p.user = user
            p.school_name, p.subject = row['school'], row['subject']
            # Grade/department defaults are not verified by the official roster.
            p.grade, p.department = '', ''
            renamed[p.user_id] = p
        else:
            uid = f'名单{row["no"]:02d}'
            p = SimpleNamespace(pk=None, user_id=uid, school_name=row['school'], subject=row['subject'],
                                department='', grade='', user=SimpleNamespace(first_name=row['name'], username='', pk=uid))
            row.update(account='', account_name='', user_id=uid)
            if row.get('profile_id'):
                row.update(status='待核对账号', basis='已匹配账号当前不可用，需重新核对')
        profiles.append(p)
        audit.append(row)
    data['profiles'] = evidence.profiles = profiles
    data['official_rows'] = audit
    data['roster_source'] = f'正式名单：{batch.roster_source}；姓名、学校、学科以正式名单为准；账号未改动'
    for row in data.get('roster_rows', []):
        if row['profile'].user_id in renamed:
            row['profile'] = renamed[row['profile'].user_id]
            row['name'] = display_name(row['profile'].user)
    for records in evidence.groups.values():
        for record in records:
            if record.author_id in renamed:
                record.author = renamed[record.author_id].user
    return evidence


def official_csv_rows(data):
    rows = [['批次', data['batch_name']], ['日期范围', str(data['start']), str(data['end'])],
            ['说明', '正式名单信息用于归档展示，不修改账号与成果原文；未匹配不等于未参训。'], [],
            ['名单序号', '正式姓名', '学校', '学科', '账号匹配状态', '平台账号', '平台原显示姓名', '核对依据']]
    for r in data.get('official_rows', []):
        rows.append([r['no'], r['name'], r['school'], r['subject'], r['status'], r['account'], r['account_name'], r['basis']])
    return rows


def official_summary(rows):
    counts = Counter(r['status'] for r in rows)
    return f'正式名单 {len(rows)} 人；已匹配 {counts["已匹配"]} 人；待核对 {counts["待核对账号"]} 人；未匹配 {counts["未匹配账号"]} 人。'
