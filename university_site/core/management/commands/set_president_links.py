"""نشانی‌های علمی رئیس موسسه را در جای خالی می‌گذارد.

    python manage.py set_president_links
    python manage.py set_president_links --website https://example.com
    python manage.py set_president_links --replace

چرا دستور و نه مهاجرت
─────────────────────
مهاجرت یک بار اجرا می‌شود و اگر ادمین بعداً مقدار را عوض کند، دفعهٔ
بعد چیزی برنمی‌گردد. این دستور در هر دیپلوی بی‌خطر اجرا می‌شود چون
پیش‌فرض فقط جای خالی را پر می‌کند؛ هرچه ادمین نوشته باشد دست‌نخورده
می‌ماند مگر با ‎--replace‎ صریحاً بخواهید.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.models import PresidencyOffice

# نشانی انجمن علمی که موسسه تأیید کرد صفحهٔ رسمی رئیس است
DEFAULT_WEBSITE = 'https://WCM-Society.Com'
DEFAULT_LABEL = 'انجمن مدیریت زنجیره تأمین'


class Command(BaseCommand):
    help = 'ثبت وب‌سایت و نشانی‌های علمی رئیس موسسه'

    def add_arguments(self, parser):
        parser.add_argument('--website', default=DEFAULT_WEBSITE)
        parser.add_argument('--label', default=DEFAULT_LABEL)
        parser.add_argument(
            '--replace', action='store_true',
            help='مقدار فعلی را هم بازنویسی کن (پیش‌فرض: فقط جای خالی)')

    def handle(self, *args, **options):
        office = PresidencyOffice.objects.first()
        if office is None:
            self.stdout.write(self.style.WARNING(
                'رکورد دفتر ریاست وجود ندارد — چیزی تنظیم نشد.'))
            return

        changed = []
        for field, value in (
            ('president_website', options['website']),
            ('president_website_label', options['label']),
        ):
            current = getattr(office, field, '') or ''
            if current and not options['replace']:
                continue
            if current == value:
                continue
            setattr(office, field, value)
            changed.append(field)

        if not changed:
            self.stdout.write('چیزی برای تغییر نبود.')
            return

        office.save(update_fields=changed)
        self.stdout.write(self.style.SUCCESS(
            'ثبت شد: %s' % '، '.join(changed)))
