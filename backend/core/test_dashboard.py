import csv
from datetime import date, datetime
from io import StringIO

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.utils import timezone

from community.models import Answer, Question
from learning.models import AssistantChat, AssistantMessage, LessonPlan, LessonReview, ResearchNote, ResearchReport
from .dashboard import PERMISSIONS


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("dashboard_admin", password="test-only-password")
        cls.alice = User.objects.create_user("teacher_a", first_name="张老师")
        cls.bob = User.objects.create_user("teacher_b", first_name="李老师")
        for user, school, subject in [(cls.alice, "甲校", "语文"), (cls.bob, "乙校", "数学")]:
            User.objects.filter(pk=user.pk).update(date_joined=cls.when("2026-09-01"))
            profile = user.teacher_profile
            profile.school_name, profile.subject = school, subject
            profile.save()
        cls.record(LessonPlan, cls.alice, "2026-10-20", topic="秋天", subject="语文")
        cls.record(LessonPlan, cls.alice, "2026-10-20", topic="阅读", subject="语文")
        cls.record(ResearchNote, cls.alice, "2026-10-20", subject="语文")
        cls.record(ResearchReport, cls.alice, "2026-10-21")
        cls.record(LessonReview, cls.bob, "2026-10-22", subject="数学")
        cls.record(ResearchNote, cls.bob, "2026-09-20", subject="数学")
        cls.record(ResearchNote, cls.admin, "2026-10-21", subject="语文")
        # Shanghai midnight belongs to the 23rd even though the UTC date is the 22nd.
        boundary = cls.record(ResearchNote, cls.alice, "2026-10-23", subject="语文")
        cls.boundary = boundary.pk
        chat = AssistantChat.objects.create(author=cls.bob, title="旧对话")
        AssistantChat.objects.filter(pk=chat.pk).update(created_at=cls.when("2026-09-01"))
        message = AssistantMessage.objects.create(chat=chat, role="user", content="新问题")
        AssistantMessage.objects.filter(pk=message.pk).update(created_at=cls.when("2026-10-24"))
        question = cls.record(Question, cls.alice, "2026-10-24")
        answer = Answer.objects.create(question=question, author=cls.bob, answer_type="ai", content="机器回复不算教师活跃")
        Answer.objects.filter(pk=answer.pk).update(created_at=cls.when("2026-10-25"))

    @staticmethod
    def when(day):
        return timezone.make_aware(datetime.combine(date.fromisoformat(day), datetime.min.time()))

    @classmethod
    def record(cls, model, author, day, **kwargs):
        record = model.objects.create(author=author, title="测试教研内容", **kwargs)
        model.objects.filter(pk=record.pk).update(created_at=cls.when(day))
        return record

    def setUp(self):
        self.client.force_login(self.admin)
        self.params = {"start": "2026-10-01", "end": "2026-10-29"}

    def overview(self, **extra):
        response = self.client.get("/admin/overview/", {**self.params, **extra})
        self.assertEqual(response.status_code, 200)
        return response

    def test_statistics_deduplicate_people_and_exclude_admin_and_ai_activity(self):
        context = self.overview().context
        stats = {row["key"]: row for row in context["stats"]}
        self.assertEqual(context["total"], 6)
        self.assertEqual(stats["teachers"]["value"], 2)
        self.assertEqual(stats["plans"]["value"], 2)
        self.assertEqual(stats["active"]["value"], 2)
        self.assertEqual(context["participation"], 100)
        series = {row["date"]: row for row in context["series"]}
        self.assertEqual(series["2026-10-20"], {"date": "2026-10-20", "active": 1, "content": 3})
        self.assertEqual(series["2026-10-24"]["active"], 2)
        self.assertEqual(series["2026-10-25"]["active"], 0)
        self.assertEqual(context["teachers"][0]["count"], 5)
        self.assertEqual(context["teachers"][0]["days"], 4)
        self.assertEqual(context["subject_count"], 2)
        self.assertEqual(sum(row["count"] for row in context["segments"]), context["total"])

    def test_school_date_and_content_filters_apply_to_every_data_section(self):
        context = self.overview(school="乙校", kind="reviews").context
        self.assertEqual(context["total"], 1)
        self.assertEqual(len(context["teachers"]), 1)
        self.assertEqual(context["latest"][0]["label"], "听评课")
        self.assertEqual(context["subjects"][0]["name"], "数学")
        self.assertEqual(sum(row["content"] for row in context["series"]), 1)
        self.assertEqual(self.overview(school="乙校", kind="plans").context["latest"], [])
        day = self.overview(start="2026-10-23", end="2026-10-23").context
        self.assertEqual(day["total"], 1)
        self.assertEqual(day["series"][0]["content"], 1)

    def test_previous_period_and_school_with_no_data(self):
        context = self.overview(school="乙校").context
        stats = {row["key"]: row for row in context["stats"]}
        self.assertEqual(stats["notes"]["delta"], -1)
        empty = self.overview(school="不存在的学校").context
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["participation"], 0)
        self.assertEqual(empty["teachers"], [])
        self.assertEqual(empty["latest"], [])

    def test_authentication_permissions_export_and_default_admin_landing(self):
        self.assertRedirects(self.client.get("/admin/"), "/admin/overview/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/admin/?manage=1").status_code, 200)
        self.client.logout()
        for url in ("/admin/overview/", "/admin/overview/export/"):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get("/admin/overview/").status_code, 302)
        staff = User.objects.create_user("limited_staff", is_staff=True)
        self.client.force_login(staff)
        for url in ("/admin/overview/", "/admin/overview/export/"):
            self.assertEqual(self.client.get(url).status_code, 403)
        for permission in PERMISSIONS:
            app, codename = permission.split(".")
            staff.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.assertEqual(self.client.get("/admin/overview/", self.params).status_code, 200)

    def test_invalid_dates_and_unknown_options_are_not_silently_accepted(self):
        for params in ({"start": "nonsense"}, {"start": "2026-10-30", "end": "2026-10-01"},
                       {"start": "2020-01-01"}, {"end": "2999-01-01"}, {"kind": "oops"}, {"trend": "999"}):
            for endpoint in ("/admin/overview/", "/admin/overview/export/"):
                self.assertEqual(self.client.get(endpoint, {**self.params, **params}).status_code, 400)

    def test_report_uses_filters_includes_all_teachers_and_escapes_spreadsheet_formulas(self):
        User.objects.filter(pk=self.alice.pk).update(first_name="=DANGEROUS()")
        response = self.client.get("/admin/overview/export/", {**self.params, "school": "甲校"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))
        self.assertTrue(any(row and row[0] == "'=DANGEROUS()" for row in rows))
        self.assertFalse(any("李老师" in row for row in rows))
        self.assertIn(["2026-10-20", "1", "3"], rows)

    def test_remaining_admin_pages_share_the_dashboard_shell(self):
        pages = {
            "/admin/?manage=1": "系统管理",
            "/admin/learning/lessonreview/": "听评课记录",
            "/admin/learning/lessonplan/": "教学设计",
            "/admin/core/teacherprofile/": "教师档案",
            "/admin/community/question/": "问题",
        }
        for url, heading in pages.items():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, "教研管理平台")
            self.assertContains(response, "返回数据看板")
            self.assertContains(response, heading)
        login = Client()
        response = login.get("/admin/login/")
        self.assertContains(response, "管理员登录")
        self.assertContains(response, "教研云管理平台")

    def test_original_login_keeps_animation_and_authentication_redirect(self):
        login = Client()
        url = "/admin/login/?next=/admin/teaching/"
        response = login.get(url)
        self.assertContains(response, 'id="particles-js"')
        self.assertContains(response, "admin/simpleui-x/img/logo.png")
        self.assertNotContains(response, "admin-login-brand")
        failed = login.post(url, {"username": "dashboard_admin", "password": "incorrect", "next": "/admin/teaching/"})
        self.assertTrue(failed.context["form"].non_field_errors())
        self.assertContains(failed, 'value="dashboard_admin"')
        self.assertContains(failed, 'name="next" value="/admin/teaching/"')
        success = login.post(url, {"username": "dashboard_admin", "password": "test-only-password", "next": "/admin/teaching/"})
        self.assertRedirects(success, "/admin/teaching/", fetch_redirect_response=False)

    def test_html_is_escaped_and_chart_data_is_safe_json(self):
        record = ResearchNote.objects.filter(author=self.alice).first()
        record.title = '<img src=x onerror="alert(1)">'
        record.save()
        response = self.overview()
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(response, "&lt;img")
        self.assertNotContains(response, '<img src=x')
        self.assertContains(response, 'id="dashboard-series" type="application/json"')
        self.assertContains(response, "当前未采集浏览量")
