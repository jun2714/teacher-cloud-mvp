from datetime import timedelta
from io import BytesIO
from zipfile import ZipFile
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from django.core.management import call_command

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from docx import Document

from core.models import TrainingBatch
from core.official_roster import match_roster
from core.test_archive_exports import payload_bytes, word_text
from learning.models import ResearchNote


class OfficialRosterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('roster_admin', password='test-only')
        self.teacher = User.objects.create_user('1234_用户', email='13900001234')
        self.same_name = User.objects.create_user('different_phone', first_name='同名老师', email='13900009999')
        self.start = timezone.localdate()-timedelta(days=2)
        self.end = timezone.localdate()
        self.batch = TrainingBatch.objects.create(name='测试批次', start_date=self.start, end_date=self.end,
                                                   confirmed_at=timezone.now(), roster_source='测试名单.docx')
        rows = [dict(no=1, name='正式老师', school='正式学校', subject='物理', phone='13900001234'),
                dict(no=2, name='未注册老师', school='正式学校', subject='化学', phone='13900005678'),
                dict(no=3, name='同名老师', school='正式学校', subject='英语', phone='13900008888')]
        self.batch.official_roster = match_roster(rows, [self.teacher.teacher_profile, self.same_name.teacher_profile])
        self.batch.save()
        self.batch.teachers.add(self.teacher.teacher_profile)
        self.note = ResearchNote.objects.create(author=self.teacher, title='真实研修笔记', content='讨论合作学习和评价量规。')
        ResearchNote.objects.create(author=self.same_name, title='不确定账号资料', content='不能混入')
        old = ResearchNote.objects.create(author=self.teacher, title='范围之外资料', content='不能混入')
        ResearchNote.objects.filter(pk=old.pk).update(created_at=timezone.now()-timedelta(days=30))
        self.client.force_login(self.admin)
        self.payload = dict(batch=self.batch.pk, batch_name=self.batch.export_name, batch_revision=0, start=str(self.start), end=str(self.end),
                            scope='batch', categories=['B4', 'B5', 'B6', 'B7', 'D1'], achievement='all')

    def test_matching_preserves_missing_and_never_matches_name_only(self):
        self.assertEqual([r['status'] for r in self.batch.official_roster], ['已匹配', '未匹配账号', '待核对账号'])
        self.assertNotIn('phone', str(self.batch.official_roster))
        self.assertEqual(self.batch.official_roster[0]['profile_id'], self.teacher.teacher_profile.pk)
        self.assertIsNone(self.batch.official_roster[2]['profile_id'])

    def test_official_exports_use_full_roster_and_period_without_editing_accounts(self):
        response = self.client.post(reverse('archive_center'), self.payload)
        self.assertEqual(response.status_code, 200, response.context['form'].errors if response.context else '')
        with ZipFile(BytesIO(payload_bytes(response))) as z:
            self.assertEqual({n.split('/')[0] for n in z.namelist()}, {'数字化平台过程数据.docx', '本批次学情分析报告.docx', '本批次研修总结报告.docx', '学员研修成果', '教师个人教研报告'})
            personal = [n for n in z.namelist() if n.startswith('教师个人教研报告/') and n.endswith('.docx')
                        and n.rsplit('/', 1)[-1] not in ('教师报告清单.docx', '批次教师名单.docx')]
            self.assertEqual(len(personal), 1)
            process = word_text(z.read('数字化平台过程数据.docx'))
            self.assertIn('正式老师', process)
            self.assertIn('正式名单与账号核对', process)
            self.assertNotIn('未注册老师', process)
            self.assertNotIn('不确定账号资料', process)
            self.assertNotIn('范围之外资料', process)
            analysis = word_text(z.read('本批次学情分析报告.docx'))
            self.assertIn('正式名单 3 人', analysis)
            self.assertIn('本次选入 1 位教师', analysis)
            self.assertIn('正式学校', analysis)
            self.assertFalse(any('未注册老师' in n for n in z.namelist()))
            original = word_text(z.read(next(n for n in z.namelist() if n.startswith('学员研修成果/') and n.endswith('.docx'))))
            self.assertIn('正式老师', original)
            self.assertIn(self.note.content, original)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, '')
        self.assertEqual(self.teacher.teacher_profile.subject, '语文')

    def test_each_teacher_gets_complete_achievements_and_only_own_alias_is_replaced(self):
        self.note.content = '**教师姓名**：1234_用户\n\n历史姓名：1234\\_用户\n\n完整原文，保留另一位 9999_用户 的引用。'
        self.note.save()
        ResearchNote.objects.create(author=self.teacher, title='另一篇成果', content='另一个成果的完整末尾。')
        response = self.client.post(reverse('archive_center'), self.payload)
        with ZipFile(BytesIO(payload_bytes(response))) as z:
            achievements = [n for n in z.namelist() if n.startswith('学员研修成果/')]
            self.assertEqual(len(achievements), 1)
            self.assertIn('学员研修成果/01_正式老师_研修成果.docx', achievements)
            body = word_text(z.read(achievements[0]))
            self.assertIn('正式老师', body)
            self.assertNotIn('1234_用户', body)
            self.assertIn('9999_用户', body)
            self.assertIn('另一个成果的完整末尾。', body)
            self.assertNotIn('范围之外资料', body)
            self.assertNotIn('不确定账号资料', body)
            self.assertFalse(any('未注册老师' in n for n in z.namelist()))
        self.note.refresh_from_db()
        self.assertIn('1234_用户', self.note.content)

    def test_only_missing_official_members_do_not_create_fake_teacher_documents(self):
        self.batch.teachers.clear()
        self.batch.official_roster = self.batch.official_roster[1:]
        self.batch.save()
        r = self.client.post(reverse('archive_center'), self.payload)
        self.assertContains(r, '暂无已匹配账号', status_code=400)

    def test_official_page_and_custom_selection_are_limited_to_matched_roster(self):
        page = self.client.get(reverse('archive_center'), {'batch': self.batch.pk})
        self.assertEqual([r['name'] for r in page.context['roster_rows']], ['正式老师'])
        self.assertContains(page, '正式学校')
        self.assertNotContains(page, '1234_用户')
        self.assertNotContains(page, '未注册老师')
        bad = self.client.post(reverse('archive_center'), {**self.payload, 'scope': 'selected',
                               'teacher_ids': [self.same_name.teacher_profile.pk]})
        self.assertEqual(bad.status_code, 400)
        selected = self.client.post(reverse('archive_center'), {**self.payload, 'scope': 'selected',
                                    'teacher_ids': [self.teacher.teacher_profile.pk]})
        with ZipFile(BytesIO(payload_bytes(selected))) as z:
            self.assertIn('学员研修成果/01_正式老师_研修成果.docx', z.namelist())

    def test_quick_download_checks_login_and_uses_confirmed_roster(self):
        url = reverse('archive_center') + f'?download_batch={self.batch.pk}'
        response = self.client.get(url)
        self.assertEqual(response['Content-Type'], 'application/zip')
        response.close()
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_formal_school_filter_uses_roster_not_default_profile(self):
        response = self.client.post(reverse('archive_center'), {**self.payload, 'school':'正式学校', 'categories':['B4', 'B6'],
                                   'teacher_ids':[self.teacher.teacher_profile.pk]})
        self.assertEqual(response.status_code, 200)
        with ZipFile(BytesIO(payload_bytes(response))) as z:
            self.assertIn('真实研修笔记', word_text(z.read('数字化平台过程数据.docx')))
            analysis = word_text(z.read('本批次学情分析报告.docx'))
            self.assertIn('本期注册 1 人，有本期使用证据 1 人', analysis)

    def test_manual_save_cannot_erase_formal_unmatched_rows(self):
        r = self.client.post(reverse('archive_center'), {**self.payload, 'action':'save_roster', 'teacher_ids':[self.teacher.teacher_profile.pk]})
        self.assertContains(r, '为防止覆盖未匹配人员', status_code=400)
        self.batch.refresh_from_db()
        self.assertEqual(len(self.batch.official_roster), 3)

    def test_duplicate_phone_rejected(self):
        row = dict(name='老师', school='学校', subject='语文', phone='13900001234')
        with self.assertRaises(ValidationError):
            match_roster([dict(row, no=1), dict(row, no=2)], [])

    def test_name_confirmation_is_explicit_and_unique(self):
        row = dict(no=1, name='同名老师', school='学校', subject='语文', phone='13900008888')
        found = match_roster([row], [self.same_name.teacher_profile], confirmed_names={'同名老师'})
        self.assertEqual(found[0]['profile_id'], self.same_name.teacher_profile.pk)
        duplicate = User.objects.create_user('second_same_name', first_name='同名老师')
        found = match_roster([row], [self.same_name.teacher_profile, duplicate.teacher_profile], confirmed_names={'同名老师'})
        self.assertIsNone(found[0]['profile_id'])

    def test_command_preflight_then_exports_five_separate_categories(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / 'roster.json'
            source.write_text(json.dumps([dict(batch=self.batch.pk, start=str(self.start), end=str(self.end), source='名单.docx',
                teachers=[dict(no=1, name='正式老师', school='正式学校', subject='物理', phone='13900001234')])]), encoding='utf-8')
            out = Path(tmp) / 'output'
            options = dict(input=str(source), output=str(out), admin=self.admin.username, verbosity=0)
            call_command('export_training_rosters', **options)
            self.assertFalse(out.exists())
            self.batch.refresh_from_db()
            self.assertEqual(self.batch.revision, 0)
            call_command('export_training_rosters', **options, apply=True)
            self.batch.refresh_from_db()
            self.assertEqual(self.batch.revision, 1)
            with ZipFile(out / '四批研修分类归档.zip') as z:
                self.assertEqual(len(z.namelist()), 5)
                self.assertEqual({Path(n).name.split('_')[0] for n in z.namelist()}, {'B4','B5','B6','B7','D1'})
