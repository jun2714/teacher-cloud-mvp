from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0003_assistant_attachment")]
    operations = [migrations.AddField(
        model_name="lessonreview", name="material_kind",
        field=models.CharField(max_length=20, default="classroom", verbose_name="材料类型", choices=[
            ("classroom", "课堂实录"), ("lesson_plan", "教案资料"), ("mixed", "教案与课堂实录"),
        ]),
    )]
