"""چهار شورای چارت سازمانی را ثبت می‌کند.

    python manage.py seed_councils
    python manage.py seed_councils --replace

چارت سازمانی موسسه چهار رکن مشورتی دارد — شورای موسسه زیر ریاست،
و شورای فرهنگی، شورای دانشجویی و کمیتهٔ انضباطی زیر معاونت
دانشجویی و فرهنگی. هیچ‌کدام تا امروز روی سایت نبودند.

نام اعضا اینجا نوشته نشده: اسم اشخاص واقعی است و باید از خود
موسسه بیاید، نه از حدس. صفحهٔ هر شورا تا آن موقع می‌گوید که هنوز
ثبت نشده.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import Council

COUNCILS = [
    {
        'slug': 'shoraye-moassese',
        'name': 'شورای موسسه',
        'order': 1,
        'icon': 'fa-landmark',
        'short_description': 'بالاترین رکن تصمیم‌گیری موسسه، زیر نظر ریاست.',
        'duties': '\n'.join([
            'تصویب سیاست‌های کلی آموزشی، پژوهشی و اداری موسسه',
            'بررسی و تصویب بودجهٔ سالانه',
            'تصویب آیین‌نامه‌های داخلی',
            'نظارت بر اجرای مصوبات هیات امنا',
        ]),
    },
    {
        'slug': 'shoraye-farhangi',
        'name': 'شورای فرهنگی',
        'order': 2,
        'icon': 'fa-masks-theater',
        'short_description':
            'برنامه‌ریزی فعالیت‌های فرهنگی و فوق‌برنامهٔ دانشجویان.',
        'duties': '\n'.join([
            'تدوین برنامهٔ سالانهٔ فعالیت‌های فرهنگی',
            'بررسی درخواست تشکل‌ها و کانون‌های دانشجویی',
            'نظارت بر برگزاری مراسم و همایش‌های فرهنگی',
        ]),
    },
    {
        'slug': 'shoraye-daneshjooyi',
        'name': 'شورای دانشجویی',
        'order': 3,
        'icon': 'fa-user-group',
        'short_description':
            'پیگیری مسائل صنفی و رفاهی دانشجویان و انتقال آن به مدیریت.',
        'duties': '\n'.join([
            'بررسی مسائل صنفی، رفاهی و خوابگاهی دانشجویان',
            'انتقال درخواست‌های دانشجویان به معاونت دانشجویی',
            'همکاری در برگزاری انتخابات تشکل‌های دانشجویی',
        ]),
    },
    {
        'slug': 'komite-enzebati',
        'name': 'کمیته انضباطی',
        'order': 4,
        'icon': 'fa-scale-balanced',
        'short_description':
            'رسیدگی به تخلفات آموزشی و انضباطی، بر پایهٔ آیین‌نامهٔ وزارت علوم.',
        'duties': '\n'.join([
            'رسیدگی به گزارش تخلفات آموزشی و انضباطی',
            'دعوت از دانشجو برای دفاع پیش از هر تصمیم',
            'صدور رأی در چارچوب آیین‌نامهٔ انضباطی وزارت علوم',
        ]),
    },
]


class Command(BaseCommand):
    help = 'ثبت شوراهای چارت سازمانی'

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
            council.save()
            updated += 1
            self.stdout.write('  ~ %s' % council.name)

        self.stdout.write(self.style.SUCCESS('انجام شد:'))
        self.stdout.write('  %d شورای تازه' % made)
        if updated:
            self.stdout.write('  %d بازنویسی شد' % updated)
        if not made and not updated:
            self.stdout.write('  چیزی برای تغییر نبود.')
        self.stdout.write('')
        self.stdout.write('نام اعضا ثبت نشده — از پنل ← شوراها واردشان کنید.')
