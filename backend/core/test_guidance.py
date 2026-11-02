from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from learning.models import LessonPlan, LessonReview, ResearchNote, ResearchReport
from .dashboard import DashboardFilters, build_dashboard
from .guidance import guidance_evidence, render_document
from .models import InAppNotice, TeachingFeedback


class GuidanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.leader = User.objects.create_superuser("guide_admin", password="test-only")
        cls.teacher = User.objects.create_user("guide_teacher", first_name="张老师")
        cls.other = User.objects.create_user("guide_other")
        cls.reader = User.objects.create_user("guide_reader", is_staff=True)
        cls.reader.user_permissions.add(Permission.objects.get(content_type__app_label="learning", codename="view_lessonplan"))
        cls.text = "# 教学设计\n\n## 教学目标\n\n**学生**能够解释文意。\n\n- 朗读\n- 讨论\n\n|活动|评价|\n|---|---|\n|诵读|互评|\n\n```text\n地灵 —— 人杰\n    ↓\n情真 —— 志坚\n```"
        cls.plan = LessonPlan.objects.create(author=cls.teacher, title="滕王阁序教学设计", subject="语文", grade="高一", topic="滕王阁序", generated_content=cls.text)
        cls.note = ResearchNote.objects.create(author=cls.teacher, title="课堂观察", content=cls.text)
        cls.report = ResearchReport.objects.create(author=cls.teacher, title="阶段总结", content=cls.text)
        cls.report.source_notes.add(cls.note)
        cls.review = LessonReview.objects.create(author=cls.teacher, title="课堂诊断", report_content=cls.text)

    def setUp(self):
        self.client.force_login(self.leader)
        self.target = reverse("teaching_feedback_new") + f"?kind=plans&object={self.plan.pk}"
        self.payload = {"strengths": "目标清楚", "suggestions": "增加学生互评环节", "action_plan": "下次课尝试同伴量规互评", "action": "send"}

    def test_readable_detail_and_original_edit_path_remain_available(self):
        for obj in (self.plan, self.note, self.report, self.review):
            url = reverse(f"admin:learning_{obj._meta.model_name}_change", args=[obj.pk])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'class="reading-document"')
            self.assertContains(response, "<strong>学生</strong>")
            self.assertContains(response, "<table>")
            self.assertContains(response, "地灵 —— 人杰")
            self.assertNotContains(response, "<textarea")
            self.assertContains(response, "编辑内容")
            self.assertContains(self.client.get(url, {"_edit": "1"}), "<textarea")
        self.assertContains(self.client.get(reverse("admin:learning_researchreport_change", args=[self.report.pk])), "课堂观察")
        download = self.client.get(reverse("teaching_document_download", args=["plans", self.plan.pk]))
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download.content.startswith(b"PK"))

    def test_markdown_rendering_blocks_active_html_unsafe_links_and_remote_images(self):
        html, toc = render_document('# 标题\n<script>alert(1)</script>\n\n[危险](javascript:alert(1))\n\n![外部图片](https://example.com/a.png)')
        self.assertNotIn("<script>", html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(toc[0]["anchor"], "reading-section-1")
        board, _ = render_document("```text\n---\n**亮点**\n↓\n```\n\n**姓名***：老师")
        self.assertIn("---\n**亮点**\n↓", board)
        self.assertIn("<strong>姓名</strong>：老师", board)

    def test_detail_permission_is_enforced_and_does_not_open_teacher_archive(self):
        self.client.force_login(self.reader)
        url = reverse("admin:learning_lessonplan_change", args=[self.plan.pk])
        response = self.client.get(url)
        self.assertContains(response, "教学目标")
        self.assertNotContains(response, "给予指导")
        self.assertNotContains(response, "查看教师成长档案")
        self.assertEqual(self.client.get(reverse("teacher_workspace", args=[self.teacher.teacher_profile.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:learning_researchreport_change", args=[self.report.pk])).status_code, 403)
        self.assertEqual(self.client.post(self.target, self.payload).status_code, 403)
        self.assertEqual(self.client.get(reverse("teaching_document_download", args=["reports", self.report.pk])).status_code, 403)

    def test_publish_resolves_recipient_from_artifact_and_creates_notice_and_audit(self):
        response = self.client.post(self.target, {**self.payload, "teacher": self.other.pk, "status": "done"})
        self.assertEqual(response.status_code, 302)
        item = TeachingFeedback.objects.get()
        self.assertEqual(item.teacher, self.teacher)
        self.assertEqual(item.status, "sent")
        self.assertEqual(item.reviewer, self.leader)
        self.assertIsNotNone(item.sent_at)
        self.assertEqual(InAppNotice.objects.get(user=self.teacher).link, f"/guidance/{item.pk}")
        self.assertEqual(self.leader.logentry_set.count(), 1)
        self.assertEqual(self.client.get(reverse("teaching_feedback_edit", args=[item.pk])).status_code, 403)

    def test_draft_is_private_editable_and_publishing_notifies_once(self):
        self.client.post(self.target, {**self.payload, "action": "draft"})
        item = TeachingFeedback.objects.get()
        self.assertEqual(InAppNotice.objects.count(), 0)
        other_leader = User.objects.create_superuser("other_guide", password="test-only")
        client = Client()
        client.force_login(other_leader)
        self.assertNotContains(client.get(reverse("teacher_workspace", args=[self.teacher.teacher_profile.pk])), self.payload["suggestions"])
        api = APIClient()
        api.force_authenticate(self.teacher)
        self.assertEqual(api.get("/api/teaching-feedback/").data["count"], 0)
        self.assertEqual(api.get(f"/api/teaching-feedback/{item.pk}/").status_code, 404)
        edit = reverse("teaching_feedback_edit", args=[item.pk])
        self.assertContains(self.client.get(edit), self.payload["suggestions"])
        self.assertEqual(self.client.post(edit, self.payload).status_code, 302)
        self.assertEqual(InAppNotice.objects.filter(user=self.teacher).count(), 1)
        self.assertEqual(self.client.post(edit, self.payload).status_code, 403)
        self.assertEqual(InAppNotice.objects.filter(user=self.teacher).count(), 1)

    def test_invalid_feedback_and_changed_recipient_do_not_leak_or_send(self):
        self.assertEqual(self.client.post(self.target, {"suggestions": "  ", "action": "send"}).status_code, 400)
        self.assertEqual(self.client.post(self.target, {**self.payload, "action": "oops"}).status_code, 400)
        self.assertEqual(self.client.post(self.target, {**self.payload, "suggestions": "长" * 5001}).status_code, 400)
        self.assertEqual(TeachingFeedback.objects.count(), 0)
        self.client.post(self.target, {**self.payload, "action": "draft"})
        item = TeachingFeedback.objects.get()
        LessonPlan.objects.filter(pk=self.plan.pk).update(author=self.other)
        self.assertEqual(self.client.post(reverse("teaching_feedback_edit", args=[item.pk]), self.payload).status_code, 403)
        self.assertEqual(InAppNotice.objects.count(), 0)

    def test_teacher_completion_is_owner_only_and_returns_to_leader(self):
        self.client.post(self.target, self.payload)
        item = TeachingFeedback.objects.get()
        api = APIClient()
        api.force_authenticate(self.other)
        self.assertEqual(api.get(f"/api/teaching-feedback/{item.pk}/").status_code, 404)
        self.assertEqual(api.post(f"/api/teaching-feedback/{item.pk}/", {"teacher_reply": "伪造"}).status_code, 404)
        api.force_authenticate(self.teacher)
        endpoint = f"/api/teaching-feedback/{item.pk}/"
        self.assertEqual(api.post(endpoint, {"teacher_reply": ""}).status_code, 400)
        response = api.post(endpoint, {"teacher_reply": "已在课堂试用量规，学生能据此互评。", "suggestions": "篡改"})
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.status, "done")
        self.assertEqual(item.suggestions, self.payload["suggestions"])
        self.assertEqual(InAppNotice.objects.filter(user=self.leader).count(), 1)
        self.assertEqual(api.post(endpoint, {"teacher_reply": "重复"}).status_code, 400)
        self.assertEqual(InAppNotice.objects.filter(user=self.leader).count(), 1)
        self.assertContains(self.client.get(reverse("teacher_workspace", args=[self.teacher.teacher_profile.pk])), "已在课堂试用量规")

    def test_evidence_summary_excludes_drafts_and_respects_date_school_and_owner(self):
        form = DashboardFilters({})
        self.assertTrue(form.is_valid())
        dashboard = build_dashboard(form.cleaned_data)
        self.assertEqual(guidance_evidence(self.leader, dashboard)["pending"], 4)
        self.client.post(self.target, {**self.payload, "action": "draft"})
        self.assertEqual(guidance_evidence(self.leader, dashboard)["pending"], 4)
        self.client.post(reverse("teaching_feedback_edit", args=[TeachingFeedback.objects.get().pk]), self.payload)
        self.assertEqual(guidance_evidence(self.leader, dashboard)["pending"], 3)
        start = timezone.localdate() - timedelta(days=10)
        end = timezone.localdate() - timedelta(days=5)
        old = DashboardFilters({"start": start.isoformat(), "end": end.isoformat()})
        self.assertTrue(old.is_valid())
        self.assertEqual(guidance_evidence(self.leader, build_dashboard(old.cleaned_data))["pending"], 0)
        response = self.client.get(reverse("guidance_workbench"), {"state": "pending"})
        self.assertContains(response, "张老师")
        self.assertNotContains(response, "guide_other</strong>")

    def test_phase_feedback_and_teacher_read_page_do_not_change_data_on_get(self):
        before = TeachingFeedback.objects.count()
        self.assertEqual(self.client.get(reverse("teacher_workspace", args=[self.teacher.teacher_profile.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:core_teacherprofile_change", args=[self.teacher.teacher_profile.pk])).status_code, 200)
        self.assertEqual(TeachingFeedback.objects.count(), before)
        endpoint = reverse("teaching_feedback_new") + f"?teacher={self.teacher.teacher_profile.pk}"
        self.assertEqual(self.client.post(endpoint, self.payload).status_code, 302)
        self.assertEqual(TeachingFeedback.objects.get().kind, "teacher")

    def test_guidance_role_can_send_but_cannot_leave_uneditable_drafts(self):
        self.reader.user_permissions.add(*Permission.objects.filter(content_type__app_label="core", codename__in=["view_teachingfeedback", "add_teachingfeedback"]))
        self.client.force_login(self.reader)
        response = self.client.get(self.target)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="draft"')
        self.assertEqual(self.client.post(self.target, {**self.payload, "action": "draft"}).status_code, 403)
        self.assertEqual(self.client.post(self.target, self.payload).status_code, 302)
        self.assertEqual(TeachingFeedback.objects.get().status, "sent")
