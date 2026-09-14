from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0002_assistant_chat"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistantmessage",
            name="attachment",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="assistant/files/%Y/%m/",
                verbose_name="附件",
            ),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="attachment_name",
            field=models.CharField(
                blank=True, default="", max_length=200, verbose_name="附件名"
            ),
        ),
    ]
