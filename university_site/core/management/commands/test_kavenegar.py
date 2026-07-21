"""تست اتصال کاوه‌نگار و ارسال OTP آزمایشی."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'تست ارسال پیامک کاوه‌نگار '
        '(مثال: python manage.py test_kavenegar 09195221749)'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'phone', type=str, nargs='?', default='09195221749',
            help='شماره موبایل گیرنده (پیش‌فرض: 09195221749)',
        )
        parser.add_argument(
            '--code', type=str, default='123456',
            help='کد آزمایشی OTP (پیش‌فرض: 123456)',
        )
        parser.add_argument(
            '--sample', action='store_true',
            help='ارسال دقیقاً مثل نمونهٔ پنل (متن ثابت کاوه‌نگار)',
        )

    def handle(self, *args, **options):
        phone = options['phone'].strip()
        code = options['code'].strip()

        api_key = (getattr(settings, 'KAVENEGAR_API_KEY', '') or '').strip()
        if not api_key:
            raise CommandError(
                'KAVENEGAR_API_KEY خالی است.\n'
                'کلید کامل را از پنل کاوه‌نگار کپی کن و در فایل .env بگذار:\n'
                '  KAVENEGAR_API_KEY=کلید_کامل_بدون_ستاره\n'
                '  SMS_ENABLED=True\n'
                '  SMS_SENDER_NUMBER=2000660110'
            )
        if '*' in api_key:
            raise CommandError(
                'API Key فعلی ماسک‌شده است (دارای *). '
                'کلید کامل بدون ستاره را در .env بگذار.'
            )
        if not getattr(settings, 'SMS_ENABLED', False):
            raise CommandError('SMS_ENABLED=False است. در .env مقدار را True کنید.')

        sender = (getattr(settings, 'SMS_SENDER_NUMBER', '') or '').strip() or '2000660110'
        self.stdout.write(f'SENDER  = {sender}')
        self.stdout.write(f'PHONE   = {phone}')

        if options['sample']:
            from core.kavenegar_client import kavenegar_sms_send
            message = '.وب سرویس پیام کوتاه کاوه نگار'
            self.stdout.write(f'MESSAGE = {message}')
            try:
                response = kavenegar_sms_send(receptor=phone, message=message, sender=sender)
            except Exception as e:
                raise CommandError(f'ارسال ناموفق: {e}') from e
            self.stdout.write(self.style.SUCCESS(f'ارسال موفق: {response}'))
            return

        self.stdout.write(f'CODE    = {code}')
        from core.sms import send_otp
        ok = send_otp(phone, code, message=f'کد تأیید آزمایشی: {code}')
        if ok:
            self.stdout.write(self.style.SUCCESS('ارسال OTP موفق بود. پیامک را روی گوشی چک کنید.'))
        else:
            raise CommandError('ارسال ناموفق بود. لاگ سرور و اعتبار پنل کاوه‌نگار را بررسی کنید.')
