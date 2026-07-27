"""
واردسازی سرفصل PDF/Word از پوشه دانشگاه به رشته‌ها و بخش آیین‌نامه‌ها.

مثال:
  python manage.py import_curriculum_files
  python manage.py import_curriculum_files --source "C:\\path\\to\\دانشگاه"
"""
from __future__ import annotations

import re
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from academics.models import AcademicGroup, Department, Major
from core.models import DownloadableDocument

# پوشه → (کد مقطع Major، کد پوشه DownloadableDocument)
FOLDER_DEGREE = {
    '1کارشناسی ارشد': ('master', 'master'),
    '2کارشناسی پیوسته': ('bachelor_cont', 'bachelor_continuous'),
    '3کارشناسی ناپیوسته': ('bachelor_disc', 'bachelor_discontinuous'),
    '4کاردانی ناپیوسته': ('associate_disc', 'associate'),
    '5کاردانی فنی': ('associate_cont', 'associate_tech'),
}

# نگاشت صریح: (پوشه، نام‌پایه بدون پسوند) → کلید رشته یا create
# کلید: ('match', degree, name_contains...) یا ('id', major_id) یا ('create', degree, name, group_name)
MAPPINGS: dict[tuple[str, str], tuple] = {
    # —— کارشناسی ارشد ——
    ('1کارشناسی ارشد', 'آموزش و پرورش ابتدایی'): ('id', 51),
    ('1کارشناسی ارشد', 'حسابداری ورودی 1400 به بعد'): ('id', 20),
    ('1کارشناسی ارشد', 'حسابرسی جدید'): ('id', 21),
    ('1کارشناسی ارشد', 'مدیریت آموزشی جدید'): ('id', 50),
    ('1کارشناسی ارشد', 'مدیریت بازرگانی گرایش بازاریابی جدید'): ('id', 40),
    ('1کارشناسی ارشد', 'مدیریت بازرگانی گرایش بازرگانی بین المللی'): ('id', 41),
    ('1کارشناسی ارشد', 'مدیریت صنعتی گرایش تولید و عملیات'): ('id', 27),
    ('1کارشناسی ارشد', 'مدیریت صنعتی گرایش مدیریت کیفیت و بهره و ری'): ('id', 26),
    # —— کارشناسی پیوسته ——
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته جامعه شناسی'): ('id', 46),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته حسابداری ورودی 1404 به بعد'): ('id', 22),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته حسابداری ورودی 96 به بعد'): ('doc_only', 22),  # نسخه قدیمی فقط در پوشه اسناد
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت بازرگانی'): (
        'create', 'bachelor_cont', 'مدیریت بازرگانی', 'گروه مدیریت بازرگانی',
    ),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت دولتی'): (
        'create', 'bachelor_cont', 'مدیریت دولتی', 'گروه مدیریت بازرگانی',
    ),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت مالی'): ('id', 29),
    ('2کارشناسی پیوسته', 'کارشناسی روانشناسی جدید'): ('id', 47),
    ('2کارشناسی پیوسته', 'کارشناسی روانشناسی'): ('doc_only', 47),
    ('2کارشناسی پیوسته', 'مهندسی برق جدید'): ('id', 31),
    ('2کارشناسی پیوسته', 'مهندسی کامپیوتر'): ('id', 15),
    ('2کارشناسی پیوسته', 'مهندسی معماری ورودی 1401 به بعد'): ('id', 10),
    # —— کارشناسی ناپیوسته ——
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته  کامپیوتر ورودی 1401 به بعد'): ('id', 16),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته  معماری جدید'): ('id', 11),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته برق'): ('id', 32),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته تکنولوژی مخابرات - گرایش انتقال'): ('id', 33),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته حسابداری ورودی 1400 به بعد'): ('id', 23),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت بازرگانی'): ('id', 42),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت بیمه'): ('id', 43),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت صنعتی'): ('id', 28),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مکانیک خودرو'): ('id', 18),
    # —— کاردانی ناپیوسته ——
    ('4کاردانی ناپیوسته', 'کاردانی امور دولتی'): ('id', 45),
    ('4کاردانی ناپیوسته', 'کاردانی مدیریت بازرگانی'): ('id', 44),
    ('4کاردانی ناپیوسته', 'کاردانی مدیریت صنعتی'): ('id', 30),
    ('4کاردانی ناپیوسته', 'کاردانی ناپیوسته حسابداری'): ('id', 24),
    # —— کاردانی فنی ——
    ('5کاردانی فنی', 'الکتروتکنیک- برق صنعتی'): ('id', 35),
    ('5کاردانی فنی', 'الکترونیک – الکترونیک عمومی'): ('id', 36),
    ('5کاردانی فنی', 'حسابداری و بازرگانی ورودی 1401 به بعد'): ('id', 25),
    ('5کاردانی فنی', 'کامپیوتر نرم افزار'): ('id', 17),
    ('5کاردانی فنی', 'گرافیک جدید ورودی 1401'): (
        'create', 'associate_cont', 'گرافیک', 'گروه معماری و نقشه کشی',
    ),
    ('5کاردانی فنی', 'مکانیک خودرو جدید ورودی 1401'): (
        'create', 'associate_cont', 'مکانیک خودرو', 'گروه مکانیک',
    ),
    ('5کاردانی فنی', 'نقشه برداری'): ('id', 13),
    ('5کاردانی فنی', 'نقشه کشی عمومی – نقشه کشی و طراحی صنعتی'): ('id', 14),
    ('5کاردانی فنی', 'نقشه کشی معماری جدید ورودی 1401'): ('id', 12),
}


def _norm(s: str) -> str:
    s = (s or '').replace('\u200c', '').replace('\u200f', '').replace('\u200e', '')
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('ـ', '')
    s = s.replace('–', '-').replace('—', '-').replace('−', '-')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _stem_key(path: Path) -> str:
    return _norm(path.stem)


class Command(BaseCommand):
    help = 'واردسازی سرفصل‌های PDF/Word به رشته‌ها و پوشه‌های آیین‌نامه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            default=r'C:\Users\Part Laptop\Desktop\windows work\دانشگاه',
            help='مسیر پوشه حاوی فایل‌های سرفصل',
        )
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        source = Path(options['source'])
        dry = options['dry_run']
        if not source.is_dir():
            raise CommandError(f'پوشه پیدا نشد: {source}')

        dept = Department.objects.order_by('id').first()
        if not dept:
            raise CommandError('هیچ دانشکده‌ای در دیتابیس نیست.')

        # جمع‌آوری جفت‌های pdf/docx بر اساس (پوشه، stem)
        bundles: dict[tuple[str, str], dict[str, Path]] = {}
        for folder_name, _ in FOLDER_DEGREE.items():
            folder = source / folder_name
            if not folder.is_dir():
                self.stdout.write(self.style.WARNING(f'پوشه نیست: {folder_name}'))
                continue
            for f in folder.iterdir():
                if not f.is_file():
                    continue
                ext = f.suffix.lower()
                if ext not in {'.pdf', '.doc', '.docx'}:
                    continue
                key = (folder_name, _stem_key(f))
                bundles.setdefault(key, {})
                if ext == '.pdf':
                    bundles[key]['pdf'] = f
                else:
                    bundles[key]['word'] = f

        # فایل عمومی ریشه
        root_doc = source / 'کد رشته و تعداد واحد.docx'
        if root_doc.is_file() and not dry:
            self._upsert_document(
                title='کد رشته و تعداد واحد',
                degree_level='general',
                pdf=None,
                word=root_doc,
            )

        ok = skip = created = 0
        unmatched = []

        with transaction.atomic():
            for (folder, stem), files in sorted(bundles.items()):
                mapping = MAPPINGS.get((folder, stem))
                # تلاش با نرمال‌سازی کلیدها اگر مستقیم نبود
                if mapping is None:
                    for (mf, ms), mv in MAPPINGS.items():
                        if mf == folder and _norm(ms) == stem:
                            mapping = mv
                            break
                if mapping is None:
                    unmatched.append(f'{folder}/{stem}')
                    continue

                degree_code, degree_level = FOLDER_DEGREE[folder]
                mode = mapping[0]

                if mode == 'doc_only':
                    major = Major.objects.filter(pk=mapping[1]).first()
                    title = stem
                    if major:
                        title = f'سرفصل {major.name} — {stem}'
                    if not dry:
                        self._upsert_document(
                            title=title,
                            degree_level=degree_level,
                            pdf=files.get('pdf'),
                            word=files.get('word'),
                        )
                    ok += 1
                    continue

                if mode == 'id':
                    major = Major.objects.filter(pk=mapping[1]).first()
                    if not major:
                        self.stdout.write(self.style.ERROR(f'Major id={mapping[1]} نیست'))
                        skip += 1
                        continue
                elif mode == 'create':
                    _, deg, name, group_name = mapping
                    major = Major.objects.filter(degree=deg, name=name, is_active=True).first()
                    if not major:
                        group = AcademicGroup.objects.filter(name=group_name).first()
                        if dry:
                            self.stdout.write(f'CREATE {deg} / {name}')
                            major = None
                        else:
                            major = Major(
                                department=dept,
                                group=group,
                                name=name,
                                degree=deg,
                                is_active=True,
                            )
                            major.save()
                            created += 1
                            self.stdout.write(self.style.SUCCESS(f'رشته جدید: {major}'))
                    degree_code = deg
                else:
                    skip += 1
                    continue

                if dry:
                    self.stdout.write(f'OK {folder}/{stem} → {major}')
                    ok += 1
                    continue

                if major is None:
                    skip += 1
                    continue

                # اتصال به Major
                if files.get('pdf'):
                    with open(files['pdf'], 'rb') as fh:
                        major.curriculum_pdf.save(files['pdf'].name, File(fh), save=False)
                if files.get('word'):
                    with open(files['word'], 'rb') as fh:
                        major.curriculum_word.save(files['word'].name, File(fh), save=False)
                major.save()

                # کپی در پوشه آیین‌نامه/فرم‌ها بر اساس مقطع
                self._upsert_document(
                    title=f'سرفصل {major.name}',
                    degree_level=FOLDER_DEGREE[folder][1],
                    pdf=files.get('pdf'),
                    word=files.get('word'),
                    order=major.order,
                )
                ok += 1
                self.stdout.write(f'✓ {major.get_degree_display()} | {major.name}')

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'انجام شد: {ok} — رشته جدید: {created} — ردشده: {skip}'
        ))
        if unmatched:
            self.stdout.write(self.style.WARNING('بدون نگاشت:'))
            for u in unmatched:
                self.stdout.write(f'  - {u}')

    def _upsert_document(self, title, degree_level, pdf, word, order=0):
        doc, _ = DownloadableDocument.objects.get_or_create(
            title=title,
            degree_level=degree_level,
            defaults={
                'category': 'guide',
                'section': 'graduate' if degree_level == 'master' else '',
                'is_active': True,
                'order': order,
                'description': 'سرفصل / برنامه درسی',
            },
        )
        if pdf:
            with open(pdf, 'rb') as fh:
                doc.file.save(pdf.name, File(fh), save=False)
        if word:
            with open(word, 'rb') as fh:
                doc.word_file.save(word.name, File(fh), save=False)
        doc.category = 'guide'
        doc.is_active = True
        doc.save()
