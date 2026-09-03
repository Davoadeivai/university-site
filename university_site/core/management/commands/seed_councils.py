"""شوراهای موسسه را با اعضایشان ثبت می‌کند.

    python manage.py seed_councils
    python manage.py seed_councils --replace

فهرست شوراها و نام اعضا از سند رسمی «اعضای شورا»ی موسسه برداشته
شده: هیات رئیسه، شورای دانشگاه، شورای آموزشی و تحصیلات تکمیلی،
شورای پژوهش و فناوری، و شورای دانشجویی و فرهنگی و اجتماعی.

شرح وظایف هر شورا اینجا نوشته شده چون در سند نیامده بود؛ متن
معمول همان شوراست و از پنل قابل ویرایش است.

شوراهایی که پیش‌تر ثبت شده بودند و در سند نیستند، با --replace
غیرفعال می‌شوند تا فهرست سایت با سند یکی بماند.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import Council

COUNCILS = [
    {
        'slug': 'hayat-raeise',
        'name': 'هیات رئیسه',
        'order': 1,
        'icon': 'fa-landmark',
        'head': 'دکتر حسن فارسیجانی',
        'short_description': 'بالاترین رکن اجرایی موسسه، زیر نظر ریاست.',
        'duties': '\n'.join([
            'هماهنگی میان حوزه‌های اجرایی موسسه',
            'بررسی و پیشنهاد سیاست‌های کلی به شورای دانشگاه',
            'پیگیری اجرای مصوبات هیات امنا و شورای دانشگاه',
            'تصمیم‌گیری دربارهٔ امور جاری آموزشی، اداری و مالی',
        ]),
        'members': '\n'.join([
            'دکتر حسن فارسیجانی',
            'دکتر علی اکبر جعفری',
            'دکتر محمدعلی جعفری',
            'مهندس حسن عمرانی',
            'دکتر شیرزاد کوپایی',
            'دکتر سیدمحمد سیدحسینی',
            'عباس اسدی امیری',
        ]),
    },
    {
        'slug': 'shoraye-daneshgah',
        'name': 'شورای دانشگاه',
        'order': 2,
        'icon': 'fa-building-columns',
        'head': 'دکتر حسن فارسیجانی',
        'short_description':
            'رکن سیاست‌گذار موسسه در امور آموزشی، پژوهشی و اداری.',
        'duties': '\n'.join([
            'تصویب سیاست‌های کلی آموزشی، پژوهشی و اداری موسسه',
            'بررسی و تصویب برنامه و بودجهٔ سالانه',
            'تصویب آیین‌نامه‌ها و دستورالعمل‌های داخلی',
            'نظارت بر اجرای مصوبات هیات امنا',
        ]),
        'members': '\n'.join([
            'دکتر حسن فارسیجانی',
            'دکتر محمدعلی جعفری',
            'دکتر علی اکبر جعفری',
            'مهندس حسن عمرانی',
            'دکتر شیرزاد کوپایی',
            'عباس اسدی امیری',
            'دکتر حسینعلی قربانی',
            'مهندس فاطمه نمازی',
        ]),
    },
    {
        'slug': 'shoraye-amoozeshi',
        'name': 'شورای آموزشی و تحصیلات تکمیلی',
        'order': 3,
        'icon': 'fa-graduation-cap',
        'head': 'دکتر محمدعلی جعفری',
        'short_description':
            'رسیدگی به امور آموزشی دوره‌های کارشناسی و تحصیلات تکمیلی.',
        'duties': '\n'.join([
            'بررسی و تصویب برنامه‌های درسی و سرفصل دوره‌ها',
            'رسیدگی به درخواست‌های آموزشی دانشجویان',
            'نظارت بر روند پایان‌نامه‌ها و دفاع تحصیلات تکمیلی',
            'بررسی مقررات آموزشی و پیشنهاد اصلاح آن',
        ]),
        'members': '\n'.join([
            'دکتر محمدعلی جعفری',
            'سید مجتبی اسماعیل نژاد',
            'مهندس حسن عمرانی',
            'دکتر جلال قنبری',
            'دکتر حسینعلی قربانی',
        ]),
    },
    {
        'slug': 'shoraye-pazhoohesh',
        'name': 'شورای پژوهش و فناوری',
        'order': 4,
        'icon': 'fa-flask',
        'head': 'مهندس حسن عمرانی',
        'short_description':
            'سیاست‌گذاری و پشتیبانی از فعالیت‌های پژوهشی و فناورانه.',
        'duties': '\n'.join([
            'بررسی و تصویب طرح‌های پژوهشی موسسه',
            'حمایت از انتشار مقاله و دستاوردهای علمی',
            'برنامه‌ریزی همایش‌ها و کارگاه‌های پژوهشی',
            'پیگیری ارتباط با صنعت و طرح‌های فناورانه',
        ]),
        'members': '\n'.join([
            'مهندس حسن عمرانی',
            'دکتر محمدعلی جعفری',
            'مهندس فاطمه نمازی',
            'دکتر جلال قنبری',
            'دکتر هانیه دلیران چمن زمین',
        ]),
    },
    {
        'slug': 'shoraye-daneshjooyi',
        'name': 'شورای دانشجویی و فرهنگی و اجتماعی',
        'order': 5,
        'icon': 'fa-user-group',
        'head': 'دکتر حسن فارسیجانی',
        'short_description':
            'برنامه‌ریزی امور دانشجویی، فرهنگی و اجتماعی موسسه.',
        'duties': '\n'.join([
            'تدوین برنامهٔ سالانهٔ فعالیت‌های فرهنگی و اجتماعی',
            'بررسی مسائل صنفی، رفاهی و خوابگاهی دانشجویان',
            'بررسی درخواست تشکل‌ها و کانون‌های دانشجویی',
            'نظارت بر برگزاری مراسم و همایش‌های دانشجویی',
        ]),
        'members': '\n'.join([
            'دکتر حسن فارسیجانی',
            'دکتر شیرزاد کوپایی',
            'عباس اسدی امیری',
            'علیرضا فرهادپور',
            'حسن غلامی',
            'دکتر محمدعلی جعفری',
            'مهندس حسن عمرانی',
            'دکتر کامبیز یزدانی',
        ]),
    },
]


class Command(BaseCommand):
    help = 'ثبت شوراهای موسسه و اعضای آن‌ها'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace', action='store_true',
            help='متن شوراهای موجود را هم بازنویسی کن')

    def handle(self, *args, **options):
        made = updated = 0
        for row in COUNCILS:
            council, created = Council.objects.get_or_create(
                slug=row['slug'],
                defaults={**row, 'is_active': True})
            if created:
                made += 1
                self.stdout.write('  + %s' % council.name)
                continue
            if not options['replace']:
                continue
            # متنی که مدیر دست‌کاری کرده، جز با --replace دست نمی‌خورد
            for field, value in row.items():
                setattr(council, field, value)
            council.is_active = True
            council.save()
            updated += 1
            self.stdout.write('  ~ %s' % council.name)

        retired = 0
        if options['replace']:
            slugs = [row['slug'] for row in COUNCILS]
            stale = Council.objects.filter(is_active=True).exclude(
                slug__in=slugs)
            for council in stale:
                council.is_active = False
                council.save(update_fields=['is_active'])
                retired += 1
                self.stdout.write('  - %s (غیرفعال شد)' % council.name)

        self.stdout.write(self.style.SUCCESS('انجام شد:'))
        self.stdout.write('  %d شورای تازه' % made)
        if updated:
            self.stdout.write('  %d بازنویسی شد' % updated)
        if retired:
            self.stdout.write('  %d شورای خارج از سند غیرفعال شد' % retired)
        if not made and not updated and not retired:
            self.stdout.write('  چیزی برای تغییر نبود.')
