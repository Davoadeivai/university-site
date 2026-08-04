"""ادغام رکوردهای تکراری «دفتر ریاست» در یک رکورد.

PresidencyOffice یک سینگلتون است — ویو با `.first()` می‌خواندش. ولی
مدل جلوی ساخت رکورد دوم را نمی‌گرفت، و وقتی دو رکورد وجود داشته باشد
هرچه در رکورد دوم نوشته شده **هرگز روی سایت دیده نمی‌شود**. روی این
نصب، بیوگرافی رئیس دقیقاً همان‌جا افتاده بود.

این دستور رکوردها را به قدیمی‌ترین‌شان می‌ریزد: هر فیلد خالیِ رکورد
اول از رکوردهای بعدی پر می‌شود، و بقیه حذف می‌شوند.

    python manage.py merge_presidency          # فقط گزارش
    python manage.py merge_presidency --apply
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'ادغام رکوردهای تکراری دفتر ریاست در یک رکورد'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='بدون این گزینه فقط گزارش می‌دهد')

    def handle(self, *args, **options):
        from core.models import PresidencyOffice

        rows = list(PresidencyOffice.objects.order_by('pk'))
        if len(rows) < 2:
            self.stdout.write(self.style.SUCCESS(
                'فقط %d رکورد هست؛ چیزی برای ادغام نیست.' % len(rows)))
            return

        keep, extras = rows[0], rows[1:]
        text_fields = [
            f.name for f in PresidencyOffice._meta.fields
            if f.name != 'id' and f.get_internal_type() in
            ('CharField', 'TextField', 'EmailField')
        ]

        moved = []
        for extra in extras:
            for name in text_fields:
                if getattr(keep, name, '') or ''.strip():
                    continue          # رکورد اصلی خودش مقدار دارد
                value = (getattr(extra, name, '') or '').strip()
                if value:
                    setattr(keep, name, value)
                    moved.append('%s ← #%s' % (name, extra.pk))

            # تصویر رئیس هم اگر فقط در رکورد اضافی باشد منتقل شود
            if not keep.president_photo and extra.president_photo:
                keep.president_photo = extra.president_photo
                moved.append('president_photo ← #%s' % extra.pk)

        self.stdout.write('نگه‌داشته می‌شود: #%s' % keep.pk)
        for line in moved:
            self.stdout.write('  منتقل شد: %s' % line)
        self.stdout.write('حذف می‌شوند: %s' % ', '.join(
            '#%s' % e.pk for e in extras))

        if not options['apply']:
            self.stdout.write(self.style.WARNING(
                '\nبرای اعمال، دوباره با --apply اجرا کنید.'))
            return

        with transaction.atomic():
            keep.save()
            for extra in extras:
                extra.delete()

        self.stdout.write(self.style.SUCCESS(
            '\n%d فیلد منتقل و %d رکورد اضافی حذف شد.' % (len(moved), len(extras))))
