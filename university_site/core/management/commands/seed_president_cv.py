"""رزومهٔ رسمی رئیس موسسه را در پنل می‌نشاند.

    python manage.py seed_president_cv
    python manage.py seed_president_cv --replace

داده‌ها از فایل «CV-Dr Farsijani-1405» که موسسه فرستاده برداشته
شده‌اند. پیش‌فرض فقط جای خالی را پر می‌کند، پس اجرای دوباره در هر
دیپلوی چیزی را که ادمین ویرایش کرده بازنویسی نمی‌کند.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import PresidencyOffice

TITLE = 'استاد گروه مدیریت صنعتی و فناوری اطلاعات'

EDUCATION = [
    'فوق دکتری مدیریت صنعتی (استراتژی تکنولوژی تولید) — دانشگاه برادفورد انگلستان',
    'دکتری مدیریت صنعتی (مدیریت تولید و ساخت) — دانشگاه برادفورد انگلستان',
    'کارشناسی ارشد مدیریت صنعتی (تحقیق در عملیات) — دانشگاه تربیت مدرس',
    'کارشناسی مدیریت صنعتی — دانشگاه شهید بهشتی (رتبهٔ اول دوره)',
    'دوره‌های فوق تخصصی مدیریت و تولید در کلاس جهانی — روسیه، آلمان، انگلستان، دبی و چین',
]

RESUME = [
    'رئیس موسسه آموزش عالی علامه امینی',
    'رئیس دانشکده مدیریت و حسابداری دانشگاه شهید بهشتی',
    'مدیر گروه مدیریت صنعتی دانشگاه شهید بهشتی',
    'مدیر گروه MBA سازمان مدیریت صنعتی',
    'مدیر هستهٔ پژوهشی «تولید در کلاس جهانی» — دانشگاه شهید بهشتی',
    'رئیس مرکز مطالعات بین‌المللی مدیریت در کلاس جهانی تولیدات و سازمان‌ها',
    'مشاور مدیریت استراتژیک گروه صنعتی ایران‌خودرو',
    'مدیرعامل شرکت بین‌المللی بازرسی مهندسی و صنعتی ایران',
    'مشاور شرکت تویوتای انگلستان — دو سال، در دورهٔ فوق دکتری',
    'مشاور شرکت‌های نفتی وزارت نفت — سه سال',
]

RESEARCH = [
    'مدیریت در کلاس جهانی',
    'مدیریت زنجیره تأمین و عملیات',
    'مدیریت تولید و ساخت پیشرفته',
    'طراحی سیستم‌های پیشرفتهٔ تولید',
    'استراتژی تکنولوژی تولید',
]

BIO = (
    'نویسندهٔ ۳۱ جلد کتاب درسی دانشگاهی در رشتهٔ مدیریت صنعتی و بیش از '
    '۲۵۰ مقالهٔ علمی-پژوهشی و ISI، و استاد راهنمای ۲۲۰ دانشجوی دکتری و '
    'کارشناسی ارشد.\n\n'
    'مدیر مسئول و سردبیر مجله‌های علمی-پژوهشی چشم‌انداز مدیریت صنعتی، '
    'بازرگانی، مالی و حسابداری، دولتی، مطالعات مدیریت راهبردی و '
    'International Journal of Management Perspective.\n\n'
    'استاد نمونه و برگزیدهٔ دانشکده مدیریت و حسابداری دانشگاه شهید بهشتی '
    '(۱۳۸۶ تا ۱۴۰۰) و پژوهشگر برگزیدهٔ سال ۱۳۸۹.'
)

FIELDS = {
    'president_name': 'دکتر حسن فارسیجانی',
    'president_title': TITLE,
    'president_bio': BIO,
    'president_education': '\n'.join(EDUCATION),
    'president_resume': '\n'.join(RESUME),
    'president_research': '\n'.join(RESEARCH),
    'president_website': 'https://WCM-Society.Com',
    'president_website_label': '',
    'office_hours': 'شنبه تا پنج‌شنبه',
}


class Command(BaseCommand):
    help = 'ثبت رزومهٔ رسمی رئیس موسسه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace', action='store_true',
            help='مقدار فعلی را هم بازنویسی کن (پیش‌فرض: فقط جای خالی)')

    def handle(self, *args, **options):
        # سایت این رکورد را با .first() می‌خواند، پس همان یکی مبناست
        office = PresidencyOffice.objects.first() or PresidencyOffice()

        changed = []
        for field, value in FIELDS.items():
            # برچسب وب‌سایت عمداً خالی می‌شود: موسسه خواست «زنجیره
            # تأمین» از صفحه برداشته شود و خودِ نشانی دیده شود.
            if field == 'president_website_label':
                if options['replace'] and office.president_website_label:
                    office.president_website_label = ''
                    changed.append(field)
                continue
            current = (getattr(office, field, '') or '').strip()
            if current and not options['replace']:
                continue
            if current == value:
                continue
            setattr(office, field, value)
            changed.append(field)

        if not changed:
            self.stdout.write('چیزی برای تغییر نبود.')
            return

        if office.pk:
            office.save(update_fields=changed)
        else:
            office.save()
        self.stdout.write(self.style.SUCCESS(
            '%d فیلد ثبت شد: %s' % (len(changed), '، '.join(changed))))
