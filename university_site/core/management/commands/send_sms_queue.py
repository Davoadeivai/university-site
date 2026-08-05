"""خالی کردن صف پیامک — برای اجرا با cron.

    python manage.py send_sms_queue
    python manage.py send_sms_queue --limit 100

cPanel ← Cron Jobs، هر ۵ دقیقه:

    cd ~/apps/university_site && python manage.py send_sms_queue

اگر SMS_QUEUE در .env روشن نباشد، پیامک‌ها همان لحظه ارسال می‌شوند و
این دستور کاری برای انجام دادن ندارد.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'ارسال پیامک‌های در صف'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50,
                            help='حداکثر پیام در هر اجرا (پیش‌فرض ۵۰)')
        parser.add_argument('--status', action='store_true',
                            help='فقط وضعیت صف را نشان بده')

    def handle(self, *args, **options):
        from core.sms_queue import QueuedSMS, flush, queue_enabled

        pending = QueuedSMS.objects.filter(status='pending').count()
        failed = QueuedSMS.objects.filter(status='failed').count()

        if options['status']:
            self.stdout.write('در صف: %d | ناموفق: %d | ارسال‌شده: %d' % (
                pending, failed,
                QueuedSMS.objects.filter(status='sent').count()))
            return

        if not queue_enabled():
            self.stdout.write(self.style.WARNING(
                'SMS_QUEUE خاموش است؛ پیامک‌ها همان لحظه ارسال می‌شوند.'))
            if not pending:
                return
            self.stdout.write('اما %d پیام از قبل در صف مانده — ارسال می‌شوند.'
                              % pending)

        if not pending:
            self.stdout.write(self.style.SUCCESS('صف خالی است.'))
            return

        result = flush(limit=options['limit'])
        self.stdout.write(self.style.SUCCESS(
            '%d ارسال شد، %d ناموفق، %d باقی‌مانده.'
            % (result['sent'], result['failed'], result['left'])))

        if failed:
            self.stdout.write(self.style.WARNING(
                '%d پیام پس از چند تلاش ناموفق مانده‌اند؛ '
                'از پنل ← «صف پیامک» بررسی کنید.' % failed))
