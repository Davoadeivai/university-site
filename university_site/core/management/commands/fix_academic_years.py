"""تبدیل سال تحصیلیِ میلادی به شمسی، در خود دیتابیس.

چرا نمایش کافی نیست
───────────────────
می‌شد فقط ستون ادمین را شمسی نشان داد و اصل داده را میلادی گذاشت. ولی
`academic_year` یک متن ساده است که همه‌جا مستقیم استفاده می‌شود:
فیلتر کنار فهرست، جست‌وجو، مرتب‌سازی، و مقایسه با سال ترم جاری. اگر
نیمی از ردیف‌ها «۱۴۰۴-۱۴۰۵» باشند و نیمی «2026-2027»، فیلتر دو گزینهٔ
جدا نشان می‌دهد برای یک سال، و مرتب‌سازی هم به‌هم می‌ریزد چون «2»
پیش از «۱» می‌آید.

پس خود مقدار اصلاح می‌شود. مقداری که از قبل شمسی است دست نمی‌خورد.
"""
from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from core.jalali import jalali_year_range

# (اپ، مدل، نام فیلد) — هر جایی که سال تحصیلی متنی نگه داشته می‌شود
TARGETS = [
    ('admissions', 'TuitionStructure', 'academic_year'),
    ('academics', 'AcademicCalendar', 'academic_year'),
    ('dashboard', 'Semester', 'academic_year'),
]


# ارقام فارسی → لاتین
_TO_LATIN = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def to_jalali(value: str) -> str:
    """سال میلادی را شمسی می‌کند و ارقام را لاتین نگه می‌دارد.

    `jalali_year_range` خروجی را با رقم فارسی می‌دهد، که برای نمایش
    درست است ولی برای ذخیره نه: مرتب‌سازی الفبایی «۱۴۰۴» و «1404» را
    دو چیز می‌بیند، `unique_together` هم همین‌طور، و هر کدی که با
    رشتهٔ لاتین مقایسه می‌کند از کار می‌افتد. ارقام در قالب فارسی
    می‌شوند، نه در دیتابیس.
    """
    if not value:
        return value
    converted = jalali_year_range(str(value))
    if not converted:
        return value
    return converted.translate(_TO_LATIN)


class Command(BaseCommand):
    help = 'تبدیل سال تحصیلی ذخیره‌شده از میلادی به شمسی'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true', help='فقط گزارش بده')

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options['dry_run']
        total = 0

        for app_label, model_name, field in TARGETS:
            try:
                model = apps.get_model(app_label, model_name)
            except LookupError:
                continue

            changed = 0
            for obj in model.objects.all():
                current = getattr(obj, field, '') or ''
                fixed = to_jalali(current)
                if fixed == current:
                    continue
                self.stdout.write('  %-28s %-14s → %s' % (
                    model_name, current, fixed))
                if not dry:
                    setattr(obj, field, fixed)
                    obj.save(update_fields=[field])
                changed += 1

            if changed:
                self.stdout.write(self.style.SUCCESS(
                    '%s: %d ردیف' % (model_name, changed)))
            total += changed

        verb = 'می‌شد اصلاح کرد' if dry else 'اصلاح شد'
        self.stdout.write('')
        if total:
            self.stdout.write(self.style.SUCCESS('%d ردیف %s.' % (total, verb)))
        else:
            self.stdout.write('همهٔ سال‌ها از قبل شمسی بودند.')
        if dry:
            self.stdout.write('حالت آزمایشی بود — چیزی نوشته نشد.')
