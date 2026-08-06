"""وارد کردن سرفصل‌های مصوب از یک پوشهٔ PDF.

    python manage.py import_curricula --source /home/cp29524/apps/university_site/media/_incoming/سرفصل

چرا فایل‌ها در گیت نیستند
─────────────────────────
این سرفصل‌ها روی هم حدود ۳۰۰ مگابایت‌اند. گذاشتن‌شان در مخزن یعنی هر
کلون و هر «Update from Remote» روی سرور همان ۳۰۰ مگابایت را دوباره
می‌کشد، و مخزن برای همیشه سنگین می‌ماند چون گیت تاریخچه را دور
نمی‌ریزد. راه درست: فایل‌ها یک بار مستقیم در `media/` سرور آپلود
می‌شوند و این دستور فقط رکوردشان را در دیتابیس می‌سازد.

پوشه‌بندی مبدأ
──────────────
نام پوشهٔ هر فایل مقطع را تعیین می‌کند («کارشناسی ارشد»، «کاردانی
پیوسته» و…). فایل‌هایی که مستقیم در ریشه‌اند از روی نام خودشان حدس
زده می‌شوند و اگر نشد در «سایر» می‌افتند تا ادمین اصلاح کند.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

from directory.models import CurriculumDocument

# نام پوشه → مقدار فیلد level
FOLDER_LEVELS = {
    'کاردانی پیوسته': 'associate_cont',
    'کاردانی ناپیوسته': 'associate_disc',
    'کارشناسی پیوسته': 'bachelor_cont',
    'کارشناسی ناپیوسته': 'bachelor_disc',
    'کارشناسی ارشد': 'master',
}

# وقتی فایل در ریشه است، از روی نام خودش حدس می‌زنیم. ترتیب مهم است:
# «کارشناسی ناپیوسته» باید پیش از «کارشناسی» بررسی شود.
TITLE_HINTS = [
    ('کارشناسی ارشد', 'master'),
    ('کاردانی ناپیوسته', 'associate_disc'),
    ('کاردانی پیوسته', 'associate_cont'),
    ('کارشناسی ناپیوسته', 'bachelor_disc'),
    ('کارشناسی پیوسته', 'bachelor_cont'),
    ('ناپیوسته', 'bachelor_disc'),
]

# «۱۴۰۰.۱۰.۱۵» یا «۹۹.۱۰.۲۳» در انتهای نام فایل
DATE_RE = re.compile(r'\s*(\d{2,4})\.(\d{1,2})\.(\d{1,2})\s*$')
# تاریخ فشرده و بی‌جداکننده: «۱۳۹۵۱۱۲۳»
COMPACT_DATE_RE = re.compile(r'\s*(13\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\s*$')
# سال تنها در انتها: «۱۴۰۳» یا «۴۰۴» چسبیده یا جدا
YEAR_RE = re.compile(r'\s*(1[34]\d{2}|[34]\d{2})\s*$')


def normalize_digits(text: str) -> str:
    """ارقام لاتین را فارسی می‌کند تا تاریخ‌ها یکدست دیده شوند."""
    table = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return text.translate(table)


def parse_name(stem: str) -> tuple[str, str]:
    """نام فایل را به (عنوان، تاریخ تصویب) می‌شکند."""
    title = stem.strip()
    approved = ''

    # ترتیب مهم است: تاریخ کامل پیش از تاریخ فشرده، و هر دو پیش از
    # «سال تنها» — وگرنه YEAR_RE چهار رقم اول یک تاریخ را می‌بلعد.
    match = DATE_RE.search(title) or COMPACT_DATE_RE.search(title)
    if match:
        year, month, day = match.groups()
        if len(year) == 2:
            year = '13' + year
        elif len(year) == 3:
            year = '1' + year
        approved = normalize_digits('%s/%02d/%02d' % (year, int(month), int(day)))
        title = title[:match.start()].strip()
    else:
        match = YEAR_RE.search(title)
        if match:
            year = match.group(1)
            if len(year) == 3:
                year = '1' + year
            approved = normalize_digits(year)
            title = title[:match.start()].strip()

    title = title.strip(' -–—_')
    # «مهندسی معماری سال ۱۳۹۷» → بعد از برداشتن سال، «سال» تنها می‌ماند
    if title.endswith(' سال'):
        title = title[:-4].rstrip()
    return title, approved


def guess_level(folder_name: str, title: str) -> str:
    if folder_name in FOLDER_LEVELS:
        return FOLDER_LEVELS[folder_name]
    for hint, level in TITLE_HINTS:
        if hint in title:
            return level
    return 'other'


class Command(BaseCommand):
    help = 'ساخت رکورد سرفصل مصوب از فایل‌های PDF یک پوشه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', required=True,
            help='مسیر پوشه‌ای که PDFها در آن هستند (زیرپوشه‌ها هم خوانده می‌شوند)',
        )
        parser.add_argument(
            '--manifest', default='',
            help='فایل JSON همراه بسته؛ عنوان و مقطع را از آن بخوان به‌جای '
                 'حدس زدن از نام فایل. برای وقتی که نام‌ها ASCII شده‌اند.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='فقط گزارش بده، چیزی ننویس',
        )
        parser.add_argument(
            '--move', action='store_true',
            help='فایل را جابه‌جا کن به‌جای کپی (وقتی فضای دیسک کم است)',
        )

    def handle(self, *args, **options):
        source = Path(options['source'])
        if not source.is_dir():
            self.stderr.write('پوشهٔ مبدأ پیدا نشد: %s' % source)
            return

        dry = options['dry_run']
        dest_root = Path(settings.MEDIA_ROOT) / 'curricula'
        created = updated = skipped = 0

        # manifest اختیاری: نام فایل روی دیسک ASCII است و عنوان فارسی
        # و مقطع از این نگاشت می‌آید. این کار حدس زدن از روی نام را
        # کنار می‌گذارد و به رفتار unzip سرور با نام‌های فارسی وابسته نیست.
        manifest: dict[str, dict] = {}
        if options['manifest']:
            manifest_path = Path(options['manifest'])
            if not manifest_path.is_file():
                self.stderr.write('manifest پیدا نشد: %s' % manifest_path)
                return
            entries = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest = {e['file'].replace('\\', '/'): e for e in entries}
            self.stdout.write('manifest با %d رکورد خوانده شد.' % len(manifest))

        pdfs = sorted(source.rglob('*.pdf'))
        if not pdfs:
            self.stderr.write('هیچ فایل PDF در %s پیدا نشد.' % source)
            return

        self.stdout.write('%d فایل PDF پیدا شد.\n' % len(pdfs))

        # دو فایل با یک کلید یعنی یکی روی دیگری نوشته می‌شود؛ باید
        # دیده شود، نه اینکه بی‌صدا یک سند گم شود.
        seen_keys: dict[tuple, str] = {}
        collisions: list[str] = []

        for index, path in enumerate(pdfs, start=1):
            key = path.relative_to(source).as_posix()
            entry = manifest.get(key)
            if entry:
                title = entry['title']
                level = entry.get('level', 'other')
                approved = entry.get('approved_on', '')
            else:
                if manifest:
                    self.stdout.write(self.style.WARNING(
                        '  ! در manifest نبود، از نام فایل حدس زده شد: %s' % key))
                title, approved = parse_name(path.stem)
                level = guess_level(path.parent.name, path.stem)

            if not title:
                skipped += 1
                continue

            key = (level, title, approved)
            if key in seen_keys:
                collisions.append('%s  ↔  %s' % (seen_keys[key], path.name))
            seen_keys[key] = path.name

            rel = 'curricula/%s/%s' % (level, path.name)
            if not dry:
                target = dest_root / level / path.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if options['move']:
                    shutil.move(str(path), str(target))
                else:
                    shutil.copy2(str(path), str(target))

                obj, was_created = CurriculumDocument.objects.update_or_create(
                    level=level,
                    title=title,
                    approved_on=approved,
                    defaults={
                        'file': rel,
                        'order': index,
                        'is_active': True,
                    },
                )
                created += was_created
                updated += not was_created
            else:
                exists = CurriculumDocument.objects.filter(
                    level=level, title=title, approved_on=approved).exists()
                created += not exists
                updated += exists

            self.stdout.write('  [%s] %s%s' % (
                dict(CurriculumDocument.LEVEL_CHOICES)[level],
                title,
                ('  (%s)' % approved) if approved else '',
            ))

        verb = 'می‌شد ساخت' if dry else 'ساخته شد'
        self.stdout.write(self.style.SUCCESS(
            '\n%d رکورد %s، %d به‌روز شد%s.' % (
                created, verb, updated, (', %d رد شد' % skipped) if skipped else '')))

        if collisions:
            self.stdout.write(self.style.WARNING(
                '\n%d فایل با فایل دیگری هم‌کلید بود و فقط آخری ماند:'
                % len(collisions)))
            for line in collisions:
                self.stdout.write('  - %s' % line)
            self.stdout.write(
                'اگر واقعاً دو سند متفاوت‌اند، در ادمین عنوان یکی را عوض کنید.')
        if dry:
            self.stdout.write('حالت آزمایشی بود — هیچ فایلی کپی نشد.')
        else:
            self.stdout.write('فایل‌ها در %s' % (dest_root,))
