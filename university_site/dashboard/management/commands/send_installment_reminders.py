"""ارسال پیامک یادآوری قسط شهریه قبل از سررسید.

مثال cron روزانه:
  python manage.py send_installment_reminders
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from dashboard.models import Payment, TuitionInstallmentPlan
from core.notify import notify_installment_due


class Command(BaseCommand):
    help = 'پیامک یادآوری اقساط شهریه نزدیک به سررسید'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='چند روز قبل از سررسید (پیش‌فرض از برنامه اقساط سال تحصیلی)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='فقط شمارش؛ پیامک ارسال نشود',
        )

    def handle(self, *args, **options):
        today = timezone.localdate()
        dry = options['dry_run']
        override_days = options['days']

        pending = Payment.objects.filter(
            payment_type='tuition',
            status__in=('pending', 'failed'),
            due_date__isnull=False,
        ).select_related('student', 'semester')

        sent = 0
        skipped = 0
        for payment in pending:
            plan_days = override_days
            if plan_days is None and payment.semester_id:
                plan = TuitionInstallmentPlan.objects.filter(
                    academic_year=payment.semester.academic_year, is_active=True
                ).first()
                plan_days = plan.reminder_days_before if plan else 3
            if plan_days is None:
                plan_days = 3

            window_start = payment.due_date - timedelta(days=plan_days)
            if not (window_start <= today <= payment.due_date):
                skipped += 1
                continue

            # حداکثر یک یادآوری در هر پنجره سررسید
            if payment.reminder_sent_at:
                sent_date = timezone.localtime(payment.reminder_sent_at).date()
                if sent_date >= window_start:
                    skipped += 1
                    continue

            if dry:
                self.stdout.write(
                    f'[dry] #{payment.pk} user={payment.student_id} '
                    f'amount={payment.amount} due={payment.due_date}'
                )
                sent += 1
                continue

            ok = notify_installment_due(payment)
            if ok:
                payment.reminder_sent_at = timezone.now()
                payment.save(update_fields=['reminder_sent_at'])
                sent += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'reminders sent={sent} skipped={skipped} dry_run={dry}'
        ))
