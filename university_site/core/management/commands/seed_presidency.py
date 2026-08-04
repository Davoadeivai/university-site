"""پرکردن نمونهٔ بخش «حوزه ریاست» تا صفحه‌ها خالی نمانند.

چرا نمونه و نه داده واقعی
─────────────────────────
نام و سمت افراد، دادهٔ هویتی موسسه است و حدس‌زدنش اشتباه است. پس هرجا
نام شخص لازم بوده، جای‌نگهدار «[…]» گذاشته شده تا در پنل ادمین با نام
واقعی جایگزین شود. بقیهٔ متن‌ها — شرح وظایف، ساعات مراجعه، ساختار —
از عرف اداری دانشگاه‌ها گرفته شده و قابل استفاده‌اند.

    python manage.py seed_presidency            # فقط جاهای خالی را پر می‌کند
    python manage.py seed_presidency --replace  # همه را بازنویسی می‌کند
"""
from django.core.management.base import BaseCommand
from django.db import transaction

PLACEHOLDER = '[نام را از پنل ادمین وارد کنید]'

OFFICE = {
    'president_name': PLACEHOLDER,
    'president_title': 'دانشیار — دکترای مدیریت',
    'president_message': (
        'دانشگاه، خانهٔ اندیشه و کارگاه ساختن آینده است. در موسسه آموزش عالی '
        'علامه امینی بر این باوریم که آموزش وقتی معنا دارد که به مهارت، و مهارت '
        'وقتی ارزش دارد که به مسئولیت اجتماعی برسد. درِ این دفتر به روی همهٔ '
        'دانشجویان، استادان و همکاران باز است؛ پیشنهادها و انتقادهای شما '
        'سرمایهٔ ما برای بهتر شدن است.'
    ),
    'president_bio': (
        'عضو هیئت علمی موسسه با سابقهٔ تدریس و پژوهش در حوزهٔ مدیریت آموزش عالی. '
        'این متن نمونه است؛ از پنل ادمین با شرح حال واقعی جایگزین شود.'
    ),
    'president_education': (
        'دکترای تخصصی — دانشگاه [نام دانشگاه]\n'
        'کارشناسی ارشد — دانشگاه [نام دانشگاه]\n'
        'کارشناسی — دانشگاه [نام دانشگاه]'
    ),
    'president_resume': (
        'ریاست موسسه آموزش عالی علامه امینی — از [سال]\n'
        'معاونت آموزشی — [بازهٔ زمانی]\n'
        'مدیر گروه آموزشی — [بازهٔ زمانی]\n'
        'عضو شورای پژوهشی — [بازهٔ زمانی]'
    ),
    'president_email': 'president@aab.ac.ir',
    'president_phone': '۰۱۱-۳۵۷۵۰۸۱۰',
    'office_manager_name': PLACEHOLDER,
    'office_duties': (
        'دفتر ریاست، مرکز هماهنگی میان ریاست موسسه و همهٔ واحدهای اداری و '
        'آموزشی است. تنظیم برنامهٔ ملاقات‌ها، پیگیری مصوبات هیئت رئیسه، '
        'مکاتبات رسمی و ارتباط با نهادهای بیرونی بر عهدهٔ این دفتر است.'
    ),
    'office_address': 'ساختمان مرکزی، طبقهٔ دوم، دفتر ریاست',
    'office_phone': '۰۱۱-۳۵۷۵۰۸۱۰ داخلی ۱۰۱',
    'office_email': 'office@aab.ac.ir',
    'office_hours': 'شنبه تا چهارشنبه، ۸ تا ۱۵',
}

UNITS = [
    {
        'slug': 'modir-daftar',
        'title': 'مدیر دفتر ریاست',
        'icon': 'fa-user-tie',
        'manager_title': 'مدیر دفتر ریاست',
        'extension': '۱۰۱',
        'location': 'ساختمان مرکزی، طبقهٔ دوم، اتاق ۲۰۱',
        'office_hours': 'شنبه تا چهارشنبه، ۸ تا ۱۵',
        'email': 'office@aab.ac.ir',
        'content': (
            'مدیر دفتر ریاست، نخستین نقطهٔ تماس با حوزهٔ ریاست است و هماهنگی '
            'میان ریاست موسسه، معاونت‌ها و مراجعان بیرونی را بر عهده دارد.'
        ),
        'duties': (
            'تنظیم و هماهنگی برنامهٔ ملاقات‌ها و جلسات ریاست\n'
            'دریافت، ثبت و ارجاع مکاتبات رسمی حوزهٔ ریاست\n'
            'پیگیری دستورها و مصوبات تا حصول نتیجه\n'
            'هماهنگی سفرها، بازدیدها و مراسم رسمی موسسه\n'
            'راهنمایی مراجعان و پاسخ‌گویی تلفنی حوزهٔ ریاست'
        ),
    },
    {
        'slug': 'dabirkhane-heyat-raise',
        'title': 'دبیرخانه هیأت رئیسه',
        'icon': 'fa-users',
        'manager_title': 'دبیر هیئت رئیسه',
        'extension': '۱۰۲',
        'location': 'ساختمان مرکزی، طبقهٔ دوم، اتاق ۲۰۳',
        'office_hours': 'شنبه تا چهارشنبه، ۸ تا ۱۵',
        'content': (
            'هیئت رئیسه بالاترین شورای اجرایی موسسه است و از رئیس و معاونان '
            'تشکیل می‌شود. این دبیرخانه جلسات را تدارک می‌بیند و مصوبات را '
            'تا اجرا پیگیری می‌کند.'
        ),
        'duties': (
            'تنظیم دستور جلسه و دعوت از اعضا\n'
            'تهیهٔ صورت‌جلسه و ابلاغ مصوبات به واحدها\n'
            'پیگیری اجرای مصوبات و گزارش وضعیت به ریاست\n'
            'نگهداری و بایگانی سوابق جلسات\n'
            'هماهنگی میان معاونت‌ها برای موضوعات مشترک'
        ),
    },
    {
        'slug': 'dabirkhane-heyat-omana',
        'title': 'دبیرخانه هیأت امناء',
        'icon': 'fa-landmark',
        'manager_title': 'دبیر هیئت امنا',
        'extension': '۱۰۳',
        'location': 'ساختمان مرکزی، طبقهٔ دوم، اتاق ۲۰۵',
        'office_hours': 'شنبه تا چهارشنبه، ۸ تا ۱۵',
        'content': (
            'هیئت امنا عالی‌ترین رکن سیاست‌گذاری موسسه است و بودجه، تشکیلات '
            'و آیین‌نامه‌های کلان در آن تصویب می‌شود. این دبیرخانه ارتباط '
            'موسسه با هیئت امنا و وزارت علوم را برقرار می‌کند.'
        ),
        'duties': (
            'تدارک جلسات هیئت امنا و تنظیم دستور کار\n'
            'تهیهٔ گزارش‌های مورد نیاز اعضا\n'
            'ابلاغ و پیگیری مصوبات هیئت امنا\n'
            'مکاتبه با وزارت علوم، تحقیقات و فناوری\n'
            'نگهداری اسناد و سوابق مصوبات'
        ),
    },
    {
        'slug': 'dabirkhane-jazb',
        'title': 'دبیرخانه هیأت اجرایی جذب هیأت علمی',
        'icon': 'fa-user-graduate',
        'manager_title': 'دبیر هیئت اجرایی جذب',
        'extension': '۱۰۴',
        'location': 'ساختمان مرکزی، طبقهٔ دوم، اتاق ۲۰۷',
        'office_hours': 'شنبه تا چهارشنبه، ۹ تا ۱۴',
        'email': 'jazb@aab.ac.ir',
        'content': (
            'فراخوان، بررسی و تأیید صلاحیت متقاضیان عضویت در هیئت علمی از '
            'طریق این دبیرخانه انجام می‌شود. متقاضیان می‌توانند برای آگاهی '
            'از فراخوان‌ها و مراحل پرونده به این واحد مراجعه کنند.'
        ),
        'duties': (
            'انتشار فراخوان جذب هیئت علمی و دریافت درخواست‌ها\n'
            'تشکیل پرونده و بررسی مدارک علمی متقاضیان\n'
            'هماهنگی جلسات هیئت اجرایی جذب\n'
            'پیگیری استعلام‌ها و مراحل تأیید صلاحیت\n'
            'اعلام نتیجه و راهنمایی متقاضیان'
        ),
    },
]


class Command(BaseCommand):
    help = 'پرکردن نمونهٔ بخش حوزه ریاست (رئیس، دفتر و واحدها)'

    def add_arguments(self, parser):
        parser.add_argument('--replace', action='store_true',
                            help='مقادیر موجود را هم بازنویسی کن')

    @transaction.atomic
    def handle(self, *args, **options):
        from core.models import PresidencyOffice, PresidencyOfficeUnit

        replace = options['replace']

        office, _created = PresidencyOffice.objects.get_or_create(pk=1)
        filled = []
        for field, value in OFFICE.items():
            current = (getattr(office, field, '') or '').strip()
            if current and not replace:
                continue
            setattr(office, field, value)
            filled.append(field)
        if filled:
            office.save()
        self.stdout.write(self.style.MIGRATE_HEADING('\nدفتر ریاست'))
        self.stdout.write('  %d فیلد پر شد%s' % (
            len(filled), '' if filled else ' (همه از قبل پر بودند)'))

        self.stdout.write(self.style.MIGRATE_HEADING('\nواحدهای دفتر ریاست'))
        created = updated = 0
        for spec in UNITS:
            spec = dict(spec)
            slug = spec.pop('slug')
            unit, is_new = PresidencyOfficeUnit.objects.get_or_create(
                slug=slug, defaults={'title': spec.get('title', slug)})

            touched = []
            for field, value in spec.items():
                current = (getattr(unit, field, '') or '')
                if isinstance(current, str) and current.strip() and not replace:
                    continue
                setattr(unit, field, value)
                touched.append(field)

            if not unit.manager_name or replace:
                unit.manager_name = PLACEHOLDER
                touched.append('manager_name')

            unit.is_active = True
            unit.save()

            created += is_new
            updated += (not is_new and bool(touched))
            self.stdout.write('  %s %s — %d فیلد' % (
                '+' if is_new else '~', unit.title, len(touched)))

        self.stdout.write(self.style.SUCCESS(
            '\n%d واحد جدید، %d واحد تکمیل شد.' % (created, updated)))
        self.stdout.write(
            'نام‌ها با «%s» علامت خورده‌اند؛ از پنل ادمین '
            'جایگزینشان کنید:\n  /admin/core/presidencyoffice/\n'
            '  /admin/core/presidencyofficeunit/' % PLACEHOLDER
        )
