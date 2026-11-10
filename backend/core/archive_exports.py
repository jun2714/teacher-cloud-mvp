"""Bounded, permission-checked exports of saved training evidence."""
import csv
import re
from datetime import timedelta
from io import StringIO
from functools import partial
from tempfile import TemporaryFile
from urllib.parse import quote
from zipfile import ZipFile, ZIP_DEFLATED

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, F
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from community.models import Answer, Question
from learning.models import AssistantMessage
from services.docx_export import markdown_to_docx
from services.archive_documents import print_tables, roster_sections, index_sections, collected_documents
from .dashboard import CONTENT, DashboardFilters, PERMISSIONS, midnight
from .guidance import BODY_FIELDS, display_name, render_document, visible_feedback
from .guidance_views import page_context
from .models import TeacherProfile, TrainingBatch
from .batch_roster import roster_evidence, roster_statistics, roster_csv_rows
from .training_reports import TrainingEvidence, report_documents, table, text, plain
from .official_roster import apply_official_roster, official_csv_rows, official_summary

CATEGORIES = [('B4', '数字化平台过程数据'), ('B5', '学员研修成果'), ('B6', '本批次学情分析报告'),
              ('B7', '本批次研修总结报告'), ('D1', '教师个人教研报告')]
MAX_RECORDS = 5000
MAX_DOCUMENTS = 500
MAX_TEACHERS = 100
MAX_TEXT = 5_000_000


def safe_name(value):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', str(value)).strip(' .')[:70] or '未命名'


def response_file(data, name, mime):
    response = FileResponse(data, content_type=mime) if hasattr(data, 'read') else HttpResponse(data, content_type=mime)
    response['Content-Disposition'] = "attachment; filename=export." + name.rsplit('.', 1)[-1] + "; filename*=UTF-8''" + quote(name)
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def csv_bytes(rows):
    output = StringIO(newline='')
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(["'" + str(v) if str(v).lstrip().startswith(('=', '+', '-', '@')) else str(v) for v in row])
    return ('\ufeff' + output.getvalue()).encode('utf-8')


def package(files, label, force_zip=False):
    def content(value):
        return value() if callable(value) else value
    if len(files) == 1 and not force_zip:
        name, data = files[0]
        name = name.rsplit('/', 1)[-1]
        mime = 'text/csv; charset=utf-8' if name.endswith('.csv') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        return response_file(content(data), name, mime)
    # Generate one Word at a time and stream a temporary ZIP; 90/500 documents
    # must not accumulate their embedded backgrounds in server memory.
    output = TemporaryFile()
    try:
        with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
            for name, data in files:
                archive.writestr(name, content(data))
        output.seek(0)
        return response_file(output, safe_name(label) + '.zip', 'application/zip')
    except Exception:
        output.close()
        raise


def document_bytes(title, body, report=False):
    # All exports include a clear title, even if the stored body has no heading.
    return markdown_to_docx('# ' + title.replace('\n', ' ') + '\n\n' + body, background=not report).getvalue()


def record_files(kind, records, *, report=False):
    spec = next(item for item in CONTENT if item[0] == kind)
    files, manifest, size = [], [['编号', '类型', '教师', '标题', '创建时间', '文件名', '正文状态']], 0
    for obj in records:
        body = getattr(obj, BODY_FIELDS[kind]) or ''
        size += len(body)
        if size > MAX_TEXT:
            raise forms.ValidationError('所选正文过多，请缩小范围后分批导出。')
        name = f'{obj.pk}_{safe_name(display_name(obj.author))}_{safe_name(obj.title)}.docx'
        when = timezone.localtime(obj.created_at).strftime('%Y-%m-%d %H:%M')
        meta = f'教师：{display_name(obj.author)}\n\n资料类型：{spec[1]}\n\n创建时间：{when}\n\n'
        for field, label in [('subject', '学科'), ('grade', '年级'), ('topic', '课题'), ('class_hours', '课时'), ('course_teacher', '授课教师')]:
            value = getattr(obj, field, '')
            if value:
                meta += f'{label}：{value}\n\n'
        files.append((name, partial(document_bytes, obj.title, meta + (body or '尚未填写正文。'), report=report)))
        manifest.append([obj.pk, spec[1], display_name(obj.author), obj.title, when, name, '有正文' if body.strip() else '未填写'])
    return files, manifest


def teacher_achievements(profile, data, groups):
    """All selected source documents for one teacher, kept in their date window."""
    name = display_name(profile.user)
    introduction = (f'研修批次：{text(data["batch_name"])}\n\n'
                    f'统计日期：{data["start"]} 至 {data["end"]}（含首尾日期）\n\n'
                    f'教师：{text(name)}\n\n学校：{text(profile.school_name)}；学科：{text(profile.subject)}\n\n')
    summary, documents = [], []
    for kind, label, *_ in CONTENT:
        if data.get('achievement') not in ('', None, 'all', kind):
            continue
        records = sorted((r for r in groups[kind] if r.author_id == profile.user_id), key=lambda r: (r.created_at, r.pk))
        summary.append([label, len(records), sum(bool(plain(getattr(r, BODY_FIELDS[kind]))) for r in records)])
        for obj in records:
            body = getattr(obj, BODY_FIELDS[kind]) or ''
            meta = (f'教师：{text(name)}\n\n资料类型：{label}；来源编号：{label} #{obj.pk}\n\n'
                    f'创建时间：{timezone.localtime(obj.created_at):%Y-%m-%d %H:%M:%S}\n\n')
            for field, caption in [('subject', '学科'), ('grade', '年级'), ('topic', '课题'), ('class_hours', '课时'), ('course_teacher', '授课教师')]:
                value = getattr(obj, field, '')
                if value:
                    meta += f'{caption}：{text(value)}\n\n'
            documents.append((f'{label} · {text(obj.title)}', meta + (body or '尚未填写正文，待补充。')))
    introduction += '## 本期成果概况\n\n' + table(['成果类型', '保存份数', '有正文份数'], summary)
    if not documents:
        introduction += '## 资料待补充\n\n本批次日期内暂未查到该教师所选类型的已保存成果。本文件仅作材料核对记录，不代表已提交成果，也不据此判断是否参训。\n\n'
    else:
        introduction += ('以下按功能类型和创建时间收录本期保存的完整材料，每份材料另起一页。'
                         '教师默认用户名按正式名单统一为本人姓名，其余正文保留；教学设想与个人观点仍需教师核对。\n\n')
    return collected_documents(text(name) + '学员研修成果', introduction, documents)


class ExportActionsMixin:
    actions = ['export_selected_documents']

    @admin.action(description='导出所选资料 Word（多条打包 ZIP）', permissions=['view'])
    def export_selected_documents(self, request, queryset):
        from django.contrib import messages
        if queryset.count() > MAX_DOCUMENTS:
            self.message_user(request, '一次最多导出 500 条，请缩小筛选范围。', level=messages.ERROR)
            return
        records = list(queryset.select_related('author').order_by('pk'))
        if not records or any(not self.has_view_or_change_permission(request, obj) for obj in records):
            raise PermissionDenied
        try:
            files, manifest = record_files(self.reading_kind, records)
        except forms.ValidationError as exc:
            self.message_user(request, exc.messages[0], level=messages.ERROR)
            return
        if len(files) > 1:
            files.append(('导出清单.docx', partial(print_tables, '资料导出清单', index_sections(manifest))))
        return package(files, self.model._meta.verbose_name + '批量导出')


class ArchiveForm(DashboardFilters):
    batch = forms.ModelChoiceField(label='研修批次', queryset=TrainingBatch.objects.all(), required=False, empty_label='自定义时间段')
    batch_revision = forms.IntegerField(required=False, widget=forms.HiddenInput, min_value=0)
    categories = forms.MultipleChoiceField(label='归档资料', choices=CATEGORIES, widget=forms.CheckboxSelectMultiple)
    batch_name = forms.CharField(label='批次名称', max_length=100, initial='吴忠中学教师跟岗实践暨“县中帮扶”交流培训')
    teacher_ids = forms.ModelMultipleChoiceField(label='指定教师', queryset=TeacherProfile.objects.none(), required=False,
                                               widget=forms.CheckboxSelectMultiple)
    scope = forms.ChoiceField(label='导出范围', choices=[('selected', '当前勾选教师'), ('batch', '已确认批次名单'), ('filtered', '本期注册或使用的教师')], initial='selected')
    achievement = forms.ChoiceField(label='成果类型', choices=[('all', '全部成果')] + [(key, label) for key, label, *_ in CONTENT], required=False)
    training_context = forms.CharField(label='培训安排与目标', required=False, max_length=3000,
                                      widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '可补充实际培训主题、安排和目标，报告会注明信息来源。'}))
    implementation_notes = forms.CharField(label='线下实施及调查情况', required=False, max_length=5000,
                                           widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '可补充线下观摩、专题培训、需求调查等真实情况；不要填写未经核实的成效。'}))
    target_plans = forms.IntegerField(label='每人教学设计最低份数', required=False, min_value=0, max_value=100)
    target_reviews = forms.IntegerField(label='每人听评课最低份数', required=False, min_value=0, max_value=100)
    target_notes = forms.IntegerField(label='每人教研笔记最低份数', required=False, min_value=0, max_value=100)
    target_reports = forms.IntegerField(label='每人已有教研报告最低份数', required=False, min_value=0, max_value=100)

    def __init__(self, *args, roster_action='', **kwargs):
        self.roster_action = roster_action
        super().__init__(*args, **kwargs)
        if roster_action:
            self.fields['categories'].required = False
        if roster_action == 'find_teachers' or (roster_action != 'save_roster' and self.is_bound and self.data.get('scope') == 'batch'):
            self.fields['teacher_ids'].disabled = True
        school = self.data.get('school', '') if self.is_bound else self.initial.get('school', '')
        qs = TeacherProfile.objects.select_related('user').filter(user__is_staff=False).order_by('user__first_name', 'pk')
        if school:
            qs = qs.filter(school_name=school)
        self.fields['teacher_ids'].queryset = qs
        self.fields['teacher_ids'].label_from_instance = lambda p: f'{display_name(p.user)}（{p.school_name} · 账号 {p.user.username}）'
        self.fields['start'].required = True
        self.fields['end'].required = True
        self.fields['start'].label = '开始日期'
        self.fields['end'].label = '结束日期'
        self.fields['start'].widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
        self.fields['end'].widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
        self.fields['school'].label = '学校（留空表示不限）'
        if not self.is_bound:
            self.initial.setdefault('start', timezone.localdate() - timedelta(days=29))
            self.initial.setdefault('end', timezone.localdate())

    def clean(self):
        data = super().clean()
        batch = data.get('batch')
        if batch:
            if (data.get('start'), data.get('end')) != (batch.start_date, batch.end_date):
                raise forms.ValidationError('日期与所选批次不一致，请重新选择批次；自定义日期请先选择“自定义时间段”。')
            data['batch_name'] = batch.export_name
        if self.roster_action == 'find_teachers':
            return data
        if 'categories' in data:
            data['categories'] = list(dict.fromkeys(data['categories']))
        qs = data.get('teacher_ids')
        if self.roster_action != 'save_roster' and data.get('scope') == 'batch':
            if not batch or not batch.confirmed_at:
                raise forms.ValidationError('该批次尚未确认名单，请先核对教师并保存名单。')
            if data.get('batch_revision') != batch.revision:
                raise forms.ValidationError('该批次名单已更新，请重新打开批次后再导出。')
            if batch.official_roster:
                official = [r for r in batch.official_roster if not data.get('school') or r['school'] == data['school']]
                if not official:
                    raise forms.ValidationError('正式名单中没有符合该学校范围的教师。')
                qs = TeacherProfile.objects.select_related('user').filter(user__is_staff=False,
                     pk__in=[r['profile_id'] for r in official if r.get('profile_id')])
                data['official_rows'] = official
            else:
                qs = self.fields['teacher_ids'].queryset.filter(training_batches=batch)
        elif self.roster_action != 'save_roster' and data.get('scope') == 'filtered':
            if self.errors:
                return data
            candidates = roster_evidence(data['start'], data['end'], data.get('school', ''), batch)
            qs = self.fields['teacher_ids'].queryset.filter(pk__in=[r['profile'].pk for r in candidates if r['candidate']])
        if qs is not None:
            if not qs.exists() and not data.get('official_rows'):
                raise forms.ValidationError('请勾选教师，或选择有教师记录的学校范围。')
            if qs.count() > MAX_TEACHERS:
                raise forms.ValidationError('一次最多导出 100 位教师，请按学校或教研组分批导出。')
            data['profiles'] = list(qs)
        data['roster_source'] = ('已确认批次名单' if data.get('scope') == 'batch' else
                                 '本期注册或使用候选教师（未视为已确认参训名单）' if data.get('scope') == 'filtered' else '本次勾选教师')
        return data


def scope_data(profiles, filters):
    from datetime import timedelta
    ids = [p.user_id for p in profiles]
    window = dict(created_at__gte=midnight(filters['start']), created_at__lt=midnight(filters['end'] + timedelta(days=1)))
    groups, process, active = {}, [], set()
    for key, label, model, *_ in CONTENT:
        records = list(model.objects.filter(author_id__in=ids, **window).select_related('author').order_by('author_id', 'created_at', 'pk')[:MAX_RECORDS + 1])
        groups[key] = records
        for obj in records:
            process.append((obj.author_id, label, obj.pk, obj.title, obj.created_at))
    for model, author, label, extra in [(Question, 'author_id', '社区提问', {}), (Answer, 'author_id', '教师回答', {'answer_type': 'teacher'}),
                                       (AssistantMessage, 'chat__author_id', '智能体提问', {'role': 'user'})]:
        title_field = 'title' if model is Question else 'question__title' if model is Answer else 'chat__title'
        records = model.objects.filter(**{author+'__in': ids}, **window, **extra).order_by('created_at', 'pk').values(author, 'pk', 'created_at', title_field)[:MAX_RECORDS + 1]
        for row in records:
            process.append((row[author], label, row['pk'], row[title_field], row['created_at']))
    if len(process) > MAX_RECORDS:
        raise forms.ValidationError('本范围超过 5000 条过程或成果记录，请缩小日期范围后分批导出。')
    for uid, _, _, _, when in process:
        active.add((uid, timezone.localdate(when)))
    if sum(len(getattr(r, BODY_FIELDS[k]) or '') for k, records in groups.items() for r in records) > MAX_TEXT:
        raise forms.ValidationError('本范围正文过多，请缩小日期范围后分批导出。')
    return groups, sorted(process, key=lambda x: (x[4], x[2])), active


def training_evidence(data, user):
    selected = {p.pk for p in data['profiles']}
    batch = data.get('batch')
    # Official school filtering has already selected the accounts. Their current
    # profile school may differ and must not hide registration/usage evidence.
    school = '' if batch and batch.official_roster and data.get('scope') == 'batch' else data.get('school', '')
    data['roster_rows'] = [r for r in roster_evidence(data['start'], data['end'], school, batch) if r['profile'].pk in selected]
    groups, process, active = scope_data(data['profiles'], data)
    ids = [p.user_id for p in data['profiles']]
    window = dict(created_at__gte=midnight(data['start']), created_at__lt=midnight(data['end'] + timedelta(days=1)))
    # The same window/roles are already counted and bounded by scope_data.
    questions = list(Question.objects.filter(author_id__in=ids, **window).order_by('created_at', 'pk'))
    messages = list(AssistantMessage.objects.filter(chat__author_id__in=ids, role='user', **window).select_related('chat').order_by('created_at', 'pk'))
    feedback = None
    if user.has_perm('core.view_teachingfeedback'):
        feedback = list(visible_feedback(user).filter(teacher_id__in=ids, status__in=['sent', 'done'],
                        sent_at__gte=midnight(data['start']), sent_at__lt=midnight(data['end'] + timedelta(days=1)))[:MAX_RECORDS + 1])
        if len(feedback) > MAX_RECORDS:
            raise forms.ValidationError('所选指导记录过多，请缩小日期范围。')
    text_size = sum(len(q.content) for q in questions) + sum(len(m.content) for m in messages)
    text_size += sum(len(getattr(r, BODY_FIELDS[k]) or '') for k, records in groups.items() for r in records)
    text_size += sum(len(f.suggestions) + len(f.action_plan) for f in feedback or [])
    if text_size > MAX_TEXT:
        raise forms.ValidationError('所选正文和提问内容过多，请缩小范围后分批生成。')
    return apply_official_roster(data, TrainingEvidence(data, groups, process, active, questions, messages, feedback))


def make_archives(data, evidence, report_key=''):
    profiles = data['profiles']
    groups, process, active = evidence.groups, evidence.process, evidence.active
    names = {p.user_id: display_name(p.user) for p in profiles}
    batch = data['batch_name']
    reports = report_documents(evidence)
    if report_key:
        selected = next((doc for doc in reports if doc['key'] == report_key), None)
        if selected is None:
            raise forms.ValidationError('该报告不在当前所选范围内，请重新选择。')
        return package([(safe_name(selected['title']) + '.docx', partial(document_bytes, selected['title'], selected['body'], report=True))], batch)
    files = []
    metadata = [('研修批次', batch), ('统计日期', f'{data["start"]} 至 {data["end"]}（含首尾日期）'),
                ('导出时间', evidence.captured_at)]
    numbers = {p.user_id: i for i, p in enumerate(profiles, 1)}
    numbers.update({r['user_id']: r['no'] for r in data.get('official_rows', [])})
    roster = roster_csv_rows(data.get('roster_rows', []))
    roster[0][0] = '名单序号'
    for row in roster[1:]:
        row[0] = numbers[row[0]]
    roster[1:] = sorted(roster[1:], key=lambda row: row[0])
    official_sections = []
    if data.get('official_rows'):
        official = official_csv_rows(data)
        official_sections = [('正式名单与账号核对', official[4][:5], [r[:5] for r in official[5:]], (1, 1.5, 3, 1.5, 2)),
                             ('姓名核对依据', ['名单序号', '姓名', '注册手机尾号', '核对依据'],
                              [[r['no'], r['name'], r.get('phone_tail') or '未匹配', r['basis']] for r in data['official_rows']], (1, 1.5, 2, 4.5))]
    for category in data['categories']:
        if category == 'B4':
            headers = ['名单序号', '姓名', '学校', '教研组', '学科', '年级', '成果数量', '有正文成果数', '活跃天数']
            rows = []
            for p in profiles:
                rows.append([numbers[p.user_id], names[p.user_id], p.school_name, p.department, p.subject or '未提供', p.grade or '未提供',
                             sum(r.author_id == p.user_id for records in groups.values() for r in records),
                             sum(r.author_id == p.user_id for records in evidence.filled.values() for r in records), sum(uid == p.user_id for uid, _ in active)])
            detail = [[f'{label} #{pk}', f'{names[uid]}（序号{numbers[uid]}）', title, timezone.localtime(when).strftime('%Y-%m-%d %H:%M:%S')] for uid, label, pk, title, when in process]
            sections = [('教师基本信息', ['名单序号', '姓名', '学校与教研组', '学科', '年级'],
                         [[r[0], r[1], r[2] + ('\n' + r[3] if r[3] else ''), r[4], r[5]] for r in rows], (1, 1.5, 3.5, 1.5, 1.5)),
                        ('教师使用汇总', [headers[i] for i in (0, 1, 6, 7, 8)],
                         [[r[i] for i in (0, 1, 6, 7, 8)] for r in rows], (1, 1.5, 2, 2, 2))]
            sections += official_sections + roster_sections(roster)
            sections.append(('过程记录明细', ['来源编号', '教师及名单序号', '标题', '时间'], detail, (1.5, 2, 4.5, 2.5)))
            files.append(('数字化平台过程数据.docx', partial(print_tables, '数字化平台过程数据', sections,
                         metadata=metadata + [('名单来源', data.get('roster_source', '本次勾选教师'))],
                         note='按创建时间筛选，仅含平台已保存记录；正文与档案为当前值，不含浏览时长。AI 回复不算教师活跃，暂无记录不等于未参训。名单序号用于对应本次教师名单，来源编号用于查找平台原记录。'
                              + (official_summary(data['official_rows']) if data.get('official_rows') else ''))))
        elif category == 'B5':
            total = sum(len(rows) for k, rows in groups.items() if data.get('achievement') in ('', None, 'all', k))
            if total > MAX_DOCUMENTS:
                raise forms.ValidationError('一次最多导出 500 份成果原文，请按类型或日期分批导出；汇总报告可分析最多 5000 条记录。')
            for p in profiles:
                number = f'{numbers[p.user_id]:02d}' if data.get('official_rows') else str(p.user_id)
                filename = safe_name(f'{number}_{names[p.user_id]}_研修成果') + '.docx'
                files.append(('学员研修成果/' + filename, partial(teacher_achievements, p, data, groups)))
    # Generated report content is shared with the preview; existing originals stay intact.
    for doc in reports:
        # Only our fixed category directory is structural; teacher names are filenames.
        name = ('教师个人教研报告/' if doc['key'].startswith('D1:') else '')
        stem = doc['filename'].removeprefix('教师个人教研报告/').removesuffix('.docx')
        if doc['key'].startswith('D1:') and data.get('official_rows'):
            person = next(p for p in profiles if doc['key'] == f'D1:{p.user_id}')
            stem = f'{numbers[person.user_id]:02d}_{names[person.user_id]}_个人教研报告'
        name += safe_name(stem) + '.docx'
        files.append((name, partial(document_bytes, doc['title'], doc['body'], report=True)))
    if not files:
        raise forms.ValidationError('当前范围没有可导出的资料。')
    return package(files, f'{batch}_{data["start"]}_{data["end"]}_归档资料', force_zip=len(files) > 1 or data['categories'] == ['B5'])


@never_cache
@staff_member_required
def archive_center(request):
    if not request.user.has_perms(PERMISSIONS):
        raise PermissionDenied
    if request.method not in ('GET', 'POST'):
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['GET', 'POST'])
    if request.method == 'GET' and request.GET.get('download_batch', '').isdigit():
        batch = TrainingBatch.objects.filter(pk=request.GET['download_batch']).first()
        if batch and batch.confirmed_at:
            quick = ArchiveForm(dict(batch=batch.pk, batch_name=batch.export_name, batch_revision=batch.revision,
                                     start=str(batch.start_date), end=str(batch.end_date), scope='batch',
                                     achievement='all', categories=[key for key, _ in CATEGORIES]))
            if quick.is_valid():
                try:
                    return make_archives(quick.cleaned_data, training_evidence(quick.cleaned_data, request.user))
                except forms.ValidationError as exc:
                    quick.add_error(None, exc)
            return render_archive_form(request, quick, status=400)
        messages.error(request, '请先确认该批次名单。')
        return redirect(reverse('archive_center'))
    action = request.POST.get('action', '')
    roster_action = action if action in ('find_teachers', 'save_roster') else ''
    initial = {}
    if request.method == 'GET':
        batch = TrainingBatch.objects.filter(pk=request.GET.get('batch')).first() if request.GET.get('batch', '').isdigit() else None
        if 'batch' not in request.GET:
            batch = TrainingBatch.objects.first()
        if batch:
            initial.update(batch=batch.pk, batch_name=batch.export_name, start=batch.start_date, end=batch.end_date,
                           batch_revision=batch.revision, scope='batch' if batch.confirmed_at else 'selected')
    form = ArchiveForm(request.POST if request.method == 'POST' else None, initial=initial, roster_action=roster_action)
    adjusting = request.method == 'POST' and request.POST.get('action') == 'adjust'
    if adjusting:
        form.is_valid()  # Preserve and display the posted criteria without generating files.
    if request.method == 'POST' and not adjusting and form.is_valid():
        try:
            if action == 'save_roster':
                if not request.user.has_perm('core.change_trainingbatch'):
                    raise PermissionDenied
                batch = form.cleaned_data.get('batch')
                if not batch:
                    raise forms.ValidationError('请先选择一个研修批次再保存名单。')
                if batch.official_roster:
                    raise forms.ValidationError('本批次已导入正式名单。为防止覆盖未匹配人员，请更新正式名单映射；临时勾选仍可直接导出。')
                if form.cleaned_data.get('school'):
                    raise forms.ValidationError('保存完整批次名单前请清空学校筛选并重新查询，避免遗漏其他学校教师。')
                with transaction.atomic():
                    changed = TrainingBatch.objects.filter(pk=batch.pk, revision=form.cleaned_data.get('batch_revision')).update(
                        confirmed_at=timezone.now(), confirmed_by=request.user, revision=F('revision') + 1)
                    if not changed:
                        raise forms.ValidationError('名单已被其他管理员更新，请重新打开该批次后核对。')
                    batch.teachers.set(form.cleaned_data['profiles'])
                messages.success(request, f'{batch.name}已保存 {len(form.cleaned_data["profiles"])} 位教师。以后可直接按已确认名单导出本阶段内容。')
                return redirect(reverse('archive_center') + f'?batch={batch.pk}')
            if action == 'find_teachers':
                # Rebuild suggestions for the new period; never carry a previous batch selection over.
                initial = dict(form.cleaned_data)
                batch = initial.get('batch')
                initial['batch'] = batch.pk if batch else None
                initial['batch_revision'] = batch.revision if batch else None
                initial['scope'] = 'selected'
                initial.pop('teacher_ids', None)
                form = ArchiveForm(initial=initial)
                return render_archive_form(request, form, suggest=True)
            evidence = training_evidence(form.cleaned_data, request.user)
            if request.POST.get('action') == 'preview':
                docs = report_documents(evidence)
                if not docs:
                    raise forms.ValidationError('请至少选择一种报告用于预览；过程数据及成果原文可直接导出。')
                for doc in docs:
                    doc['html'], _ = render_document(doc['body'], anchor_prefix='report-' + doc['key'].replace(':', '-'))
                conditions = [(key, value) for key in form.fields for value in request.POST.getlist(key)]
                return render(request, 'admin/archive_preview.html', page_context(request, title='研修报告预览',
                              reports=docs, conditions=conditions, batch_name=form.cleaned_data['batch_name']))
            return make_archives(form.cleaned_data, evidence, request.POST.get('report_key', ''))
        except forms.ValidationError as exc:
            form.add_error(None, exc)
    return render_archive_form(request, form, status=400 if request.method == 'POST' and not adjusting else 200)


def render_archive_form(request, form, status=200, suggest=False):
    batches = list(TrainingBatch.objects.annotate(teacher_count=Count('teachers')).order_by('start_date', 'pk'))
    def value(name):
        return form[name].value()
    try:
        start, end = form.fields['start'].clean(value('start')), form.fields['end'].clean(value('end'))
        batch_id = str(value('batch') or '')
        batch = next((b for b in batches if str(b.pk) == batch_id), None)
        valid_period = start and end and start <= end and (end-start).days < 366
    except forms.ValidationError:
        start = end = batch = None
        valid_period = False
    rows = roster_evidence(start, end, value('school') or '', batch) if valid_period else []
    selected = {str(x) for x in (value('teacher_ids') or [])}
    if not form.is_bound and (suggest or not selected):
        selected = {str(r['profile'].pk) for r in rows if (r['confirmed'] if batch and batch.confirmed_at and not suggest else r['candidate'] or r['confirmed'])}
    for row in rows:
        row['checked'] = str(row['profile'].pk) in selected
    if batch:
        for field in ('start', 'end', 'batch_name'):
            form.fields[field].widget.attrs['readonly'] = True
    return render(request, 'admin/archive_center.html', page_context(request, title='资料导出与批次归档', form=form,
                  batches=batches, selected_batch=batch, roster_rows=rows, roster_stats=roster_statistics(rows),
                  official_summary=official_summary(batch.official_roster) if batch and batch.official_roster else '',
                  roster_valid=valid_period, can_save_roster=request.user.has_perm('core.change_trainingbatch')),
                  status=status)
