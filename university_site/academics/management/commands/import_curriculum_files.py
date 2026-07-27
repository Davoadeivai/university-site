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
    # نام‌های ASCII برای دیپلوی روی سرور (ZIP ویندوز)
    '1_master': ('master', 'master'),
    '2_bachelor_cont': ('bachelor_cont', 'bachelor_continuous'),
    '3_bachelor_disc': ('bachelor_disc', 'bachelor_discontinuous'),
    '4_associate_disc': ('associate_disc', 'associate'),
    '5_associate_tech': ('associate_cont', 'associate_tech'),
}

FOLDER_ALIAS = {
    '1_master': '1کارشناسی ارشد',
    '2_bachelor_cont': '2کارشناسی پیوسته',
    '3_bachelor_disc': '3کارشناسی ناپیوسته',
    '4_associate_disc': '4کاردانی ناپیوسته',
    '5_associate_tech': '5کاردانی فنی',
}

# نگاشت: (پوشه، نام‌پایه) → دستور
# id از لوکال فقط راهنماست؛ روی سرور با (degree, name_contains) مچ می‌شود.
MAPPINGS: dict[tuple[str, str], tuple] = {
    # —— کارشناسی ارشد ——
    ('1کارشناسی ارشد', 'آموزش و پرورش ابتدایی'): ('match', 'master', 'آموزش و پرورش ابتدایی'),
    ('1کارشناسی ارشد', 'حسابداری ورودی 1400 به بعد'): ('match', 'master', 'حسابداری - حسابداری'),
    ('1کارشناسی ارشد', 'حسابرسی جدید'): ('match', 'master', 'حسابرسی'),
    ('1کارشناسی ارشد', 'مدیریت آموزشی جدید'): ('match', 'master', 'مدیریت آموزشی'),
    ('1کارشناسی ارشد', 'مدیریت بازرگانی گرایش بازاریابی جدید'): ('match', 'master', 'بازاریابی'),
    ('1کارشناسی ارشد', 'مدیریت بازرگانی گرایش بازرگانی بین المللی'): ('match', 'master', 'بازرگانی بین'),
    ('1کارشناسی ارشد', 'مدیریت صنعتی گرایش تولید و عملیات'): ('match', 'master', 'تولید و عملیات'),
    ('1کارشناسی ارشد', 'مدیریت صنعتی گرایش مدیریت کیفیت و بهره و ری'): ('match', 'master', 'کیفیت و بهره'),
    # —— کارشناسی پیوسته ——
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته جامعه شناسی'): ('match', 'bachelor_cont', 'علوم اجتماعی'),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته حسابداری ورودی 1404 به بعد'): ('match', 'bachelor_cont', 'حسابداری'),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته حسابداری ورودی 96 به بعد'): ('doc_match', 'bachelor_cont', 'حسابداری'),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت بازرگانی'): (
        'create', 'bachelor_cont', 'مدیریت بازرگانی', 'گروه مدیریت بازرگانی',
    ),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت دولتی'): (
        'create', 'bachelor_cont', 'مدیریت دولتی', 'گروه مدیریت بازرگانی',
    ),
    ('2کارشناسی پیوسته', 'کارشناسی پیوسته مدیریت مالی'): ('match', 'bachelor_cont', 'مدیریت مالی'),
    ('2کارشناسی پیوسته', 'کارشناسی روانشناسی جدید'): ('match', 'bachelor_cont', 'روانشناسی'),
    ('2کارشناسی پیوسته', 'کارشناسی روانشناسی'): ('doc_match', 'bachelor_cont', 'روانشناسی'),
    ('2کارشناسی پیوسته', 'مهندسی برق جدید'): ('match', 'bachelor_cont', 'مهندسی برق'),
    ('2کارشناسی پیوسته', 'مهندسی کامپیوتر'): ('match', 'bachelor_cont', 'مهندسی کامپیوتر'),
    ('2کارشناسی پیوسته', 'مهندسی معماری ورودی 1401 به بعد'): ('match', 'bachelor_cont', 'مهندسی معماری'),
    # —— کارشناسی ناپیوسته ——
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته  کامپیوتر ورودی 1401 به بعد'): ('match', 'bachelor_disc', 'کامپیوتر'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته  معماری جدید'): ('match', 'bachelor_disc', 'معماری'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته برق'): ('match', 'bachelor_disc', 'برق'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته تکنولوژی مخابرات - گرایش انتقال'): ('match', 'bachelor_disc', 'مخابرات'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته حسابداری ورودی 1400 به بعد'): ('match', 'bachelor_disc', 'حسابداری'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت بازرگانی'): ('match', 'bachelor_disc', 'مدیریت بازرگانی'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت بیمه'): ('match', 'bachelor_disc', 'بیمه'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مدیریت صنعتی'): ('match', 'bachelor_disc', 'مدیریت صنعتی'),
    ('3کارشناسی ناپیوسته', 'کارشناسی ناپیوسته مکانیک خودرو'): ('match', 'bachelor_disc', 'مکانیک خودرو'),
    # —— کاردانی ناپیوسته ——
    ('4کاردانی ناپیوسته', 'کاردانی امور دولتی'): ('match', 'associate_disc', 'امور دولتی'),
    ('4کاردانی ناپیوسته', 'کاردانی مدیریت بازرگانی'): ('match', 'associate_disc', 'مدیریت بازرگانی'),
    ('4کاردانی ناپیوسته', 'کاردانی مدیریت صنعتی'): ('match', 'associate', 'مدیریت صنعتی'),
    ('4کاردانی ناپیوسته', 'کاردانی ناپیوسته حسابداری'): ('match', 'associate_disc', 'حسابداری'),
    # —— کاردانی فنی ——
    ('5کاردانی فنی', 'الکتروتکنیک- برق صنعتی'): ('match', 'associate_cont', 'برق صنعتی'),
    ('5کاردانی فنی', 'الکترونیک – الکترونیک عمومی'): ('match', 'associate_cont', 'الکترونیک عمومی'),
    ('5کاردانی فنی', 'حسابداری و بازرگانی ورودی 1401 به بعد'): ('match', 'associate_cont', 'حسابداری و بازرگانی'),
    ('5کاردانی فنی', 'کامپیوتر نرم افزار'): ('match', 'associate_cont', 'کامپیوتر'),
    ('5کاردانی فنی', 'گرافیک جدید ورودی 1401'): (
        'create', 'associate_cont', 'گرافیک', 'گروه معماری و نقشه کشی',
    ),
    ('5کاردانی فنی', 'مکانیک خودرو جدید ورودی 1401'): (
        'create', 'associate_cont', 'مکانیک خودرو', 'گروه مکانیک',
    ),
    ('5کاردانی فنی', 'نقشه برداری'): ('match', 'associate_cont', 'نقشه برداری'),
    ('5کاردانی فنی', 'نقشه کشی عمومی – نقشه کشی و طراحی صنعتی'): ('match', 'associate_cont', 'طراحی صنعتی'),
    ('5کاردانی فنی', 'نقشه کشی معماری جدید ورودی 1401'): ('match', 'associate_cont', 'معماری نقشه'),
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
        for root_name in ('کد رشته و تعداد واحد.docx', 'major_codes.docx'):
            root_doc = source / root_name
            if root_doc.is_file() and not dry:
                self._upsert_document(
                    title='کد رشته و تعداد واحد',
                    degree_level='general',
                    pdf=None,
                    word=root_doc,
                )
                break

        ok = skip = created = 0
        unmatched = []

        with transaction.atomic():
            for (folder, stem), files in sorted(bundles.items()):
                map_folder = FOLDER_ALIAS.get(folder, folder)
                mapping = None

                # همیشه اول sidecar .map را بخوان (برای دیپلوی ASCII)
                for kind in ('pdf', 'word'):
                    p = files.get(kind)
                    if not p:
                        continue
                    cand = Path(str(p)).with_suffix('.map')
                    if cand.exists():
                        raw = cand.read_text(encoding='utf-8', errors='ignore').splitlines()
                        if len(raw) >= 2:
                            try:
                                mapping = eval(raw[1], {'__builtins__': {}})  # noqa: S307
                            except Exception:
                                mapping = None
                        break

                if mapping is None:
                    m_id = re.match(r'^id_(\d+)$', stem)
                    if m_id:
                        mapping = ('id', int(m_id.group(1)))

                if mapping is None:
                    mapping = MAPPINGS.get((map_folder, stem))
                if mapping is None:
                    for (mf, ms), mv in MAPPINGS.items():
                        if mf == map_folder and _norm(ms) == stem:
                            mapping = mv
                            break
                if mapping is None:
                    unmatched.append(f'{folder}/{stem}')
                    continue

                degree_code, degree_level = FOLDER_DEGREE[folder]
                mode = mapping[0]

                def _find_major(degree: str, needle: str):
                    needle_n = _norm(needle)
                    qs = Major.objects.filter(degree=degree, is_active=True)
                    # exact then contains
                    for m in qs:
                        if _norm(m.name) == needle_n:
                            return m
                    for m in qs:
                        if needle_n in _norm(m.name):
                            return m
                    # also inactive
                    qs2 = Major.objects.filter(degree=degree)
                    for m in qs2:
                        if needle_n in _norm(m.name):
                            return m
                    return None

                if mode in ('doc_only', 'doc_match'):
                    if mode == 'doc_only':
                        major = Major.objects.filter(pk=mapping[1]).first()
                    else:
                        major = _find_major(mapping[1], mapping[2])
                    title = f'سرفصل {major.name} — آرشیو' if major else stem
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
                elif mode == 'match':
                    major = _find_major(mapping[1], mapping[2])
                    if not major:
                        self.stdout.write(self.style.ERROR(
                            f'رشته پیدا نشد: {mapping[1]} / {mapping[2]}'
                        ))
                        skip += 1
                        continue
                elif mode == 'create':
                    _, deg, name, group_name = mapping
                    major = Major.objects.filter(degree=deg, name=name).first()
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
