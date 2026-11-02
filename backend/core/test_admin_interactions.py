from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse

from community.models import Answer, Question
from learning.models import AssistantChat, AssistantMessage


class InteractionReadingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("interaction_admin", password="test-only")
        cls.teacher = User.objects.create_user("interaction_teacher", first_name="李老师")
        cls.chat = AssistantChat.objects.create(author=cls.teacher, title="阅读课堂如何设计互评")
        cls.message = AssistantMessage.objects.create(chat=cls.chat, role="user", content="## 教师的问题\n\n如何组织**同伴互评**？", attachment="assistant/files/test.docx", attachment_name="互评材料.docx")
        cls.reply = AssistantMessage.objects.create(chat=cls.chat, role="assistant", content="## 活动建议\n\n|环节|评价|\n|---|---|\n|朗读|互评|\n\n<script>alert(1)</script>")
        cls.question = Question.objects.create(author=cls.teacher, title="怎样让学生主动提问", content="## 课堂现象\n\n学生回答问题积极，但不愿主动提问。", tags=["课堂互动", "语文"], subject="语文")
        cls.answer = Answer.objects.create(question=cls.question, author=cls.teacher, content="**实践建议**：先分组整理问题。", is_accepted=True)
        cls.ai_answer = Answer.objects.create(question=cls.question, answer_type="ai", content="AI 独立回答正文")

    def setUp(self):
        self.client.force_login(self.admin)

    def url(self, obj):
        return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])

    def test_all_interaction_details_show_content_and_keep_edit_forms(self):
        expected = [(self.chat, "同伴互评"), (self.message, "互评材料.docx"), (self.question, "先分组整理问题"), (self.answer, "实践建议"), (self.ai_answer, "AI 独立回答正文")]
        for obj, text in expected:
            response = self.client.get(self.url(obj))
            self.assertContains(response, text)
            self.assertContains(response, "编辑记录")
            self.assertNotContains(response, "<textarea")
            self.assertContains(self.client.get(self.url(obj), {"_edit": "1"}), 'id="id_author"' if obj in (self.chat, self.question, self.answer, self.ai_answer) else 'id="id_content"')
        chat = self.client.get(self.url(self.chat))
        self.assertContains(chat, "<table>")
        self.assertNotContains(chat, "<script>alert(1)</script>")
        self.assertContains(chat, "&lt;script&gt;")
        self.assertContains(chat, f'entry-assistantmessage-{self.message.pk}-1')
        question = self.client.get(self.url(self.question))
        self.assertContains(question, "已采纳")
        self.assertContains(question, "AI 参考回答")
        self.assertContains(question, "课堂互动")

    def test_parent_permission_does_not_grant_child_content_access(self):
        reader = User.objects.create_user("parent_only", is_staff=True)
        reader.user_permissions.add(*Permission.objects.filter(codename__in=["view_assistantchat", "view_question"]))
        self.client.force_login(reader)
        self.assertNotContains(self.client.get(self.url(self.chat)), "同伴互评")
        self.assertNotContains(self.client.get(self.url(self.question)), "先分组整理问题")
        self.assertContains(self.client.get(self.url(self.chat)), "当前账号没有内容查看权限")
        self.assertEqual(self.client.get(self.url(self.reply)).status_code, 403)
        self.assertEqual(self.client.get(self.url(self.answer)).status_code, 403)

    def test_child_only_permission_does_not_expose_parent_body_or_edit(self):
        reader = User.objects.create_user("child_only", is_staff=True)
        reader.user_permissions.add(*Permission.objects.filter(codename__in=["view_assistantmessage", "view_answer"]))
        self.client.force_login(reader)
        response = self.client.get(self.url(self.ai_answer))
        self.assertContains(response, "AI 独立回答正文")
        self.assertNotContains(response, "学生回答问题积极")
        self.assertNotContains(response, "查看原问题与全部回答")
        self.assertNotContains(response, "编辑记录")
        self.assertEqual(self.client.post(self.url(self.ai_answer), {"content": "篡改"}).status_code, 403)
        self.assertEqual(self.client.get(self.url(self.chat)).status_code, 403)
        self.assertEqual(Client().get(self.url(self.reply)).status_code, 302)

    def test_ordering_pagination_and_empty_states(self):
        for i in range(31):
            AssistantMessage.objects.create(chat=self.chat, role="user", content=f"延伸讨论-{i}")
        page = self.client.get(self.url(self.chat))
        self.assertEqual(page.context["thread_page"].paginator.count, 33)
        self.assertEqual(len(page.context["entries"]), 30)
        self.assertEqual(page.context["statistics"], [("消息总数", 33), ("教师提问", 32), ("助手回复", 1)])
        self.assertEqual(page.context["entries"][0]["pk"], self.message.pk)
        self.assertEqual(len(self.client.get(self.url(self.chat), {"page": 2}).context["entries"]), 3)
        empty = AssistantChat.objects.create(author=self.teacher, title="尚未开始的讨论")
        self.assertContains(self.client.get(self.url(empty)), "暂无对话消息")
        unanswered = Question.objects.create(author=self.teacher, title="尚未解答", content="问题说明")
        self.assertContains(self.client.get(self.url(unanswered)), "暂时没有回答")

    def test_reading_keeps_saved_data_and_native_edit_submission(self):
        before = (AssistantMessage.objects.count(), Answer.objects.count(), self.question.status)
        self.client.get(self.url(self.question))
        self.client.get(self.url(self.chat))
        self.question.refresh_from_db()
        self.assertEqual(before, (AssistantMessage.objects.count(), Answer.objects.count(), self.question.status))
        response = self.client.post(self.url(self.chat), {"author": self.teacher.pk, "title": "更新后的教学交流", "_save": "保存"})
        self.assertEqual(response.status_code, 302)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.title, "更新后的教学交流")
