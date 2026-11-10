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
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, FileResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from community.models import Answer, Question
from learning.models import AssistantMessage
from services.docx_export import markdown_to_docx
from .dashboard import CONTENT, DashboardFilters, PERMISSIONS, midnight
from .guidance import BODY_FIELDS, display_name, render_document, visible_feedback
from .guidance_views import page_context
from .models import TeacherProfile
from .training_reports import TrainingEvidence, report_documents

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


def record_files(kind, records):
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
        files.append((name, partial(document_bytes, obj.title, meta + (body or '尚未填写正文。'))))
        manifest.append([obj.pk, spec[1], display_name(obj.author), obj.title, when, name, '有正文' if body.strip() else '未填写'])
    return files, manifest


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
            files.append(('导出清单.csv', csv_bytes(manifest)))
        return package(files, self.model._meta.verbose_name + '批量导出')


class ArchiveForm(DashboardFilters):
    categories = forms.MultipleChoiceField(label='归档资料', choices=CATEGORIES, widget=forms.CheckboxSelectMultiple)
    batch_name = forms.CharField(label='批次名称', max_length=100, initial='吴忠中学教师跟岗实践暨“县中帮扶”交流培训')
    teacher_ids = forms.ModelMultipleChoiceField(label='指定教师', queryset=TeacherProfile.objects.none(), required=False,
                                               widget=forms.CheckboxSelectMultiple)
    scope = forms.ChoiceField(label='导出范围', choices=[('selected', '勾选教师'), ('filtered', '当前学校全部教师')], initial='selected')
    achievement = forms.ChoiceField(label='成果类型', choices=[('all', '全部成果')] + [(key, label) for key, label, *_ in CONTENT], required=False)
    training_context = forms.CharField(label='培训安排与目标', required=False, max_length=3000,
                                      widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '可补充实际培训主题、安排和目标，报告会注明信息来源。'}))
    implementation_notes = forms.CharField(label='线下实施及调查情况', required=False, max_length=5000,
                                           widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '可补充线下观摩、专题培训、需求调查等真实情况；不要填写未经核实的成效。'}))
    target_plans = forms.IntegerField(label='每人教学设计最低份数', required=False, min_value=0, max_value=100)
    target_reviews = forms.IntegerField(label='每人听评课最低份数', required=False, min_value=0, max_value=100)
    target_notes = forms.IntegerField(label='每人教研笔记最低份数', required=False, min_value=0, max_value=100)
    target_reports = forms.IntegerField(label='每人已有教研报告最低份数', required=False, min_value=0, max_value=100)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school = self.data.get('school', '') if self.is_bound else ''
        qs = TeacherProfile.objects.select_related('user').filter(user__is_staff=False).order_by('user__first_name', 'pk')
        if school:
            qs = qs.filter(school_name=school)
        self.fields['teacher_ids'].queryset = qs
        self.fields['teacher_ids'].label_from_instance = lambda p: f'{display_name(p.user)}（{p.school_name} · 账号 {p.user.username}）'
        self.fields['start'].required = True
        self.fields['end'].required = True
        self.fields['start'].label = '开始日期'
        self.fields['end'].label = '结束日期'
        self.fields['start'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['end'].widget = forms.DateInput(attrs={'type': 'date'})
        self.fields['school'].label = '学校（留空表示不限）'
        if not self.is_bound:
            self.initial.setdefault('start', timezone.localdate() - timedelta(days=29))
            self.initial.setdefault('end', timezone.localdate())

    def clean(self):
        data = super().clean()
        if 'categories' in data:
            data['categories'] = list(dict.fromkeys(data['categories']))
        qs = data.get('teacher_ids')
        if data.get('scope') == 'filtered':
            qs = self.fields['teacher_ids'].queryset
        if qs is not None:
            if not qs.exists():
                raise forms.ValidationError('请勾选教师，或选择有教师记录的学校范围。')
            if qs.count() > MAX_TEACHERS:
                raise forms.ValidationError('一次最多导出 100 位教师，请按学校或教研组分批导出。')
            data['profiles'] = list(qs)
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
    return TrainingEvidence(data, groups, process, active, questions, messages, feedback)


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
    for category in data['categories']:
        if category == 'B4':
            rows = [['批次', batch], ['日期范围', data['start'], data['end']], ['导出时间', evidence.captured_at], ['口径', '按创建时间筛选；正文与档案为当前值；仅已保存记录，不含浏览时长；AI回复不算教师活跃。'], [], ['教师编号', '姓名', '学校', '教研组', '学科', '年级', '成果数量', '有正文成果数', '活跃天数']]
            for p in profiles:
                rows.append([p.user_id, names[p.user_id], p.school_name, p.department, p.subject, p.grade,
                             sum(r.author_id == p.user_id for records in groups.values() for r in records),
                             sum(r.author_id == p.user_id for records in evidence.filled.values() for r in records), sum(uid == p.user_id for uid, _ in active)])
            rows += [[], ['教师编号', '姓名', '记录类型', '记录编号', '标题', '时间']]
            rows += [[uid, names[uid], label, pk, title, timezone.localtime(when).strftime('%Y-%m-%d %H:%M:%S')] for uid, label, pk, title, when in process]
            files.append(('数字化平台过程数据.csv', csv_bytes(rows)))
        elif category == 'B5':
            total = sum(len(rows) for k, rows in groups.items() if data.get('achievement') in ('', None, 'all', k))
            if total > MAX_DOCUMENTS:
                raise forms.ValidationError('一次最多导出 500 份成果原文，请按类型或日期分批导出；汇总报告可分析最多 5000 条记录。')
            manifest = [['类型', '编号', '教师', '标题', '时间', '文件名', '正文状态']]
            for key, label, *_ in CONTENT:
                if data.get('achievement') not in ('', None, 'all', key):
                    continue
                docs, rows = record_files(key, groups[key])
                files.extend((f'学员研修成果/{label}/{name}', body) for name, body in docs)
                manifest.extend([[row[1], row[0], *row[2:5], f'{label}/{row[5]}', row[6]] for row in rows[1:]])
            if len(manifest) == 1:
                manifest.append(['所选日期及教师范围暂无符合条件的成果', '', '', '', '', '', '请调整筛选条件'])
            files.append(('学员研修成果/成果清单.csv', csv_bytes(manifest)))
    # Generated report content is shared with the preview; existing originals stay intact.
    for doc in reports:
        # Only our fixed category directory is structural; teacher names are filenames.
        name = ('教师个人教研报告/' if doc['key'].startswith('D1:') else '')
        stem = doc['filename'].removeprefix('教师个人教研报告/').removesuffix('.docx')
        name += safe_name(stem) + '.docx'
        files.append((name, partial(document_bytes, doc['title'], doc['body'], report=True)))
    if 'D1' in data['categories'] and len(profiles) > 1:
        manifest = [['教师编号', '姓名', '学校', '有正文成果数', '材料状态', '文件名']]
        for p in profiles:
            n = sum(r.author_id == p.user_id for records in evidence.filled.values() for r in records)
            has_question = any(s['uid'] == p.user_id and s['kind'] in ('question', 'message') for s in evidence.sources)
            manifest.append([p.user_id, names[p.user_id], p.school_name, n,
                             '已整理，待教师核对' if n or has_question else '资料待补充', safe_name(f'{p.user_id}_{names[p.user_id]}') + '.docx'])
        files.append(('教师个人教研报告/教师报告清单.csv', csv_bytes(manifest)))
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
    form = ArchiveForm(request.POST if request.method == 'POST' else None)
    adjusting = request.method == 'POST' and request.POST.get('action') == 'adjust'
    if adjusting:
        form.is_valid()  # Preserve and display the posted criteria without generating files.
    if request.method == 'POST' and not adjusting and form.is_valid():
        try:
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
    return render(request, 'admin/archive_center.html', page_context(request, title='资料导出与批次归档', form=form,
                  schools=TeacherProfile.objects.exclude(school_name='').order_by('school_name').values_list('school_name', flat=True).distinct()),
                  status=400 if request.method == 'POST' and not adjusting else 200)
