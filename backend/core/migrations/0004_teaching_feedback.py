# Teaching feedback plus existing teacher-profile display metadata alignment.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_notices"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="teacherprofile",
            options={"verbose_name": "教师档案", "verbose_name_plural": "教师档案"},
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="avatar_text",
            field=models.CharField(
                blank=True, default="", max_length=4, verbose_name="头像文字"
            ),
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="department",
            field=models.CharField(
                default="语文教研组", max_length=100, verbose_name="教研组"
            ),
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="grade",
            field=models.CharField(default="高一", max_length=40, verbose_name="年级"),
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="school_name",
            field=models.CharField(
                default="吴忠市吴忠中学", max_length=100, verbose_name="学校"
            ),
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="subject",
            field=models.CharField(default="语文", max_length=40, verbose_name="学科"),
        ),
        migrations.AlterField(
            model_name="teacherprofile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="teacher_profile",
                to=settings.AUTH_USER_MODEL,
                verbose_name="用户",
            ),
        ),
        migrations.CreateModel(
            name="TeachingFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("teacher", "阶段指导"),
                            ("plans", "教学设计"),
                            ("reviews", "听评课"),
                            ("notes", "教研笔记"),
                            ("reports", "教研报告"),
                        ],
                        default="teacher",
                        max_length=16,
                        verbose_name="指导类型",
                    ),
                ),
                (
                    "object_id",
                    models.PositiveBigIntegerField(
                        blank=True, null=True, verbose_name="关联成果编号"
                    ),
                ),
                (
                    "target_title",
                    models.CharField(max_length=200, verbose_name="指导对象"),
                ),
                (
                    "strengths",
                    models.TextField(blank=True, default="", verbose_name="值得肯定"),
                ),
                ("suggestions", models.TextField(verbose_name="改进建议")),
                (
                    "action_plan",
                    models.TextField(blank=True, default="", verbose_name="下一步行动"),
                ),
                (
                    "follow_up_date",
                    models.DateField(blank=True, null=True, verbose_name="跟进日期"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "草稿"),
                            ("sent", "待落实"),
                            ("done", "已落实"),
                        ],
                        default="draft",
                        max_length=12,
                        verbose_name="状态",
                    ),
                ),
                (
                    "teacher_reply",
                    models.TextField(
                        blank=True, default="", verbose_name="教师落实说明"
                    ),
                ),
                (
                    "sent_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="发送时间"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="落实时间"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="given_teaching_feedback",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="指导人",
                    ),
                ),
                (
                    "teacher",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="teaching_feedback",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="教师",
                    ),
                ),
            ],
            options={
                "verbose_name": "教研指导反馈",
                "verbose_name_plural": "教研指导反馈",
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(
                        fields=["teacher", "status"], name="feedback_teacher_status"
                    ),
                    models.Index(fields=["kind", "object_id"], name="feedback_target"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("kind", "teacher"), ("object_id__isnull", True)),
                            models.Q(
                                ("kind__in", ["plans", "reviews", "notes", "reports"]),
                                ("object_id__isnull", False),
                            ),
                            _connector="OR",
                        ),
                        name="feedback_target_consistent",
                    )
                ],
            },
        ),
    ]
