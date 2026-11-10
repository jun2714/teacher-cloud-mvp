import csv
from datetime import timedelta
from io import BytesIO, StringIO
from zipfile import ZipFile

from django.contrib.auth.models import User, Permission
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from docx import Document
from docx.oxml.ns import qn

from community.models import Question
from learning.models import LessonPlan, ResearchReport, ResearchNote, LessonReview, AssistantChat, AssistantMessage
from .archive_exports import csv_bytes, record_files
from .models import TeachingFeedback


def payload_bytes(response):
    if response.streaming:
        body = b''.join(response.streaming_content)
        response.close()
        return body
    return response.content


def word_text(data):
    document = Document(BytesIO(data))
    return '\n'.join([p.text for p in document.paragraphs] + [c.text for t in document.tables for r in t.rows for c in r.cells])


class ArchiveExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('export_admin', password='test-only')
        cls.teacher = User.objects.create_user('export_one', first_name='同名老师')
        cls.other = User.objects.create_user('export_two', first_name='同名老师')
        cls.teacher.teacher_profile.school_name = '甲校'
        cls.teacher.teacher_profile.save()
        cls.other.teacher_profile.school_name = '乙校'
        cls.other.teacher_profile.save()
        cls.body = '## 教学目标\n\n**完整正文**\n\n|环节|评价|\n|---|---|\n|诵读|互评|\n\n```text\n---\n    ↓\n**板书符号**\n```'
        cls.plan = LessonPlan.objects.create(author=cls.teacher, title='../同名课题', topic='春', student_context='已有阅读基础，需要加强互评。', generated_content=cls.body)
        cls.report = ResearchReport.objects.create(author=cls.teacher, title='研修总结', content=cls.body)
        cls.old = LessonPlan.objects.create(author=cls.teacher, title='范围外旧记录', generated_content='不应导出')
        LessonPlan.objects.filter(pk=cls.old.pk).update(created_at=timezone.now()-timedelta(days=80))
        cls.foreign = LessonPlan.objects.create(author=cls.other, title='其他学校资料', generated_content='其他学校正文')
        Question.objects.create(author=cls.teacher, title='如何评价朗读', content='讨论')

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('archive_center')
        self.payload = {'batch_name': '本期培训', 'start': (timezone.localdate()-timedelta(days=2)).isoformat(),
                        'end': timezone.localdate().isoformat(), 'scope': 'selected', 'achievement': 'all',
                        'teacher_ids': [self.teacher.teacher_profile.pk], 'categories': ['B4']}

    def post(self, **kwargs):
        return self.client.post(self.url, {**self.payload, **kwargs})

    def test_process_export_has_real_scope_and_safe_csv(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
        text = response.content.decode('utf-8-sig')
        self.assertIn('甲校', text)
        self.assertIn('如何评价朗读', text)
        self.assertNotIn('其他学校资料', text)
        self.assertNotIn('范围外旧记录', text)
        self.assertEqual(list(csv.reader(StringIO(csv_bytes([['=SUM(A1)', '+x', '@y']]).decode('utf-8-sig'))))[0], ["'=SUM(A1)", "'+x", "'@y"])

    def test_all_categories_zip_contains_complete_documents_and_distinct_teachers(self):
        response = self.post(categories=['B4', 'B5', 'B6', 'B7', 'D1'], teacher_ids=[self.teacher.teacher_profile.pk, self.other.teacher_profile.pk])
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(payload_bytes(response))) as archive:
            names = archive.namelist()
            self.assertIn('数字化平台过程数据.csv', names)
            self.assertTrue(any(n.startswith('学员研修成果/') and n.endswith('.docx') for n in names))
            personal = [n for n in names if n.startswith('教师个人教研报告/') and n.endswith('.docx')]
            self.assertEqual(len(personal), 2)
            self.assertEqual(len(names), len(set(names)))
            other_report = word_text(archive.read(next(n for n in personal if f'/{self.other.pk}_' in n)))
            self.assertIn('其他学校正文', other_report)
            self.assertNotIn('完整正文', other_report)
            b6 = Document(BytesIO(archive.read('本批次学情分析报告.docx')))
            self.assertIn('参训教师', '\n'.join(p.text for p in b6.paragraphs))
            self.assertNotIn('已有阅读基础', '\n'.join(p.text for p in b6.paragraphs))
            self.assertNotIn('范围外旧记录', '\n'.join(p.text for p in b6.paragraphs))
            for name in names:
                self.assertFalse(any(part == '..' for part in name.split('/')))
                if name.endswith('.docx'):
                    Document(BytesIO(archive.read(name)))

    def test_single_person_download_and_bulk_admin_actions(self):
        single = self.post(categories=['D1'])
        self.assertIn('wordprocessingml', single['Content-Type'])
        self.assertNotIn('%2F', single['Content-Disposition'])
        self.assertIn('完整正文', '\n'.join(p.text for p in Document(BytesIO(single.content)).paragraphs))
        url = reverse('admin:learning_lessonplan_changelist')
        for ids in ([self.plan.pk], [self.plan.pk, self.foreign.pk]):
            response = self.client.post(url, {'action': 'export_selected_documents', '_selected_action': ids})
            self.assertEqual(response.status_code, 200)
            if len(ids) == 1:
                document = Document(BytesIO(response.content))
                self.assertIn('    ↓', [p.text for p in document.paragraphs])
                self.assertIn('---', [p.text for p in document.paragraphs])
                self.assertNotIn('```', '\n'.join(p.text for p in document.paragraphs))
                self.assertTrue(document.tables[0].rows[0]._tr.get_or_add_trPr().find(qn('w:tblHeader')) is not None)
            else:
                with ZipFile(BytesIO(payload_bytes(response))) as archive:
                    self.assertEqual(len([n for n in archive.namelist() if n.endswith('.docx')]), 2)
                    self.assertIn('导出清单.csv', archive.namelist())

    def test_invalid_selections_dates_and_unavailable_permissions_fail(self):
        for kwargs in ({'teacher_ids': []}, {'teacher_ids': ['99999999']}, {'school': '甲校', 'teacher_ids': [self.other.teacher_profile.pk]},
                       {'categories': ['B8']}, {'categories': []}, {'start': 'bad'}, {'end': ''}):
            self.assertEqual(self.post(**kwargs).status_code, 400, kwargs)
        self.assertEqual(Client().get(self.url).status_code, 302)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        reader = User.objects.create_user('archive_reader', is_staff=True)
        reader.user_permissions.add(Permission.objects.get(codename='view_lessonplan'))
        self.client.force_login(reader)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        response = self.client.post(reverse('admin:learning_lessonplan_changelist'), {'action': 'export_selected_documents', '_selected_action': [self.plan.pk]})
        self.assertEqual(response.status_code, 200)
        Document(BytesIO(response.content))

    def test_filtered_scope_and_limits_do_not_silently_truncate(self):
        response = self.post(scope='filtered', school='甲校', teacher_ids=[])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('乙校', response.content.decode('utf-8-sig'))
        from unittest.mock import patch
        with patch('core.archive_exports.MAX_RECORDS', 1):
            response = self.post()
            self.assertEqual(response.status_code, 400)
            self.assertContains(response, '请缩小日期范围', status_code=400)
        with patch('core.archive_exports.MAX_TEXT', 1):
            response = self.post(categories=['B5'])
            self.assertEqual(response.status_code, 400)
        before = (LessonPlan.objects.count(), ResearchReport.objects.count())
        payload_bytes(self.post(categories=['D1', 'B7']))
        self.assertEqual(before, (LessonPlan.objects.count(), ResearchReport.objects.count()))

    def test_ninety_teachers_each_have_an_individual_archive(self):
        from .models import TeacherProfile
        users = [User.objects.create_user(f'archive_teacher_{i}', first_name='同名老师') for i in range(90)]
        ids = list(TeacherProfile.objects.filter(user__in=users).values_list('pk', flat=True))
        ResearchNote.objects.bulk_create([ResearchNote(author=u, title=f'个人学习记录{i}', content=f'唯一材料{i}：计划改进课堂评价方式。') for i, u in enumerate(users)])
        response = self.post(categories=['D1'], teacher_ids=ids)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        with ZipFile(BytesIO(payload_bytes(response))) as archive:
            docs = [n for n in archive.namelist() if n.endswith('.docx')]
            self.assertEqual(len(docs), 90)
            self.assertEqual(len(set(docs)), 90)
            for i, u in enumerate(users):
                name = next(n for n in docs if f'/{u.pk}_' in n)
                body = word_text(archive.read(name))
                self.assertIn(f'唯一材料{i}：', body)
                self.assertNotIn(f'唯一材料{(i+1)%90}：', body)

    def test_word_inline_markdown_does_not_leak_markers(self):
        from services.docx_export import markdown_to_docx
        document = Document(markdown_to_docx('**重点**与*说明*和`课堂词语`\n\n|内容|评价|\n|---|---|\n|甲\\|乙|互评|'))
        self.assertEqual(document.paragraphs[0].text, '重点与说明和课堂词语')
        self.assertEqual(document.tables[0].rows[1].cells[0].text, '甲|乙')

    def test_personal_report_is_built_without_an_existing_research_report(self):
        ResearchReport.objects.filter(author=self.teacher).delete()
        note = ResearchNote.objects.create(author=self.teacher, title='课堂观察反思', content='小组互评还缺乏具体标准，希望改进评价量规。')
        review = LessonReview.objects.create(author=self.teacher, title='观摩心得', report_content='本次观察学生在讨论中主动提问。')
        response = self.post(categories=['D1'])
        body = word_text(response.content)
        for value in ['完整正文', '希望改进评价量规', '本次观察学生', f'教研笔记 #{note.pk}', f'听评课 #{review.pk}', '下一步实践计划']:
            self.assertIn(value, body)
        self.assertNotIn('资料待补充', body)
        self.assertNotIn('其他学校正文', body)
        self.assertEqual(ResearchReport.objects.filter(author=self.teacher).count(), 0)

    def test_analysis_uses_teacher_questions_not_student_context_or_ai_replies(self):
        chat = AssistantChat.objects.create(author=self.teacher, title='课堂活动')
        AssistantMessage.objects.create(chat=chat, role='user', content='学生不愿主动提问，怎样改进课堂互动？')
        AssistantMessage.objects.create(chat=chat, role='assistant', content='无依据效果提升百分之九十')
        foreign = AssistantChat.objects.create(author=self.other)
        AssistantMessage.objects.create(chat=foreign, role='user', content='其他教师私有问题')
        body = word_text(self.post(categories=['B6']).content)
        self.assertIn('怎样改进课堂互动', body)
        self.assertIn('学习关注点与具体需求', body)
        self.assertIn('分层支持安排', body)
        for value in ['已有阅读基础', '效果提升百分之九十', '其他教师私有问题']:
            self.assertNotIn(value, body)

    def test_optional_targets_only_count_nonblank_saved_materials(self):
        LessonPlan.objects.create(author=self.other, title='空正文', generated_content='   \n\n')
        body = word_text(self.post(categories=['B6'], teacher_ids=[self.teacher.teacher_profile.pk, self.other.teacher_profile.pk], target_plans=2).content)
        self.assertIn('0/2 人达到所填全部数量要求', body)
        self.assertIn('教学设计 1/2', body)
        body = word_text(self.post(categories=['B6'], target_plans=1).content)
        self.assertIn('1/1 人达到所填全部数量要求', body)
        self.assertIn('不是成果质量审核或结业通过率', body)
        body = word_text(self.post(categories=['B6']).content)
        self.assertIn('不计算任务完成率', body)
        document = Document(BytesIO(self.post(categories=['B6']).content))
        material = next(t for t in document.tables if t.cell(0, 0).text == '材料类型')
        self.assertEqual(material.cell(2, 1).text, '0')
        for value in (-1, 101, 'invalid'):
            self.assertEqual(self.post(target_plans=value).status_code, 400)

    def test_summary_has_process_evidence_and_attributed_external_facts(self):
        response = self.post(categories=['B7'], training_context='聚焦课堂评价', implementation_notes='负责人记录：举行一次现场观课研讨。')
        body = word_text(response.content)
        for value in ['研修实施过程', '实践内容与阶段认识', '后续改进安排', '聚焦课堂评价', '负责人记录', '未经平台核验', f'教学设计 #{self.plan.pk}']:
            self.assertIn(value, body)
        self.assertNotIn('范围外旧记录', body)

    def test_feedback_visibility_and_period_filtering(self):
        shared = TeachingFeedback.objects.create(teacher=self.teacher, reviewer=self.admin, target_title='阶段指导', suggestions='按标准设计互评', status='sent', sent_at=timezone.now())
        TeachingFeedback.objects.create(teacher=self.teacher, reviewer=self.admin, target_title='草稿', suggestions='私有未发送草稿', status='draft')
        TeachingFeedback.objects.create(teacher=self.other, reviewer=self.admin, target_title='其他教师', suggestions='其他教师指导', status='sent', sent_at=timezone.now())
        TeachingFeedback.objects.create(teacher=self.teacher, reviewer=self.admin, target_title='过去指导', suggestions='历史指导', status='sent', sent_at=timezone.now()-timedelta(days=60))
        body = word_text(self.post(categories=['D1']).content)
        self.assertIn(f'指导 #{shared.pk}', body)
        self.assertIn('按标准设计互评', body)
        for value in ['私有未发送草稿', '其他教师指导', '历史指导']:
            self.assertNotIn(value, body)
        from .dashboard import PERMISSIONS
        reader = User.objects.create_user('export_report_reader', is_staff=True)
        reader.user_permissions.set([Permission.objects.get(content_type__app_label=s.split('.')[0], codename=s.split('.')[1]) for s in PERMISSIONS])
        self.client.force_login(reader)
        body = word_text(self.post(categories=['D1']).content)
        self.assertNotIn('按标准设计互评', body)
        self.assertIn('无教研指导查看权限', body)

    def test_preview_single_report_download_and_return_preserve_conditions(self):
        response = self.post(action='preview', categories=['B6', 'B7', 'D1'], target_notes=2)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '研修报告预览')
        self.assertContains(response, '教师主动提问')
        self.assertContains(response, '下载此报告 Word', count=3)
        response = self.post(action='adjust', categories=['B6', 'D1'], target_notes=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form']['target_notes'].value(), '2')
        self.assertEqual(response.context['form']['categories'].value(), ['B6', 'D1'])
        single = self.post(categories=['B6', 'B7', 'D1'], report_key='B7')
        self.assertIn('wordprocessingml', single['Content-Type'])
        self.assertIn('研修实施过程', word_text(single.content))
        self.assertEqual(self.post(categories=['D1'], report_key=f'D1:{self.other.pk}').status_code, 400)
        self.assertEqual(self.post(categories=['D1'], report_key='B6').status_code, 400)
        self.assertEqual(self.post(categories=['B4'], action='preview').status_code, 400)

    def test_no_evidence_is_not_reported_as_completed_and_dangerous_text_is_escaped(self):
        empty = User.objects.create_user('no_evidence', first_name='路径/同名')
        response = self.post(categories=['D1'], teacher_ids=[empty.teacher_profile.pk])
        self.assertIn('资料待补充', word_text(response.content))
        self.assertNotIn('达到数量要求', word_text(response.content))
        ResearchNote.objects.create(author=self.teacher, title='甲|乙', content='<script>alert("xss")</script>\n\n## 原材料标题\n\n[点击](javascript:alert(1))')
        response = self.post(categories=['B6'], action='preview', implementation_notes='<img src=x onerror=alert(2)>')
        self.assertNotContains(response, '<script>alert(')
        self.assertNotContains(response, '<img src=x')
        document = Document(BytesIO(self.post(categories=['B6']).content))
        self.assertTrue(any('甲|乙' in c.text for t in document.tables for r in t.rows for c in r.cells))
        self.assertTrue(all(len(r.cells) == len(t.columns) for t in document.tables for r in t.rows))

    def test_export_limits_are_separate_for_documents_and_process(self):
        from unittest.mock import patch
        with patch('core.archive_exports.MAX_DOCUMENTS', 1):
            response = self.post(categories=['B6'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.post(categories=['B5']).status_code, 400)

    def test_date_boundaries_are_inclusive_and_new_accounts_do_not_hide_selected_teachers(self):
        from .dashboard import midnight
        start = timezone.localdate()-timedelta(days=1)
        end = timezone.localdate()
        for name, when in [('第一天零点', midnight(start)), ('最后一天末尾', midnight(end+timedelta(days=1))-timedelta(microseconds=1)), ('下一天', midnight(end+timedelta(days=1)))]:
            obj = ResearchNote.objects.create(author=self.teacher, title=name, content=name)
            ResearchNote.objects.filter(pk=obj.pk).update(created_at=when)
        body = self.post(categories=['B4'], start=start, end=end).content.decode('utf-8-sig')
        self.assertIn('第一天零点', body)
        self.assertIn('最后一天末尾', body)
        self.assertNotIn('下一天', body)

    def test_duplicate_categories_do_not_duplicate_zip_members(self):
        response = self.post(categories=['B5', 'B5', 'D1', 'D1'])
        with ZipFile(BytesIO(payload_bytes(response))) as archive:
            self.assertEqual(len(archive.namelist()), len(set(archive.namelist())))

    def test_excerpts_skip_document_cover_and_source_order_uses_time(self):
        from .training_reports import excerpt
        result = excerpt('# 个人教研报告\n\n教师姓名：测试教师\n\n学科：语文\n\n## 实践收获\n\n通过课堂观察，发现学生互评需要更具体的标准。')
        self.assertNotIn('教师姓名', result)
        self.assertIn('学生互评需要更具体的标准', result)
        newer = ResearchNote.objects.create(author=self.teacher, title='较新笔记', content='较新内容')
        older = ResearchNote.objects.create(author=self.teacher, title='较旧笔记', content='较旧内容')
        ResearchNote.objects.filter(pk=older.pk).update(created_at=timezone.now()-timedelta(minutes=10))
        body = word_text(self.post(categories=['B7']).content)
        self.assertIn('较新内容', body)
        self.assertNotIn('较旧内容', body)  # Older source stays in the index, not the newest excerpt.
