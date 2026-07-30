"""پرکردن «مزایای تحصیل» و «بخش‌های صفحه اصلی» با مقادیر فعلی قالب.

این دو بخش پیش از این در قالب هاردکد بودند. این دستور همان محتوا را به
دیتابیس منتقل می‌کند تا از پنل ادمین قابل ویرایش باشد — بدون اینکه ظاهر
سایت تغییری کند.

    python manage.py seed_home_sections
    python manage.py seed_home_sections --clear
"""
from django.core.management.base import BaseCommand
from django.db import transaction

FEATURES = [
    ('اساتید برجسته',      'هیئت علمی با سابقه پژوهشی و تجربه عملی در صنعت',
     'fa-graduation-cap', 'blue'),
    ('آزمایشگاه‌های مجهز',  'فضاهای پژوهشی پیشرفته برای یادگیری عملی',
     'fa-flask', 'green'),
    ('ارتباط با صنعت',      'شبکه همکاری برای کارآموزی و اشتغال فارغ‌التحصیلان',
     'fa-handshake', 'gold'),
    ('آموزش الکترونیکی',    'یادگیری آنلاین در هر زمان و مکان',
     'fa-laptop-code', 'violet'),
    ('کتابخانه دیجیتال',    'دسترسی به منابع علمی، مقالات و پایان‌نامه‌ها',
     'fa-book', 'red'),
    ('رتبه‌بندی معتبر',      'ارزیابی‌های سالانه علمی و آموزشی در سطح کشور',
     'fa-medal', 'amber'),
]

# (کلید, عنوان, زیرعنوان) — تصویر را ادمین خودش آپلود می‌کند
SECTIONS = [
    ('timeline',    'تقویم آموزشی',
     'روی هر مرحله بزنید تا به صفحهٔ مربوطه بروید'),
    ('features',    'مزایای تحصیل در موسسه آموزش عالی علامه امینی',
     'یک تجربه آموزشی کامل و آینده‌ساز'),
    ('quicklinks',  '', ''),
    ('news',        '', ''),
    ('departments', '', ''),
    ('faculty',     '', ''),
    ('events',      '', ''),
    ('gallery',     '', ''),
    ('alumni',      '', ''),
    ('faq',         '', ''),
    ('cta',         '', ''),
    ('stats',       '', ''),
]


class Command(BaseCommand):
    help = 'ثبت مزایای تحصیل و بخش‌های صفحه اصلی در دیتابیس'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='حذف رکوردهای قبلی پیش از ثبت')

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import HomeFeature, HomeSection

        if options['clear']:
            n1 = HomeFeature.objects.all().delete()[0]
            n2 = HomeSection.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(
                f'{n1} مزیت و {n2} بخش قبلی حذف شد.'))

        self.stdout.write(self.style.MIGRATE_HEADING('\nمزایای تحصیل'))
        c = u = 0
        for i, (title, desc, icon, tone) in enumerate(FEATURES, start=1):
            _, new = HomeFeature.objects.update_or_create(
                title=title,
                defaults={'description': desc, 'icon': icon, 'tone': tone,
                          'order': i, 'is_active': True},
            )
            c += new
            u += (not new)
            self.stdout.write(f'  {"+" if new else "~"} {title}')

        self.stdout.write(self.style.MIGRATE_HEADING('\nبخش‌های صفحه اصلی'))
        cs = us = 0
        for key, title, subtitle in SECTIONS:
            defaults = {'is_visible': True}
            # عنوان را فقط برای رکورد جدید بنویس تا ویرایش ادمین پاک نشود
            obj = HomeSection.objects.filter(key=key).first()
            if obj is None:
                HomeSection.objects.create(
                    key=key, title=title, subtitle=subtitle, **defaults)
                cs += 1
                self.stdout.write(f'  + {key}')
            else:
                us += 1
                self.stdout.write(f'  = {key} (دست‌نخورده)')

        self.stdout.write(self.style.SUCCESS(
            f'\nمزایا: {c} جدید، {u} به‌روز — بخش‌ها: {cs} جدید، {us} موجود.'))
        self.stdout.write(
            'حالا از پنل ← «مزایای تحصیل» و «بخش‌های صفحه اصلی» قابل ویرایش‌اند.\n'
            'برای هر بخش می‌توانید تصویر پس‌زمینه آپلود کنید.'
        )
