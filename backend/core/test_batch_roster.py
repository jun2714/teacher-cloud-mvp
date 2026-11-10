from datetime import date, datetime
from io import BytesIO
from zipfile import ZipFile

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import ResearchNote, AssistantChat, AssistantMessage
from community.models import Question, Answer
from .models import TrainingBatch
from .dashboard import PERMISSIONS
from .batch_roster import roster_evidence, roster_statistics
from .test_archive_exports import payload_bytes, word_text


class BatchRosterTests(TestCase):
    @staticmethod
    def when(value):
        return timezone.make_aware(datetime.fromisoformat(value))

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('batch_admin', password='test-only')
        def teacher(name, joined, login=None):
            u = User.objects.create_user(name, first_name=name)
            User.objects.filter(pk=u.pk).update(date_joined=cls.when(joined), last_login=cls.when(login) if login else None)
            return u
        cls.alice = teacher('本期注册使用', '2026-10-12 09:00')
        cls.bob = teacher('提前注册本期使用', '2026-09-01 09:00')
        cls.carol = teacher('仅注册', '2026-10-15 09:00')
        cls.david = teacher('第二批教师', '2026-10-19 09:00')
        cls.eve = teacher('仅有最近登录证据', '2026-09-01 09:00', '2026-10-16 09:00')
        cls.manual = teacher('需人工补选', '2026-09-01 09:00', '2026-11-09 09:00')
        cls.notes = []
        for u, title, when in [(cls.alice, '第一批独有内容', '2026-10-13 10:00'), (cls.alice, '同教师第二批内容', '2026-10-20 10:00'),
                               (cls.bob, '第一批提前注册老师笔记', '2026-10-14 10:00'), (cls.david, '第二批其他教师内容', '2026-10-20 10:00')]:
            note = ResearchNote.objects.create(author=u, title=title, content=title)
            ResearchNote.objects.filter(pk=note.pk).update(created_at=cls.when(when))
            cls.notes.append(note)
        chat = AssistantChat.objects.create(author=cls.manual)
        msg = AssistantMessage.objects.create(chat=chat, role='assistant', content='仅 AI 回复，不作为教师使用')
        AssistantMessage.objects.filter(pk=msg.pk).update(created_at=cls.when('2026-10-13 12:00'))
        cls.first = TrainingBatch.objects.get(name='第一批')
        cls.second = TrainingBatch.objects.get(name='第二批')

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('archive_center')
        self.payload = {'batch': self.first.pk, 'batch_revision': 0, 'batch_name': self.first.export_name,
                        'start': '2026-10-11', 'end': '2026-10-17', 'scope': 'selected',
                        'categories': ['B4'], 'achievement': 'all', 'teacher_ids': [self.alice.teacher_profile.pk]}

    def post(self, **kwargs):
        return self.client.post(self.url, {**self.payload, **kwargs})

    def test_four_actual_batch_dates_are_seeded(self):
        self.assertEqual(list(TrainingBatch.objects.values_list('start_date', 'end_date')), [
            (date(2026, 10, 11), date(2026, 10, 17)), (date(2026, 10, 18), date(2026, 10, 24)),
            (date(2026, 10, 25), date(2026, 10, 31)), (date(2026, 11, 1), date(2026, 11, 7))])

    def test_candidates_are_registration_or_usage_with_distinct_reasons(self):
        rows = roster_evidence(self.first.start_date, self.first.end_date, batch=self.first)
        candidates = {r['profile'].user_id for r in rows if r['candidate']}
        self.assertEqual(candidates, {self.alice.pk, self.bob.pk, self.carol.pk, self.eve.pk})
        self.assertEqual(roster_statistics(rows), {'registered': 2, 'used': 3, 'both': 1, 'candidates': 4, 'confirmed': 0})
        alice = next(r for r in rows if r['profile'].user_id == self.alice.pk)
        self.assertEqual(alice['materials'], 1)
        self.assertIn('第二批', alice['other_usage'])
        bob = next(r for r in rows if r['profile'].user_id == self.bob.pk)
        self.assertEqual(bob['basis'], '非本期注册，本期有使用记录')
        manual = next(r for r in rows if r['profile'].user_id == self.manual.pk)
        self.assertFalse(manual['used'])
        self.assertNotIn(self.admin.pk, candidates)

    def test_get_and_find_suggest_teachers_without_saving_members(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_batch'].pk, self.first.pk)
        self.assertContains(response, 'value="2026-10-11"')
        self.assertContains(response, 'value="2026-10-17"')
        checked = {r['profile'].user_id for r in response.context['roster_rows'] if r['checked']}
        self.assertEqual(checked, {self.alice.pk, self.bob.pk, self.carol.pk, self.eve.pk})
        self.assertFalse(self.first.teachers.exists())
        response = self.post(action='find_teachers', categories=[], teacher_ids=[])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['roster_stats']['candidates'], 4)
        self.assertFalse(self.first.teachers.exists())

    def test_saved_membership_is_stable_and_export_restricts_time_and_author(self):
        selected = [self.alice.teacher_profile.pk, self.carol.teacher_profile.pk, self.manual.teacher_profile.pk]
        response = self.post(action='save_roster', categories=[], teacher_ids=selected)
        self.assertEqual(response.status_code, 302)
        self.first.refresh_from_db()
        self.assertEqual(self.first.revision, 1)
        self.assertEqual(set(self.first.teachers.values_list('pk', flat=True)), set(selected))
        self.assertFalse(self.second.teachers.exists())
        response = self.client.get(self.url, {'batch': self.first.pk})
        self.assertEqual([b.pk for b in response.context['batches']], list(TrainingBatch.objects.values_list('pk', flat=True)))
        self.assertEqual(response.context['form']['scope'].value(), 'batch')
        self.assertEqual({r['profile'].pk for r in response.context['roster_rows'] if r['checked']}, set(selected))
        # A new candidate is not silently added to a previously confirmed roster.
        from .test_archive_exports import word_text
        body = word_text(self.post(scope='batch', batch_revision=1, teacher_ids=[], categories=['B4']).content)
        self.assertIn('第一批独有内容', body)
        self.assertIn('仅注册', body)
        self.assertIn('需人工补选', body)
        self.assertNotIn('第一批提前注册老师笔记', body)
        self.assertNotIn('同教师第二批内容', body)
        self.assertNotIn('第二批其他教师内容', body)
        with ZipFile(BytesIO(payload_bytes(self.post(scope='batch', batch_revision=1, teacher_ids=[], categories=['B5'])))) as zipfile:
            docs = [n for n in zipfile.namelist() if n.endswith('.docx')
                    and n.rsplit('/', 1)[-1] not in ('成果清单.docx', '批次教师名单.docx')]
            self.assertEqual(len(docs), 1)
            self.assertIn('第一批独有内容', word_text(zipfile.read(docs[0])))
            self.assertIn('学员研修成果/批次教师名单.docx', zipfile.namelist())

    def test_all_period_candidates_export_and_registered_only_teacher_remains_visible(self):
        response = self.post(scope='filtered', teacher_ids=[], categories=['D1'])
        with ZipFile(BytesIO(payload_bytes(response))) as archive:
            self.assertEqual(len([n for n in archive.namelist() if n.endswith('.docx')
                                  and n.rsplit('/', 1)[-1] not in ('教师报告清单.docx', '批次教师名单.docx')]), 4)
            carol = next(n for n in archive.namelist() if n.startswith(f'教师个人教研报告/{self.carol.pk}_'))
            self.assertIn('资料待补充', word_text(archive.read(carol)))
        self.assertEqual(self.post(scope='batch').status_code, 400)

    def test_batch_dates_cannot_be_spoofed_and_name_comes_from_saved_batch(self):
        self.assertEqual(self.post(start='2026-10-01').status_code, 400)
        self.assertEqual(self.post(batch=self.second.pk).status_code, 400)
        self.assertEqual(self.post(batch='999999').status_code, 400)
        body = word_text(self.post(batch_name='错误批次名称').content)
        self.assertIn(self.first.export_name, body)
        self.assertNotIn('错误批次名称', body)

    def test_stale_roster_cannot_overwrite_or_export_changed_members(self):
        self.post(action='save_roster', categories=[])
        response = self.post(action='save_roster', categories=[], teacher_ids=[self.david.teacher_profile.pk])
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, '名单已被其他管理员更新', status_code=400)
        self.assertEqual(self.post(scope='batch', batch_revision=0).status_code, 400)
        self.assertEqual(list(self.first.teachers.values_list('user_id', flat=True)), [self.alice.pk])

    def test_roster_save_permission_and_school_subset_protection(self):
        self.assertEqual(self.post(action='save_roster', categories=[], school=self.alice.teacher_profile.school_name).status_code, 400)
        reader = User.objects.create_user('batch_reader', is_staff=True)
        reader.user_permissions.set([Permission.objects.get(content_type__app_label=x.split('.')[0], codename=x.split('.')[1]) for x in PERMISSIONS])
        self.client.force_login(reader)
        self.assertEqual(self.post(action='find_teachers', categories=[]).status_code, 200)
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post(action='save_roster', categories=[]).status_code, 403)
        self.assertFalse(self.first.teachers.exists())

    def test_date_boundaries_and_teacher_actions_are_included_but_ai_is_not(self):
        User.objects.filter(pk=self.manual.pk).update(date_joined=self.when('2026-10-17 23:59:59'))
        question = Question.objects.create(author=self.david, title='原先的提问', content='测试')
        Question.objects.filter(pk=question.pk).update(created_at=self.when('2026-10-10 10:00'))
        answer = Answer.objects.create(author=self.david, question=question, answer_type='teacher', content='教师回答')
        Answer.objects.filter(pk=answer.pk).update(created_at=self.when('2026-10-17 23:59:59'))
        rows = roster_evidence(self.first.start_date, self.first.end_date, batch=self.first)
        david = next(r for r in rows if r['profile'].user_id == self.david.pk)
        self.assertEqual(david['activities'], 1)
        self.assertFalse(david['registered'])
        self.assertTrue(david['candidate'])
        self.assertTrue(next(r for r in rows if r['profile'].user_id == self.manual.pk)['registered'])

    def test_find_can_change_school_without_reusing_previous_selected_teachers(self):
        profile = self.bob.teacher_profile
        profile.school_name = '另一所学校'
        profile.save()
        response = self.post(action='find_teachers', categories=[], school='另一所学校')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['profile'].user_id for r in response.context['roster_rows']], [self.bob.pk])
        self.assertTrue(response.context['roster_rows'][0]['checked'])
