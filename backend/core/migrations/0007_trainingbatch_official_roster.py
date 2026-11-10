from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0006_seed_training_batches')]
    operations = [
        migrations.AddField(model_name='trainingbatch', name='official_roster', field=models.JSONField('正式名单快照', default=list, blank=True)),
        migrations.AddField(model_name='trainingbatch', name='roster_source', field=models.CharField('正式名单来源', max_length=200, blank=True, default='')),
    ]
