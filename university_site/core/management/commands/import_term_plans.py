"""وارد کردن ترم‌بندی رشته‌ها.

ترم‌بندی چیست و چرا جدا از سرفصل است
────────────────────────────────────
«سرفصل مصوب» سند ابلاغی وزارت است: چه درس‌هایی با چند واحد. «ترم‌بندی»
برنامهٔ خود موسسه است: کدام درس در کدام ترم. دانشجویی که می‌خواهد
بداند ترم بعد چه بردارد، دومی را می‌خواهد نه اولی — و تا امروز هیچ‌جای
سایت نبود.

چرا این فایل‌ها در مخزن‌اند ولی سرفصل‌ها نه
────────────────────────────────────────────
ترم‌بندی‌ها روی هم ۱۱ مگابایت‌اند، سرفصل‌ها ۳۰۰ مگابایت. آن حجم مخزن
را برای همیشه سنگین می‌کرد، ولی این یکی می‌تواند بماند — و ماندنش یعنی
با هر دیپلوی خودکار سر جایش می‌رود، بدون آپلود دستی.

نام فایل‌ها ASCII است و عنوان فارسی در manifest می‌آید؛ همان دلیل
سرفصل‌ها: پروسهٔ Passenger روی این سرور locale ندارد.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import DownloadableDocument

SEED_DIR = Path(__file__).resolve().parents[2] / 'seed_files' / 'term_plans'
MANIFEST = SEED_DIR / 'manifest.json'


class Command(BaseCommand):
    help = 'وارد کردن ترم‌بندی رشته‌ها به آیین‌نامه‌ها و فرم‌ها'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='فقط گزارش بده')
        parser.add_argument(
            '--replace-files', action='store_true',
            help='فایل را حتی اگر از قبل هست دوباره بنویس',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not MANIFEST.exists():
            self.stderr.write('manifest پیدا نشد: %s' % MANIFEST)
            return

        records = json.loads(MANIFEST.read_text(encoding='utf-8'))
        dry = options['dry_run']
        created = updated = 0

        for index, record in enumerate(records, start=1):
            title = record['title']
            level = record['degree_level']

            if dry:
                exists = DownloadableDocument.objects.filter(
                    title=title, degree_level=level).exists()
                created += not exists
                updated += exists
                self.stdout.write('  [%s] %s' % (level, title))
                continue

            doc, was_created = DownloadableDocument.objects.get_or_create(
                title=title,
                degree_level=level,
                defaults={
                    'category': 'guide',
                    'section': 'academic',
                    'description': 'برنامهٔ ترم‌به‌ترم دروس این رشته',
                    'order': index,
                    'is_active': True,
                },
            )
            created += was_created
            updated += not was_created

            self._attach(doc, 'file', record.get('file'),
                         options['replace_files'])
            self._attach(doc, 'word_file', record.get('word'),
                         options['replace_files'])

            self.stdout.write('  [%s] %s' % (level, title))

        verb = 'می‌شد ساخت' if dry else 'ساخته شد'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            '%d ترم‌بندی %s، %d به‌روز شد.' % (created, verb, updated)))
        if dry:
            self.stdout.write('حالت آزمایشی بود — چیزی نوشته نشد.')

    def _attach(self, doc, field: str, filename: str | None, replace: bool):
        """فایل را ضمیمه می‌کند؛ نسخهٔ آپلودشده در ادمین دست نمی‌خورد."""
        if not filename:
            return
        current = getattr(doc, field, None)
        if current and not replace:
            return
        source = SEED_DIR / filename
        if not source.exists():
            self.stderr.write('  فایل نیست: %s' % filename)
            return
        getattr(doc, field).save(
            filename, ContentFile(source.read_bytes()), save=True)
