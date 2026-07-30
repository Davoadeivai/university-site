"""پرکردن تقویم آموزشی نیمسال با مراحل استاندارد.

تقویم آموزشی مدل داشت ولی هیچ رکوردی نداشت، پس تایم‌لاین صفحهٔ اصلی خالی
می‌ماند. این دستور مراحل یک نیمسال را با تاریخ شمسی ثبت می‌کند.

    python manage.py seed_academic_calendar
    python manage.py seed_academic_calendar --year 1404-1405 --semester spring
    python manage.py seed_academic_calendar --clear
"""
import jdatetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# (عنوان, شروع شمسی, پایان شمسی یا None, مهم؟, اقدام, رنگ, توضیح)
DEFAULT_MILESTONES = [
    ('شروع انتخاب واحد',      (1404, 11, 27), (1404, 11, 29), True,
     'registration', 'gold',
     'درس، استاد و کلاس خود را انتخاب کنید'),
    ('شروع کلاس‌ها',           (1404, 12, 2),  None,           True,
     'schedule', 'teal',
     'برنامهٔ هفتگی کلاس‌ها را ببینید'),
    ('حذف و اضافه',            (1405, 1, 17),  (1405, 1, 18),  True,
     'registration', 'sky',
     'فرصت تغییر دروس انتخاب‌شده'),
    ('آخرین مهلت حذف تک‌درس',  (1405, 3, 23),  None,           False,
     'courses', 'violet',
     'حذف یک درس بدون احتساب در سنوات'),
    ('پایان کلاس‌ها',          (1405, 4, 10),  None,           False,
     'schedule', 'amber',
     'پایان جلسات درسی نیمسال'),
    ('شروع امتحانات',          (1405, 4, 13),  None,           True,
     'exam_card', 'rose',
     'کارت ورود به جلسه را دریافت کنید'),
    ('پایان امتحانات',         (1405, 4, 27),  None,           False,
     'grades', 'gold',
     'نمرات پس از ثبت استاد نمایش داده می‌شود'),
]


def to_gregorian(jy, jm, jd):
    return jdatetime.date(jy, jm, jd).togregorian()


class Command(BaseCommand):
    help = 'ثبت مراحل تقویم آموزشی نیمسال (تاریخ‌ها شمسی وارد می‌شوند)'

    def add_arguments(self, parser):
        parser.add_argument('--year', default='1404-1405', help='سال تحصیلی')
        parser.add_argument(
            '--semester', default='spring',
            choices=['fall', 'spring', 'summer'], help='نیم‌سال',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='حذف مراحل قبلی همین سال تحصیلی پیش از ثبت',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from academics.models import AcademicCalendar

        year = options['year']
        semester = options['semester']

        if options['clear']:
            n = AcademicCalendar.objects.filter(academic_year=year).delete()[0]
            self.stdout.write(self.style.WARNING(f'{n} مرحلهٔ قبلی حذف شد.'))

        created = updated = 0
        for idx, (title, start_j, end_j, important, action, tone, desc) in enumerate(
                DEFAULT_MILESTONES, start=1):
            try:
                start = to_gregorian(*start_j)
                end = to_gregorian(*end_j) if end_j else start
            except Exception as exc:
                raise CommandError(f'تاریخ نامعتبر برای «{title}»: {exc}')

            obj, is_new = AcademicCalendar.objects.update_or_create(
                title=title,
                academic_year=year,
                defaults={
                    'semester': semester,
                    'start_date': start,
                    'end_date': end,
                    'is_important': important,
                    'action': action,
                    'tone': tone,
                    'description': desc,
                    'order': idx,
                    'is_active': True,
                },
            )
            created += is_new
            updated += (not is_new)
            js = jdatetime.date.fromgregorian(date=start)
            self.stdout.write(
                f'  {"+" if is_new else "~"} {title:28} {js.year}/{js.month:02d}/{js.day:02d}'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n{created} مرحله ساخته شد، {updated} مرحله به‌روز شد '
            f'(سال {year}، نیم‌سال {semester}).'
        ))
        self.stdout.write(
            'این مراحل از پنل ادمین ← «تقویم آموزشی» قابل ویرایش‌اند.'
        )
