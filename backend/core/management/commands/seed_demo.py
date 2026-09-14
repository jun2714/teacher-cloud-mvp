from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import TeacherProfile
from learning.models import ResearchNote, LessonPlan, LessonReview
from community.models import Question, Answer

class Command(BaseCommand):
    help = "创建演示账号与演示数据"

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True, "first_name": "管理员"})
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password("admin123456")
        admin.save()

        teacher, _ = User.objects.get_or_create(username="teacher", defaults={"first_name": "张老师"})
        teacher.set_password("teacher123")
        teacher.save()
        profile = teacher.teacher_profile
        profile.school_name = "吴忠市吴忠中学"
        profile.subject = "语文"
        profile.grade = "高一"
        profile.department = "高一语文组"
        profile.avatar_text = "张"
        profile.save()

        old_grades = [
            "一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
            "七年级", "八年级", "九年级",
        ]
        TeacherProfile.objects.filter(grade__in=old_grades).update(grade="高一")
        ResearchNote.objects.filter(grade__in=old_grades).update(grade="高一")
        Question.objects.filter(grade__in=old_grades).update(grade="高一")
        LessonPlan.objects.filter(grade__in=old_grades).update(grade="高一")
        LessonReview.objects.filter(grade__in=old_grades).update(grade="高一")

        if not ResearchNote.objects.filter(author=teacher).exists():
            ResearchNote.objects.create(
                author=teacher,
                title="新课标核心素养导向的教学设计思考",
                content="通过深入学习新课标，认识到教学要从知识传授转向素养培养。课堂中需要重视文化自信、语言运用、思维能力和审美创造。",
                category="reflection",
                subject="语文",
                grade="高一",
                tags=["新课标", "核心素养", "教学设计"],
            )
            ResearchNote.objects.create(
                author=teacher,
                title="新课改背景下大单元教学的实践感悟",
                content="尝试设计大单元教学方案，通过整合教材内容、创设真实情境任务，学生的学习积极性明显提升。",
                category="learning",
                subject="语文",
                grade="高一",
                tags=["新课改", "大单元教学", "情境任务"],
            )

        if not Question.objects.exists():
            q = Question.objects.create(
                author=teacher,
                title='新课标中“学习任务群”如何有效落地？',
                content="新课标提出了学习任务群的概念，但在实际教学中，如何设计既符合课标要求又适合学生学情的学习任务群？",
                subject="语文",
                grade="高一",
                tags=["新课标", "学习任务群", "教学设计"],
                status="discussing",
                ask_ai=True,
            )
            Answer.objects.create(
                question=q,
                answer_type="ai",
                content="可以从真实情境、核心任务、连续活动和评价证据四个方面设计。先明确单元要解决的真实问题，再将任务拆成若干递进活动，每个活动都保留可观察的学习成果。",
            )
            Answer.objects.create(
                question=q,
                author=teacher,
                answer_type="teacher",
                content="我们组的做法是先确定单元核心问题，再围绕阅读、表达和实践设计三层任务，效果比逐课设计更连贯。",
            )

        self.stdout.write(self.style.SUCCESS("演示账号与数据已准备完成"))
