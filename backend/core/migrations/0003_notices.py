import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_teacherprofile_avatar"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="teacherprofile",
            name="notify_community",
            field=models.BooleanField(default=True, verbose_name="社区互动提醒"),
        ),
        migrations.AddField(
            model_name="teacherprofile",
            name="notify_lesson",
            field=models.BooleanField(default=True, verbose_name="教学生成提醒"),
        ),
        migrations.CreateModel(
            name="InAppNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("lesson", "教学设计"), ("report", "教研报告"), ("review", "听评课"), ("community", "社区互动"), ("system", "系统")], default="system", max_length=20, verbose_name="类型")),
                ("title", models.CharField(max_length=80, verbose_name="标题")),
                ("body", models.CharField(blank=True, default="", max_length=300, verbose_name="摘要")),
                ("link", models.CharField(blank=True, default="", max_length=200, verbose_name="跳转")),
                ("is_read", models.BooleanField(default=False, verbose_name="已读")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notices", to=settings.AUTH_USER_MODEL, verbose_name="用户")),
            ],
            options={
                "verbose_name": "站内通知",
                "verbose_name_plural": "站内通知",
                "ordering": ["-created_at"],
            },
        ),
    ]
