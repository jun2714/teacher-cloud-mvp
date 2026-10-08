from django.db import migrations
from django.db.models import Value
from django.db.models.functions import Replace


OLD_NAME = "吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地"
NEW_NAME = "吴忠中学教师跟岗实践暨“县中帮扶”交流培训"


def update_program_name(apps, schema_editor):
    # Update stored generated documents so history and Word downloads agree.
    for model_name, content_field in [
        ("LessonPlan", "generated_content"),
        ("ResearchReport", "content"),
        ("LessonReview", "report_content"),
    ]:
        model = apps.get_model("learning", model_name)
        for field in ("title", content_field):
            model.objects.using(schema_editor.connection.alias).filter(
                **{f"{field}__contains": OLD_NAME}
            ).update(**{field: Replace(field, Value(OLD_NAME), Value(NEW_NAME))})


class Migration(migrations.Migration):
    dependencies = [("learning", "0004_lessonreview_material_kind")]
    operations = [migrations.RunPython(update_program_name, migrations.RunPython.noop)]
