"""نشاندن ایمیل تماس موسسه در تنظیمات سایت.

این یک فیلد است که سه جا خوانده می‌شود: نوار بالای صفحه، فوتر، و
صفحهٔ تماس. پس یک مقدار، همه‌جا.

آدرس از `.env` گرفته می‌شود (`SITE_CONTACT_EMAIL`) نه از داخل کد، تا
عوض‌کردنش یک ویرایش یک‌خطی روی سرور باشد و نیازی به دیپلوی تازه
نداشته باشد.

هشدار املا
──────────
آدرس فعلی `suppurt@portal.aab.ac.ir` است — املای درست `support` است.
این دستور آدرس را همان‌طور که داده می‌شود می‌نشاند و چیزی را حدس
نمی‌زند، ولی اگر شکل مشکوکی دید در خروجی می‌گوید. آدرس رسمی موسسه پای
هر صفحه و در هر ایمیل به دانشجو می‌نشیند؛ یک غلط تایپی آنجا ماندگار
می‌شود.
"""
from __future__ import annotations

from django.conf import settings as dj_settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import SiteSettings

# املاهای رایجِ غلط که ارزش گفتن دارند
SUSPECT = {
    'suppurt': 'support',
    'suport': 'support',
    'supprot': 'support',
    'infoo': 'info',
    'admn': 'admin',
    'noreplay': 'noreply',
}


class Command(BaseCommand):
    help = 'نشاندن ایمیل تماس موسسه (نوار بالا، فوتر، صفحهٔ تماس)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email', default='',
            help='آدرس ایمیل. اگر ندهید از SITE_CONTACT_EMAIL در .env '
                 'خوانده می‌شود.')
        parser.add_argument(
            '--replace', action='store_true',
            help='اگر آدرسی از قبل هست هم جایگزینش کن')

    @transaction.atomic
    def handle(self, *args, **options):
        email = (options['email']
                 or getattr(dj_settings, 'SITE_CONTACT_EMAIL', '')).strip()
        if not email:
            self.stdout.write(
                'آدرسی داده نشد. یا --email بدهید یا در .env بنویسید:\n'
                '  SITE_CONTACT_EMAIL=support@portal.aab.ac.ir')
            return

        row = SiteSettings.objects.first()
        if row is None:
            self.stderr.write(
                'رکورد «تنظیمات سایت» وجود ندارد — اول در پنل ادمین بسازید.')
            return

        local = email.split('@')[0].lower()
        if local in SUSPECT:
            self.stdout.write(self.style.WARNING(
                'املای «%s» مشکوک است — منظورتان «%s» نبود؟ آدرس همان‌طور '
                'که دادید نشست، ولی این نشانی پای هر صفحه و در هر ایمیل به '
                'دانشجو دیده می‌شود.' % (local, SUSPECT[local])))

        if row.email and not options['replace']:
            self.stdout.write('ایمیل از قبل هست: %s' % row.email)
            self.stdout.write('برای جایگزینی، --replace بزنید.')
            return

        previous = row.email
        row.email = email
        row.save(update_fields=['email'])
        self.stdout.write(self.style.SUCCESS(
            'ایمیل تماس: %s%s' % (email,
                                  (' (قبلاً %s بود)' % previous) if previous else '')))
        self.stdout.write(
            'در نوار بالای صفحه، فوتر و صفحهٔ تماس دیده می‌شود — هر سه '
            'قابل کلیک.')
