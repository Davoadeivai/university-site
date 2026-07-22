"""
هم‌سان‌سازی تحصیلات تکمیلی و دفتر ریاست با سایت رسمی aab.ac.ir
Run: python manage.py sync_official_graduate_presidency
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from academics.models import AcademicGroup, Department, Major
from core.models import (
    DownloadableDocument,
    GraduateStudiesInfo,
    PresidencyOffice,
    PresidencyOfficeUnit,
)

OFFICE_DUTIES = (
    'تنظیم برنامه‌های مربوط به جلسات، ملاقات‌ها، کنفرانس‌ها، مسافرت‌ها، '
    'کنفرانس‌ها و بازدیدهای داخلی و خارجی رئیس دانشگاه و تهیه گزارش‌های لازم؛\n'
    'دریافت و ثبت مکاتبات و دعوت‌نامه‌ها با عنوان رئیس دانشگاه و ارائه آن برای '
    'صدور دستور و ارسال آن‌ها برای مسئولان ذیربط؛\n'
    'پیگیری لازم در خصوص تهیه و تنظیم اطلاعات، گزارش‌ها و تحلیل‌های لازم در '
    'رابطه با موضوعات و دستور جلسات رئیس دانشگاه از طریق معاونت‌ها، دانشکده‌ها '
    'و واحدهای ذیربط؛\n'
    'ابلاغ دستور جلسات، صورت جلسات، یادداشت‌ها و دستورات رئیس دانشگاه به '
    'مسئولان و واحدهای ذیربط و پیگیری تا حصول نتیجه و ارائه گزارش نتیجه '
    'اقدامات انجام شده؛'
)

OFFICE_UNITS = [
    {
        'slug': 'modir-daftar',
        'title': 'مدیر دفتر ریاست',
        'content': 'مدیر دفتر ریاست : ماریا چاری',
        'order': 1,
    },
    {
        'slug': 'dabirkhane-heyat-raise',
        'title': 'دبیرخانه هیأت رئیسه',
        'content': 'دبیرخانه هیأت رئیسه موسسه آموزش عالی علامه امینی بهنمیر.',
        'order': 2,
    },
    {
        'slug': 'dabirkhane-heyat-omana',
        'title': 'دبیرخانه هیأت امناء',
        'content': 'دبیرخانه هیأت امناء موسسه آموزش عالی علامه امینی بهنمیر.',
        'order': 3,
    },
    {
        'slug': 'dabirkhane-jazb',
        'title': 'دبیرخانه هیأت اجرایی جذب هیأت علمی',
        'content': 'دبیرخانه هیأت اجرایی جذب هیأت علمی موسسه آموزش عالی علامه امینی بهنمیر.',
        'order': 4,
    },
]

# (name, group_slug)
MASTER_MAJORS = [
    ('حسابداری - حسابداری', 'گروه-حسابداری'),
    ('حسابداری - گرایش حسابرسی', 'گروه-حسابداری'),
    ('مدیریت بازرگانی - گرایش بازاریابی', 'گروه-مدیریت-بازرگانی'),
    ('مدیریت بازرگانی - گرایش بازرگانی بین الملل', 'گروه-مدیریت-بازرگانی'),
    ('مدیریت بازرگانی - گرایش مدیریت مالی', 'گروه-مدیریت-بازرگانی'),
    ('مدیریت صنعتی - گرایش مدیریت کیفیت و بهره وری', 'گروه-مدیریت-صنعتی-و-مالی'),
    ('مدیریت صنعتی - تولید و عملیات', 'گروه-مدیریت-صنعتی-و-مالی'),
    ('علوم تربیتی - مدیریت آموزشی', 'گروه-علوم-تربیتی-مدیریت-آموزشی'),
    ('آموزش و پرورش ابتدایی', 'گروه-علوم-تربیتی-مدیریت-آموزشی'),
]

GRADUATE_DOCS = [
    {
        'title': 'آیین نامه نحوه نگارش و تدوین پایان نامه',
        'category': 'regulation',
        'order': 1,
    },
    {'title': 'فرم صفر (پیشنهاد موضوع پایان نامه)', 'category': 'form', 'order': 2},
    {'title': 'فرم شماره 1 (فرم پروپوزال)', 'category': 'form', 'order': 3},
    {'title': 'فرم شماره 2 (گزارش پیشرفت کار 3 ماهه)', 'category': 'form', 'order': 4},
    {'title': 'فرم شماره 3 (فرم اعلام آمادگی برای دفاع از پایان نامه)', 'category': 'form', 'order': 5},
    {'title': 'فرم شماره 4 (تعیین تاریخ و ساعت برگزاری جلسه دفاع)', 'category': 'form', 'order': 6},
    {'title': 'فرم شماره 5 (تاییدیه تصحیح اشکالات اشاره شده در جلسه دفاع)', 'category': 'form', 'order': 7},
    {'title': 'فرم شماره 6 (فرم تحویل نسخه‌های پایان‌نامه دانشجویان کارشناسی ارشد)', 'category': 'form', 'order': 8},
    {'title': 'فرم 7 (تعهد نامه اصالت پایان نامه)', 'category': 'form', 'order': 9},
    {'title': 'فرم شماره 8 (تمدید پایان نامه)', 'category': 'form', 'order': 10},
    {'title': 'فرم شماره ۹ (فرم انصراف از مقاله)', 'category': 'form', 'order': 11},
    {'title': 'فرم شماره 10 (فرم شرکت در جلسات دفاع)', 'category': 'form', 'order': 12},
    {'title': 'فرمت چینش صفحات پایان نامه', 'category': 'guide', 'order': 13},
    {'title': 'فرمت اطلاعیه جلسه دفاع از پایان نامه کارشناسی ارشد', 'category': 'guide', 'order': 14},
]


def _norm(name: str) -> str:
    import re
    s = (
        name.replace('\u200c', '')
        .replace('\u200d', '')
        .replace('‌', '')
        .replace('ي', 'ی')
        .replace('ك', 'ک')
    )
    return re.sub(r'\s+', '', s).strip()


class Command(BaseCommand):
    help = 'Sync graduate studies + presidency office with official aab.ac.ir'

    def handle(self, *args, **options):
        office, _ = PresidencyOffice.objects.get_or_create(pk=1)
        office.office_manager_name = 'ماریا چاری'
        office.office_duties = OFFICE_DUTIES
        office.save()
        self.stdout.write(self.style.SUCCESS('PresidencyOffice duties/manager updated'))

        for spec in OFFICE_UNITS:
            obj, created = PresidencyOfficeUnit.objects.update_or_create(
                slug=spec['slug'],
                defaults={
                    'title': spec['title'],
                    'content': spec['content'],
                    'order': spec['order'],
                    'is_active': True,
                },
            )
            self.stdout.write(f"  unit {'created' if created else 'updated'}: {obj.title}")

        info, _ = GraduateStudiesInfo.objects.get_or_create(pk=1)
        info.manager_name = 'خانم ماریا چاری'
        if not info.intro:
            info.intro = 'مدیریت تحصیلات تکمیلی موسسه آموزش عالی علامه امینی بهنمیر.'
        info.save()
        self.stdout.write(self.style.SUCCESS('GraduateStudiesInfo manager updated'))

        dept = Department.objects.filter(name__icontains='تکمیلی').first()
        if not dept:
            dept = Department.objects.first()
        if not dept:
            self.stdout.write(self.style.WARNING('No Department found; skipping majors'))
        else:
            keep_slugs = set()
            for order, (name, group_slug) in enumerate(MASTER_MAJORS, start=1):
                group = AcademicGroup.objects.filter(slug=group_slug).first()
                existing = None
                for m in Major.objects.filter(degree='master', is_active=True):
                    if _norm(m.name) == _norm(name):
                        if group and m.group_id == group.id:
                            existing = m
                            break
                        if existing is None:
                            existing = m
                if existing:
                    existing.name = name
                    existing.group = group
                    existing.department = dept
                    existing.order = order
                    existing.is_active = True
                    existing.save()
                    keep_slugs.add(existing.slug)
                    # سایر رکوردهای هم‌نام را غیرفعال کن
                    for dup in Major.objects.filter(degree='master', is_active=True).exclude(pk=existing.pk):
                        if _norm(dup.name) == _norm(name):
                            dup.is_active = False
                            dup.save(update_fields=['is_active'])
                            self.stdout.write(f'  major deactivated duplicate: {dup.slug}')
                    self.stdout.write(f'  major updated: {name}')
                else:
                    base = slugify(name, allow_unicode=True)[:40] or f'master-{order}'
                    slug = base
                    i = 1
                    while Major.objects.filter(slug=slug).exists():
                        slug = f'{base}-{i}'
                        i += 1
                    Major.objects.create(
                        name=name,
                        slug=slug,
                        department=dept,
                        group=group,
                        degree='master',
                        order=order,
                        is_active=True,
                    )
                    keep_slugs.add(slug)
                    self.stdout.write(f'  major created: {name}')

            # غیرفعال‌سازی تکراری‌های هم‌نام بدون گروه ترجیحی
            for m in Major.objects.filter(degree='master', is_active=True):
                if m.slug in keep_slugs:
                    continue
                for kept_name, _ in MASTER_MAJORS:
                    if _norm(m.name) == _norm(kept_name):
                        m.is_active = False
                        m.save(update_fields=['is_active'])
                        self.stdout.write(f'  major deactivated duplicate: {m.slug}')
                        break

        for spec in GRADUATE_DOCS:
            DownloadableDocument.objects.update_or_create(
                title=spec['title'],
                section='graduate',
                defaults={
                    'category': spec['category'],
                    'order': spec['order'],
                    'is_active': True,
                    'description': 'مربوط به تحصیلات تکمیلی (مطابق سایت رسمی)',
                },
            )
        self.stdout.write(self.style.SUCCESS(
            f'Graduate documents synced ({len(GRADUATE_DOCS)})'
        ))
