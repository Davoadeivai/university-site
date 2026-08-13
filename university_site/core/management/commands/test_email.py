"""آزمایش تنظیمات ایمیل و ترجمهٔ خطای SMTP به زبان آدمیزاد.

    python manage.py test_email --to you@example.com

چرا لازم است
────────────
وقتی ایمیل نمی‌رسد، جنگو یک خطای SMTP خام می‌دهد که چیزی نمی‌گوید —
`(535, b'5.7.8 Username and Password not accepted')`. پشت هر کدام از
این کدها یک اشتباه مشخص و یک راه‌حل مشخص است، و همان را اینجا
می‌نویسیم تا لازم نباشد کسی دنبالش بگردد.

هیچ چیزی را عوض نمی‌کند؛ فقط تنظیمات فعلی را نشان می‌دهد و یک ایمیل
آزمایشی می‌فرستد.
"""
from __future__ import annotations


from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand

# نشانه در متن خطا → (علت، کاری که باید کرد)
HINTS = [
    ('username and password not accepted',
     'رمز پذیرفته نشد',
     'برای جیمیل باید «رمز اپلیکیشن» بسازید، نه رمز اصلی حساب:\n'
     '     myaccount.google.com ← Security ← 2-Step Verification را روشن کنید\n'
     '     ← App passwords ← یک رمز ۱۶ حرفی بسازید و بدون فاصله در .env بگذارید'),
    ('application-specific password required',
     'گوگل رمز اپلیکیشن می‌خواهد',
     'همان مسیر بالا: myaccount.google.com ← Security ← App passwords'),
    ('authentication required',
     'نام کاربری یا رمز خالی است',
     'EMAIL_HOST_USER و EMAIL_HOST_PASSWORD را در .env پر کنید.'),
    ('535',
     'احراز هویت رد شد',
     'رمز اشتباه است یا رمز اپلیکیشن نیست. برای صندوق cPanel، رمز همان '
     'چیزی است که هنگام ساخت حساب گذاشتید.'),
    ('name or service not known',
     'نام میزبان resolve نشد',
     'سرور نتوانست EMAIL_HOST را به آی‌پی تبدیل کند — یعنی DNS، نه رمز.\n'
     '     صندوق روی همین ماشین است، پس از DNS رد نشوید:\n'
     '       EMAIL_HOST=localhost\n'
     '       EMAIL_PORT=25\n'
     '       EMAIL_USE_TLS=False\n'
     '       EMAIL_USE_SSL=False\n'
     '     ترافیک از ماشین بیرون نمی‌رود، پس رمزنگاری لازم نیست.'),
    ('nodename nor servname',
     'نام میزبان resolve نشد',
     'همان مورد بالا — EMAIL_HOST=localhost و EMAIL_PORT=25 را بگذارید.'),
    ('connection refused',
     'سرور جواب نداد',
     'EMAIL_HOST یا EMAIL_PORT اشتباه است. مقدار درست را از cPanel ← '
     'Email Accounts ← Connect Devices بردارید.'),
    ('timed out',
     'اتصال تایم‌اوت شد',
     'یا پورت بسته است یا هاست بیرونی را فیلتر می‌کند. پورت ۴۶۵ (SSL) و '
     '۵۸۷ (TLS) را هر دو امتحان کنید.'),
    ('wrong version number',
     'SSL و TLS جابه‌جا شده‌اند',
     'پورت ۴۶۵ با EMAIL_USE_SSL=True می‌خواهد و ۵۸۷ با EMAIL_USE_TLS=True. '
     'هر دو را هم‌زمان True نگذارید.'),
    ('certificate verify failed',
     'گواهی سرور تأیید نشد',
     'نام میزبان با گواهی نمی‌خواند. به‌جای mail.portal.aab.ac.ir نام '
     'میزبانی را بزنید که cPanel در Connect Devices می‌دهد.'),
    ('sender address rejected',
     'آدرس فرستنده رد شد',
     'DEFAULT_FROM_EMAIL باید همان آدرسی باشد که با آن وارد شده‌اید.'),
]


class Command(BaseCommand):
    help = 'آزمایش تنظیمات ایمیل و ارسال یک پیام نمونه'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to', required=True, help='آدرسی که ایمیل آزمایشی به آن برود')

    def handle(self, *args, **options):
        path = settings.EMAIL_BACKEND
        # نام کلاس در هر دو backend یکی است (EmailBackend)، پس تشخیص
        # باید روی مسیر ماژول باشد نه روی نام کلاس.
        is_console = '.console.' in path
        backend = 'console' if is_console else path.rsplit('.', 2)[-2]

        self.stdout.write('=' * 58)
        self.stdout.write('تنظیمات فعلی')
        self.stdout.write('=' * 58)
        for label, value in (
            ('backend', backend),
            ('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', '—')),
            ('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', '—')),
            ('EMAIL_USE_TLS', getattr(settings, 'EMAIL_USE_TLS', False)),
            ('EMAIL_USE_SSL', getattr(settings, 'EMAIL_USE_SSL', False)),
            ('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', '') or '—'),
            ('رمز', '••• تنظیم شده' if getattr(
                settings, 'EMAIL_HOST_PASSWORD', '') else '!! خالی'),
            ('DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
        ):
            self.stdout.write('  %-20s %s' % (label, value))

        if is_console:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'حالت کنسول: ایمیل‌ها فقط چاپ می‌شوند و ارسال نمی‌شوند.'))
            self.stdout.write(
                'برای ارسال واقعی، EMAIL_HOST_USER و EMAIL_HOST_PASSWORD را '
                'در .env پر کنید و اپ را ری‌استارت کنید.')
            return

        if getattr(settings, 'EMAIL_USE_TLS', False) and getattr(
                settings, 'EMAIL_USE_SSL', False):
            self.stdout.write(self.style.ERROR(
                '\n!! EMAIL_USE_TLS و EMAIL_USE_SSL هر دو True هستند. '
                'فقط یکی باید روشن باشد — ۴۶۵ یعنی SSL، ۵۸۷ یعنی TLS.'))
            return

        self.stdout.write('')
        self.stdout.write('در حال ارسال به %s …' % options['to'])

        message = EmailMultiAlternatives(
            subject='آزمایش ایمیل — موسسه آموزش عالی علامه امینی',
            body=('این یک پیام آزمایشی از سامانهٔ موسسه است.\n\n'
                  'اگر این را می‌بینید، تنظیمات ایمیل درست است و بازیابی '
                  'رمز عبور دانشجویان کار می‌کند.'),
            to=[options['to']],
            connection=get_connection(fail_silently=False),
        )

        try:
            sent = message.send()
        except Exception as exc:                    # noqa: BLE001
            text = str(exc).lower()
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('!! ارسال نشد.'))
            self.stdout.write('خطای خام: %s' % exc)

            for needle, reason, fix in HINTS:
                if needle in text:
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING('علت: %s' % reason))
                    self.stdout.write('راه‌حل:')
                    for line in fix.splitlines():
                        self.stdout.write('  %s' % line)
                    return
            self.stdout.write(
                '\nاین خطا در فهرست شناخته‌شده‌ها نبود — همین متن را بفرستید.')
            return

        self.stdout.write('')
        if sent:
            self.stdout.write(self.style.SUCCESS(
                'ارسال شد. صندوق %s را ببینید (پوشهٔ Spam را هم چک کنید).'
                % options['to']))
            self.stdout.write(
                'حالا بازیابی رمز دانشجویان هم کار می‌کند: '
                '/accounts/password-reset/')
        else:
            self.stdout.write(self.style.WARNING(
                'بدون خطا تمام شد ولی چیزی ارسال نشد — تنظیمات را بررسی کنید.'))
