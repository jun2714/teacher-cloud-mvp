from datetime import date
from django.db import migrations


def seed_batches(apps, schema_editor):
    Batch = apps.get_model('core', 'TrainingBatch')
    for name, start, end in [
        ('第一批', date(2026, 10, 11), date(2026, 10, 17)),
        ('第二批', date(2026, 10, 18), date(2026, 10, 24)),
        ('第三批', date(2026, 10, 25), date(2026, 10, 31)),
        ('第四批', date(2026, 11, 1), date(2026, 11, 7)),
    ]:
        Batch.objects.using(schema_editor.connection.alias).get_or_create(name=name, start_date=start, end_date=end)


class Migration(migrations.Migration):
    dependencies = [('core', '0005_training_batch')]
    operations = [migrations.RunPython(seed_batches, migrations.RunPython.noop)]
