import json, os, sqlite3, sys, secrets
from pathlib import Path
root = Path(__file__).resolve().parents[3] / 'backend'
sys.path.insert(0, str(root))
from dotenv import load_dotenv
load_dotenv(root / '.env')
source = Path(os.environ.get('SQLITE_PATH', str(root / 'db.sqlite3')))
if not source.is_absolute(): source = root / source
preview = root / 'data' / 'dashboard-preview.sqlite3'
preview.parent.mkdir(parents=True, exist_ok=True)
if source.exists():
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original, sqlite3.connect(str(preview)) as copy:
        original.backup(copy)
os.environ.update(SQLITE_PATH=str(preview), DJANGO_SETTINGS_MODULE='config.settings', DEBUG='1', ALLOWED_HOSTS='127.0.0.1,localhost,testserver', SECRET_KEY=secrets.token_urlsafe(48))
import django
django.setup()
from django.core.management import call_command
call_command('migrate', verbosity=0)
from django.contrib.auth.models import User
from django.test import Client
user = User.objects.filter(is_superuser=True, is_active=True).first()
if not user:
    user = User.objects.create_superuser('dashboard_preview', password=None)
client = Client()
client.force_login(user)
from learning.models import AssistantChat, AssistantMessage, LessonPlan, ResearchReport
from community.models import Question, Answer
from rest_framework_simplejwt.tokens import AccessToken
teacher = User.objects.filter(is_staff=False, lesson_plans__isnull=False).distinct().order_by('pk').first()
if not teacher:
    teacher = User.objects.create_user('guidance_browser_teacher', first_name='浏览器验证教师')
    LessonPlan.objects.create(author=teacher, title='阅读教学设计', subject='语文', grade='高一', topic='阅读', generated_content='# 教学设计\n\n## 教学目标\n\n理解文章内容。')
plan = LessonPlan.objects.filter(author=teacher).order_by('-created_at').first()
report = ResearchReport.objects.filter(author=teacher).first()
if not report:
    report = ResearchReport.objects.create(author=teacher, title='教研实践阶段总结（浏览器验证）', content='# 阶段总结\n\n## 实践收获\n\n围绕课堂问题开展教研。\n\n## 下一步计划\n\n结合指导建议改进课堂评价。')
chat = AssistantChat.objects.create(author=teacher, title='怎样让课堂互评更有效（浏览器验证）')
chat_message = AssistantMessage.objects.create(chat=chat, role='user', content='## 教师的问题\n\n学生在小组互评时往往只说“很好”，怎样引导他们给出具体建议？', attachment='assistant/files/peer-review.docx', attachment_name='课堂互评材料.docx')
AssistantMessage.objects.create(chat=chat, role='assistant', content='## 活动设计建议\n\n可以先提供**可观察的评价标准**，让学生用作品中的具体例子说明。\n\n|课堂环节|教师支持|\n|---|---|\n|示范评价|展示一条具体反馈|\n|同伴互评|使用简洁的评价量规|\n\n- 先肯定一个优点。\n- 再提出一个可以尝试的改进。')
question = Question.objects.create(author=teacher, title='学生不愿主动提问，如何调整课堂活动？（浏览器验证）', content='## 课堂里的困惑\n\n学生愿意回答教师的问题，但很少主动提出自己的问题。希望交流**问题意识培养**方面的做法。', subject='语文', grade='高一', tags=['课堂互动', '问题意识'], status='solved')
answer = Answer.objects.create(question=question, author=teacher, answer_type='teacher', is_accepted=True, content='## 一次课堂尝试\n\n先让学生在便签上写下自己的疑问，再由小组整理出**最值得讨论的问题**。\n\n- 留出独立思考时间。\n- 允许先写下来再表达。\n- 用追问帮助学生说清理由。')
question.accepted_answer = answer
question.save(update_fields=['accepted_answer'])
Answer.objects.create(question=question, answer_type='ai', content='## 可参考的活动\n\n可尝试“提问卡—小组筛选—全班讨论”的活动流程，并结合本班学情调整。')
(root / 'data' / 'dashboard-browser-session.json').write_text(json.dumps({
    'sessionid': client.cookies['sessionid'].value,
    'teacher_access': str(AccessToken.for_user(teacher)),
    'profile_id': teacher.teacher_profile.pk,
    'plan_id': plan.pk,
    'report_id': report.pk,
    'chat_id': chat.pk,
    'message_id': chat_message.pk,
    'question_id': question.pk,
    'answer_id': answer.pk,
}), encoding='utf-8')
print('Dashboard preview ready on port 8002 (isolated database copy)', flush=True)
call_command('runserver', '127.0.0.1:8002', use_reloader=False)
