"""Import official rosters without personal ID storage; export all five categories."""
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.archive_exports import CATEGORIES, safe_name, training_evidence, make_archives
from core.models import TrainingBatch, TeacherProfile
from core.official_roster import match_roster, official_summary


class Command(BaseCommand):
    help = '按正式名单核对账号并分别导出五类资料；默认只预检，--apply 保存名单并导出。'

    def add_arguments(self, parser):
        parser.add_argument('--input', required=True)
        parser.add_argument('--output', required=True)
        parser.add_argument('--admin', required=True)
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--confirmed-names', default='', help='已由负责人核对确认的同名账号，逗号分隔；不自动接受其他同名账号。')

    def handle(self, *args, **options):
        admin = get_user_model().objects.filter(username=options['admin'], is_active=True, is_superuser=True).first()
        if admin is None:
            raise CommandError('请指定当前有效的超级管理员账号。')
        source = json.loads(Path(options['input']).read_text(encoding='utf-8-sig'))
        prepared, seen_batches = [], set()
        profiles = list(TeacherProfile.objects.select_related('user').filter(user__is_staff=False))
        for item in source:
            batch = TrainingBatch.objects.get(pk=item['batch'])
            if batch.pk in seen_batches:
                raise CommandError('输入包含重复批次。')
            seen_batches.add(batch.pk)
            if item.get('start') != str(batch.start_date) or item.get('end') != str(batch.end_date):
                raise CommandError('名单日期必须与已配置批次一致。')
            entries = match_roster(item['teachers'], profiles, confirmed_names=set(filter(None, options['confirmed_names'].split(','))))
            prepared.append((batch, entries, Path(item['source']).name))
            self.stdout.write(f'{batch.name}：{official_summary(entries)}')
        if not options['apply']:
            self.stdout.write('预检完成；未修改任何名单或账号。')
            return
        destination = Path(options['output'])
        destination.mkdir(parents=True, exist_ok=False)
        # Snapshot every previous roster before changing the batch, for reversible recovery.
        previous = [dict(batch=b.pk, revision=b.revision, official_roster=b.official_roster,
                         roster_source=b.roster_source, teachers=list(b.teachers.values_list('pk', flat=True)),
                         confirmed_at=b.confirmed_at.isoformat() if b.confirmed_at else None,
                         confirmed_by=b.confirmed_by_id) for b, _, _ in prepared]
        (destination / 'previous-rosters.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding='utf-8')
        with transaction.atomic():
            for batch, entries, filename in prepared:
                changed = TrainingBatch.objects.filter(pk=batch.pk, revision=batch.revision).update(
                    official_roster=entries, roster_source=filename, revision=batch.revision + 1,
                    confirmed_at=timezone.now(), confirmed_by=admin)
                if changed != 1:
                    raise CommandError('名单被其他管理员修改，请重新预检。')
                batch.teachers.set([r['profile_id'] for r in entries if r['profile_id']])
        for batch, entries, _ in prepared:
            batch.refresh_from_db()
            folder = destination / safe_name(f'{batch.name}_{batch.start_date}_{batch.end_date}')
            folder.mkdir()
            for key, label in CATEGORIES:
                data = dict(batch=batch, batch_name=batch.export_name, start=batch.start_date, end=batch.end_date,
                            scope='batch', profiles=list(batch.teachers.select_related('user')), school='',
                            achievement='all', categories=[key])
                response = make_archives(data, training_evidence(data, admin))
                suffix = '.zip' if response['Content-Type'] == 'application/zip' else '.docx'
                target = folder / f'{key}_{label}{suffix}'
                try:
                    with target.open('wb') as f:
                        if response.streaming:
                            for chunk in response.streaming_content:
                                f.write(chunk)
                        else:
                            f.write(response.content)
                finally:
                    response.close()
                if suffix == '.zip':
                    with ZipFile(target) as z:
                        if z.testzip():
                            raise CommandError(f'{target.name} 校验失败。')
                self.stdout.write(f'已生成 {batch.name} {key} ({target.stat().st_size} bytes)')
        # Keep recovery metadata outside the deliverable ZIP.
        with ZipFile(destination / '四批研修分类归档.zip', 'w', ZIP_DEFLATED) as z:
            for folder in sorted(p for p in destination.iterdir() if p.is_dir()):
                for file in sorted(folder.iterdir()):
                    z.write(file, file.relative_to(destination).as_posix())
        self.stdout.write('全部归档完成。原始账号及教师材料未修改。')
