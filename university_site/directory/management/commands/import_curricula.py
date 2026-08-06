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
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
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
            '--source', default='',
            help='مسیر پوشه‌ای که PDFها در آن هستند (زیرپوشه‌ها هم خوانده می‌شوند)',
        )
        parser.add_argument(
            '--manifest', default='',
            help='فایل JSON همراه بسته؛ عنوان و مقطع را از آن بخوان به‌جای '
                 'حدس زدن از نام فایل. برای وقتی که نام‌ها ASCII شده‌اند.',
        )
        parser.add_argument(
            '--zip', dest='zip_path', default='',
            help='خواندن مستقیم از یک فایل zip بدون استخراج کامل. هر PDF '
                 'جدا بیرون کشیده و سر جایش گذاشته می‌شود، پس فضای اضافی '
                 'لازم نیست. manifest.json اگر داخل zip باشد خودکار خوانده می‌شود.',
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
        zip_path = options['zip_path']
        if zip_path:
            archive = Path(zip_path)
            if not archive.is_file():
                self.stderr.write('فایل zip پیدا نشد: %s' % archive)
                return
            with zipfile.ZipFile(archive) as zf:
                self._run(options, *self._from_zip(zf, options))
            return

        source = Path(options['source']) if options['source'] else None
        if not source or not source.is_dir():
            self.stderr.write(
                'پوشهٔ مبدأ پیدا نشد: %s — یا --source بدهید یا --zip.' % source)
            return
        self._run(options, *self._from_folder(source, options))

    # ── دو منبع، یک مسیر پردازش ───────────────────────────────────────
    # هر کدام (manifest، فهرست کار) برمی‌گردانند. هر «کار» یک تاپل است:
    # (کلید نسبی، نام فایل، تابعی که فایل را سر جایش می‌نویسد).

    def _load_manifest(self, raw: str) -> dict:
        entries = json.loads(raw)
        return {e['file'].replace('\\', '/'): e for e in entries}

    def _from_folder(self, source: Path, options):
        manifest = {}
        if options['manifest']:
            manifest_path = Path(options['manifest'])
            if not manifest_path.is_file():
                raise CommandError('manifest پیدا نشد: %s' % manifest_path)
            manifest = self._load_manifest(manifest_path.read_text(encoding='utf-8'))
            self.stdout.write('manifest با %d رکورد خوانده شد.' % len(manifest))

        jobs = []
        for path in sorted(source.rglob('*.pdf')):
            key = path.relative_to(source).as_posix()

            def write(target, _p=path, _move=options['move']):
                if _move:
                    shutil.move(str(_p), str(target))
                else:
                    shutil.copy2(str(_p), str(target))

            jobs.append((key, path.name, path.parent.name, path.stem, write))
        return manifest, jobs

    def _from_zip(self, zf: zipfile.ZipFile, options):
        """خواندن مستقیم از آرشیو — هر PDF جدا بیرون کشیده می‌شود.

        دلیلش فضای دیسک است: استخراج کامل ۳۰۰ مگابایت یعنی یک لحظه
        دو نسخه از همان فایل‌ها روی هاست اشتراکی. اینجا فقط یک فایل
        در هر لحظه در حافظه است.
        """
        manifest = {}
        names = zf.namelist()

        # manifest داخل آرشیو مقدم است؛ اگر نبود، از --manifest
        inner = next((n for n in names if n.endswith('manifest.json')), '')
        if inner:
            manifest = self._load_manifest(zf.read(inner).decode('utf-8'))
            self.stdout.write(
                'manifest از داخل zip خوانده شد (%d رکورد).' % len(manifest))
        elif options['manifest']:
            manifest_path = Path(options['manifest'])
            if not manifest_path.is_file():
                raise CommandError('manifest پیدا نشد: %s' % manifest_path)
            manifest = self._load_manifest(manifest_path.read_text(encoding='utf-8'))

        jobs = []
        for name in sorted(n for n in names if n.lower().endswith('.pdf')):
            posix = name.replace('\\', '/')
            base = posix.rsplit('/', 1)[-1]
            folder = posix.rsplit('/', 2)[-2] if '/' in posix else ''

            def write(target, _n=name):
                with zf.open(_n) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)

            jobs.append((posix, base, folder, base[:-4], write))
        return manifest, jobs

    def _run(self, options, manifest: dict, jobs: list):
        if not jobs:
            self.stderr.write('هیچ فایل PDF پیدا نشد.')
            return

        dry = options['dry_run']
        dest_root = Path(settings.MEDIA_ROOT) / 'curricula'
        created = updated = skipped = 0

        self.stdout.write('%d فایل PDF پیدا شد.\n' % len(jobs))

        # دو فایل با یک کلید یعنی یکی روی دیگری نوشته می‌شود؛ باید
        # دیده شود، نه اینکه بی‌صدا یک سند گم شود.
        seen_keys: dict[tuple, str] = {}
        collisions: list[str] = []

        for index, (rel_key, filename, folder, stem, write) in enumerate(jobs, start=1):
            entry = manifest.get(rel_key)
            if entry:
                title = entry['title']
                level = entry.get('level', 'other')
                approved = entry.get('approved_on', '')
            else:
                if manifest:
                    self.stdout.write(self.style.WARNING(
                        '  ! در manifest نبود، از نام فایل حدس زده شد: %s' % rel_key))
                title, approved = parse_name(stem)
                level = guess_level(folder, stem)

            if not title:
                skipped += 1
                continue

            key = (level, title, approved)
            if key in seen_keys:
                collisions.append('%s  ↔  %s' % (seen_keys[key], filename))
            seen_keys[key] = filename

            rel = 'curricula/%s/%s' % (level, filename)
            if not dry:
                target = dest_root / level / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                write(target)

                _, was_created = CurriculumDocument.objects.update_or_create(
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
